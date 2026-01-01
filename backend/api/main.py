"""스탑퍼 FastAPI 메인 앱"""

import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import init_db, close_db, fetch_all, fetch_one, fetch_val, execute
from models.schemas import (
    FoodResponse, FoodSearchResponse,
    UserSettings, RecordCreate, RecordResponse, TodayResponse, DailyTotals,
    CombinationCreate, CombinationResponse, CombinationListResponse,
    ComboIntent, ComboResult, ComboSignals,
    ScanResult
)
from datetime import datetime
import uuid


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클"""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="🛑 STOPPER API",
    description="멈추면 보이는 한 끼의 %",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Health ==============

@app.get("/")
async def root():
    return {"status": "ok", "message": "🛑 STOPPER API", "version": "1.0.0"}


@app.get("/health")
async def health():
    count = await fetch_val("SELECT COUNT(*) FROM foods")
    return {"status": "healthy", "foods_count": count}


# ============== Foods ==============

@app.get("/api/foods/search", response_model=FoodSearchResponse)
async def search_foods(
    q: str = Query(..., min_length=1, description="검색어"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    sort: str = Query("relevance", description="정렬: relevance, calories_asc, protein_desc, sugar_asc"),
    limit: int = Query(20, le=100),
    offset: int = Query(0)
):
    """음식 검색"""
    # 정렬 옵션
    order_by = {
        "relevance": "ts_rank(to_tsvector('simple', name), to_tsquery('simple', $1)) DESC",
        "calories_asc": "calories ASC",
        "calories_desc": "calories DESC",
        "protein_desc": "protein DESC",
        "protein_asc": "protein ASC",
        "sugar_asc": "sugar ASC",
        "sugar_desc": "sugar DESC"
    }.get(sort, "ts_rank(to_tsvector('simple', name), to_tsquery('simple', $1)) DESC")

    # 검색 쿼리 생성 (공백을 &로 연결)
    search_terms = q.strip().split()
    tsquery = " & ".join(search_terms)

    # WHERE 조건
    where_clause = "to_tsvector('simple', name) @@ to_tsquery('simple', $1)"
    params = [tsquery]

    if category:
        where_clause += " AND category_large = $2"
        params.append(category)

    # 총 개수
    count_query = f"SELECT COUNT(*) FROM foods WHERE {where_clause}"
    total = await fetch_val(count_query, *params)

    # 검색 실행
    search_query = f"""
        SELECT id, food_code, name, manufacturer, category_large, category_medium,
               calories, protein, fat, carbohydrate, sugar, sodium, saturated_fat, serving_size
        FROM foods
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.extend([limit, offset])

    rows = await fetch_all(search_query, *params)

    items = [
        FoodResponse(
            id=r["id"],
            name=r["name"],
            manufacturer=r["manufacturer"],
            category_large=r["category_large"],
            category_medium=r["category_medium"],
            calories=float(r["calories"] or 0),
            protein=float(r["protein"] or 0),
            fat=float(r["fat"] or 0),
            carbohydrate=float(r["carbohydrate"] or 0),
            sugar=float(r["sugar"] or 0),
            sodium=float(r["sodium"] or 0),
            saturated_fat=float(r["saturated_fat"] or 0),
            serving_size=r["serving_size"]
        )
        for r in rows
    ]

    return FoodSearchResponse(total=total, items=items)


@app.get("/api/foods/{food_id}", response_model=FoodResponse)
async def get_food(food_id: int):
    """음식 상세"""
    row = await fetch_one(
        "SELECT * FROM foods WHERE id = $1",
        food_id
    )
    if not row:
        raise HTTPException(404, "Food not found")

    return FoodResponse(
        id=row["id"],
        name=row["name"],
        manufacturer=row["manufacturer"],
        category_large=row["category_large"],
        category_medium=row["category_medium"],
        calories=float(row["calories"] or 0),
        protein=float(row["protein"] or 0),
        fat=float(row["fat"] or 0),
        carbohydrate=float(row["carbohydrate"] or 0),
        sugar=float(row["sugar"] or 0),
        sodium=float(row["sodium"] or 0),
        saturated_fat=float(row["saturated_fat"] or 0),
        serving_size=row["serving_size"]
    )


@app.get("/api/foods/{food_id}/scan")
async def scan_food(
    food_id: int,
    calorie_goal: int = Query(2000),
    protein_goal: int = Query(60),
    sugar_limit: int = Query(50)
):
    """음식 스캔 - % 계산 + 판정"""
    row = await fetch_one("SELECT * FROM foods WHERE id = $1", food_id)
    if not row:
        raise HTTPException(404, "Food not found")

    calories = float(row["calories"] or 0)
    protein = float(row["protein"] or 0)
    sugar = float(row["sugar"] or 0)
    sodium = float(row["sodium"] or 0)

    # % 계산
    cal_pct = round(calories / calorie_goal * 100) if calorie_goal > 0 else 0
    pro_pct = round(protein / protein_goal * 100) if protein_goal > 0 else 0
    sug_pct = round(sugar / sugar_limit * 100) if sugar_limit > 0 else 0
    sod_pct = round(sodium / 2000 * 100)  # 나트륨 기준 2000mg

    # 상태 판정
    def get_status(pct, reverse=False):
        if reverse:  # 단백질: 높을수록 좋음
            return "good" if pct >= 30 else "low"
        if pct <= 25:
            return "safe"
        if pct <= 45:
            return "ok"
        if pct <= 70:
            return "caution"
        return "danger"

    status = {
        "calories": get_status(cal_pct),
        "protein": get_status(pro_pct, reverse=True),
        "sugar": get_status(sug_pct),
        "sodium": get_status(sod_pct)
    }

    # 판정 문구
    verdict = generate_verdict(cal_pct, pro_pct, sug_pct, sod_pct, status)

    return {
        "food": {
            "id": row["id"],
            "name": row["name"],
            "manufacturer": row["manufacturer"],
            "serving_size": row["serving_size"],
            "calories": calories,
            "protein": protein,
            "sugar": sugar,
            "sodium": sodium,
            "fat": float(row["fat"] or 0),
            "carbohydrate": float(row["carbohydrate"] or 0)
        },
        "percentages": {
            "calories": cal_pct,
            "protein": pro_pct,
            "sugar": sug_pct,
            "sodium": sod_pct
        },
        "status": status,
        "verdict": verdict
    }


def generate_verdict(cal_pct, pro_pct, sug_pct, sod_pct, status):
    """판정 문구 생성"""
    verdicts = []

    # 전체 안전
    if all(s in ["safe", "ok", "good"] for s in [status["calories"], status["sugar"], status["sodium"]]):
        if status["protein"] == "good":
            return "이상적인 선택이에요! 💪"
        return "괜찮은 선택이에요! 🛡️"

    # 개별 판정
    if status["calories"] == "danger":
        verdicts.append(f"칼로리가 높아요 ({cal_pct}%)")
    elif status["calories"] == "caution":
        verdicts.append(f"칼로리 주의 ({cal_pct}%)")

    if status["protein"] == "low":
        verdicts.append("단백질 보충 필요")

    if status["sugar"] in ["danger", "caution"]:
        verdicts.append(f"당류 주의! ({sug_pct}%)")

    if status["sodium"] in ["danger", "caution"]:
        verdicts.append("나트륨 높음, 물 많이 드세요 💧")

    if not verdicts:
        return "적절한 선택이에요 👍"

    return " / ".join(verdicts)


@app.get("/api/categories")
async def get_categories():
    """카테고리 목록"""
    rows = await fetch_all("""
        SELECT category_large, COUNT(*) as count
        FROM foods
        WHERE category_large IS NOT NULL AND category_large != ''
        GROUP BY category_large
        ORDER BY count DESC
    """)
    return {"categories": [{"name": r["category_large"], "count": r["count"]} for r in rows]}


# ============== Daily Records ==============

@app.post("/api/records")
async def add_record(
    record: RecordCreate,
    x_fingerprint: str = Header(...)
):
    """오늘 기록 추가"""
    food = await fetch_one("SELECT * FROM foods WHERE id = $1", record.food_id)
    if not food:
        raise HTTPException(404, "Food not found")

    # 영양정보 계산 (수량 반영)
    qty = record.quantity
    calories = float(food["calories"] or 0) * qty
    protein = float(food["protein"] or 0) * qty
    sugar = float(food["sugar"] or 0) * qty
    sodium = float(food["sodium"] or 0) * qty

    result = await fetch_one("""
        INSERT INTO daily_records (
            user_fingerprint, food_id, quantity, meal_type,
            calories, protein, sugar, sodium
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id, created_at
    """, x_fingerprint, record.food_id, qty, record.meal_type,
        calories, protein, sugar, sodium
    )

    return {
        "id": result["id"],
        "food_id": record.food_id,
        "food_name": food["name"],
        "quantity": qty,
        "calories": calories,
        "protein": protein,
        "sugar": sugar,
        "sodium": sodium
    }


@app.get("/api/records/today")
async def get_today_records(
    x_fingerprint: str = Header(...)
):
    """오늘 기록 조회"""
    today = date.today()

    # 기록 조회
    rows = await fetch_all("""
        SELECT r.id, r.food_id, f.name as food_name, r.quantity, r.meal_type,
               r.calories, r.protein, r.sugar, r.sodium, r.created_at
        FROM daily_records r
        JOIN foods f ON r.food_id = f.id
        WHERE r.user_fingerprint = $1 AND r.recorded_date = $2
        ORDER BY r.created_at DESC
    """, x_fingerprint, today)

    records = [
        RecordResponse(
            id=r["id"],
            food_id=r["food_id"],
            food_name=r["food_name"],
            quantity=float(r["quantity"]),
            meal_type=r["meal_type"],
            calories=float(r["calories"] or 0),
            protein=float(r["protein"] or 0),
            sugar=float(r["sugar"] or 0),
            sodium=float(r["sodium"] or 0),
            recorded_at=r["created_at"]
        )
        for r in rows
    ]

    # 합계 계산
    totals = DailyTotals(
        calories=sum(r.calories for r in records),
        protein=sum(r.protein for r in records),
        sugar=sum(r.sugar for r in records),
        sodium=sum(r.sodium for r in records)
    )

    return TodayResponse(date=today, totals=totals, records=records)


@app.delete("/api/records/{record_id}")
async def delete_record(
    record_id: int,
    x_fingerprint: str = Header(...)
):
    """기록 삭제"""
    result = await execute("""
        DELETE FROM daily_records
        WHERE id = $1 AND user_fingerprint = $2
    """, record_id, x_fingerprint)

    return {"deleted": True}


# ============== Combinations (Neo4j-ready) ==============

def generate_combo_id():
    """문자열 조합 ID 생성: combo_YYYYMMDD_XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6]
    return f"combo_{today}_{short_uuid}"


def generate_author_id(fingerprint: str):
    """문자열 author ID 생성"""
    return f"user_anon_{fingerprint[:12]}"


@app.get("/api/combinations")
async def list_combinations(
    sort: str = Query("likes", description="정렬: likes, recent"),
    goal: Optional[str] = Query(None, description="목표: diet, bulk, maintain, diabetes"),
    limit: int = Query(20, le=50),
    offset: int = Query(0)
):
    """조합 목록 (Neo4j-ready JSON 구조)"""
    order_by = "likes_count DESC" if sort == "likes" else "created_at DESC"

    where_clause = "1=1"
    params = []

    if goal:
        where_clause += f" AND intent->>'goal' = ${len(params) + 1}"
        params.append(goal)

    # 총 개수
    total = await fetch_val(
        f"SELECT COUNT(*) FROM combinations WHERE {where_clause}",
        *params
    )

    # 조회
    rows = await fetch_all(f"""
        SELECT combo_id, name, description, author_id, items, intent, result, signals,
               tags, likes_count, is_official, created_at
        FROM combinations
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """, *params, limit, offset)

    items = [
        {
            "id": r["combo_id"],
            "name": r["name"],
            "description": r["description"],
            "author_id": r["author_id"],
            "items": json.loads(r["items"]) if isinstance(r["items"], str) else r["items"],
            "intent": json.loads(r["intent"]) if isinstance(r["intent"], str) else r["intent"],
            "result": json.loads(r["result"]) if isinstance(r["result"], str) else r["result"],
            "signals": json.loads(r["signals"]) if isinstance(r["signals"], str) else r["signals"],
            "tags": r["tags"] or [],
            "likes_count": r["likes_count"],
            "is_official": r["is_official"],
            "created_at": r["created_at"].isoformat()
        }
        for r in rows
    ]

    return {"total": total, "items": items}


@app.get("/api/combinations/{combo_id}")
async def get_combination(combo_id: str):
    """조합 상세 (combo_id는 문자열)"""
    row = await fetch_one(
        "SELECT * FROM combinations WHERE combo_id = $1",
        combo_id
    )
    if not row:
        raise HTTPException(404, "Combination not found")

    # 조회수 증가
    await execute(
        "UPDATE combinations SET views_count = views_count + 1 WHERE combo_id = $1",
        combo_id
    )

    return {
        "id": row["combo_id"],
        "name": row["name"],
        "description": row["description"],
        "author_id": row["author_id"],
        "items": json.loads(row["items"]) if isinstance(row["items"], str) else row["items"],
        "intent": json.loads(row["intent"]) if isinstance(row["intent"], str) else row["intent"],
        "result": json.loads(row["result"]) if isinstance(row["result"], str) else row["result"],
        "signals": json.loads(row["signals"]) if isinstance(row["signals"], str) else row["signals"],
        "tags": row["tags"] or [],
        "likes_count": row["likes_count"],
        "views_count": row["views_count"],
        "is_official": row["is_official"],
        "created_at": row["created_at"].isoformat()
    }


@app.post("/api/combinations")
async def create_combination(
    combo: CombinationCreate,
    x_fingerprint: str = Header(...)
):
    """조합 생성 (Neo4j-ready 구조)"""
    combo_id = generate_combo_id()
    author_id = generate_author_id(x_fingerprint)

    # items에 food_id를 문자열로 변환
    items_json = [
        {
            "food_id": f"food_{item.food_id}" if not item.food_id.startswith("food_") else item.food_id,
            "name": item.name,
            "qty": item.qty,
            "calories": item.calories,
            "protein": item.protein,
            "sugar": item.sugar,
            "sodium": item.sodium
        }
        for item in combo.items
    ]

    result = await fetch_one("""
        INSERT INTO combinations (
            combo_id, name, description, author_id,
            items, intent, result, signals, tags
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING combo_id
    """,
        combo_id,
        combo.name,
        combo.description,
        author_id,
        json.dumps(items_json),
        json.dumps(combo.intent.model_dump()),
        json.dumps(combo.result.model_dump()),
        json.dumps(combo.signals.model_dump()),
        combo.tags
    )

    return {
        "id": result["combo_id"],
        "author_id": author_id,
        "message": "조합이 등록되었습니다"
    }


@app.post("/api/combinations/{combo_id}/like")
async def toggle_like(
    combo_id: str,
    x_fingerprint: str = Header(...)
):
    """추천 토글 (combo_id는 문자열)"""
    # DB PK 조회
    row = await fetch_one(
        "SELECT id FROM combinations WHERE combo_id = $1",
        combo_id
    )
    if not row:
        raise HTTPException(404, "Combination not found")

    db_id = row["id"]

    # 기존 추천 확인
    existing = await fetch_one("""
        SELECT id FROM likes
        WHERE combination_id = $1 AND user_fingerprint = $2
    """, db_id, x_fingerprint)

    if existing:
        # 추천 취소
        await execute("""
            DELETE FROM likes
            WHERE combination_id = $1 AND user_fingerprint = $2
        """, db_id, x_fingerprint)
        await execute("""
            UPDATE combinations SET likes_count = likes_count - 1
            WHERE id = $1
        """, db_id)
        return {"liked": False}
    else:
        # 추천
        await execute("""
            INSERT INTO likes (combination_id, user_fingerprint)
            VALUES ($1, $2)
        """, db_id, x_fingerprint)
        await execute("""
            UPDATE combinations SET likes_count = likes_count + 1
            WHERE id = $1
        """, db_id)
        return {"liked": True}


@app.get("/api/combinations/{combo_id}/liked")
async def check_liked(
    combo_id: str,
    x_fingerprint: str = Header(...)
):
    """추천 여부 확인"""
    row = await fetch_one(
        "SELECT id FROM combinations WHERE combo_id = $1",
        combo_id
    )
    if not row:
        return {"liked": False}

    existing = await fetch_one("""
        SELECT id FROM likes
        WHERE combination_id = $1 AND user_fingerprint = $2
    """, row["id"], x_fingerprint)

    return {"liked": existing is not None}


@app.patch("/api/combinations/{combo_id}/signals")
async def update_signals(
    combo_id: str,
    worked: Optional[bool] = None,
    x_fingerprint: str = Header(...)
):
    """조합 피드백 업데이트 (signals.worked)"""
    row = await fetch_one(
        "SELECT author_id, signals FROM combinations WHERE combo_id = $1",
        combo_id
    )
    if not row:
        raise HTTPException(404, "Combination not found")

    # 본인 조합만 수정 가능
    author_id = generate_author_id(x_fingerprint)
    if row["author_id"] != author_id:
        raise HTTPException(403, "권한이 없습니다")

    signals = json.loads(row["signals"]) if isinstance(row["signals"], str) else row["signals"]

    if worked is not None:
        signals["worked"] = worked

    await execute("""
        UPDATE combinations SET signals = $1 WHERE combo_id = $2
    """, json.dumps(signals), combo_id)

    return {"signals": signals}


# ============== User Settings ==============

@app.post("/api/users/settings")
async def save_settings(
    settings: UserSettings,
    x_fingerprint: str = Header(...)
):
    """사용자 설정 저장"""
    await execute("""
        INSERT INTO users (fingerprint, goal_type, calorie_goal, protein_goal, sugar_limit)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (fingerprint)
        DO UPDATE SET
            goal_type = $2,
            calorie_goal = $3,
            protein_goal = $4,
            sugar_limit = $5,
            last_active = NOW()
    """, x_fingerprint, settings.goal_type, settings.calorie_goal,
        settings.protein_goal, settings.sugar_limit)

    return {"message": "Settings saved"}


@app.get("/api/users/settings")
async def get_settings(x_fingerprint: str = Header(...)):
    """사용자 설정 조회"""
    row = await fetch_one(
        "SELECT * FROM users WHERE fingerprint = $1",
        x_fingerprint
    )

    if not row:
        return UserSettings()

    return UserSettings(
        goal_type=row["goal_type"],
        calorie_goal=row["calorie_goal"],
        protein_goal=row["protein_goal"],
        sugar_limit=row["sugar_limit"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
