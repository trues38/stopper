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
from db.category_serving_rules import get_serving_rule
from db.meal_type_rules import get_meal_type, effective_protein
from db.stopper_messages import (
    get_protein_verdict,
    get_calorie_verdict,
    get_sugar_verdict,
    get_overall_verdict
)
from api.openfoodfacts import (
    fetch_product_by_barcode,
    match_product_name
)
from api.mfds import lookup_barcode_i2570
from api.convenience import match_convenience_product
from models.schemas import (
    FoodResponse, FoodSearchResponse,
    UserSettings, RecordCreate, RecordResponse, TodayResponse, DailyTotals,
    CombinationCreate, CombinationResponse, CombinationListResponse,
    ComboIntent, ComboResult, ComboSignals,
    ScanResult,
    BarcodeLookupResponse, ProductRegisterRequest, ProductRegisterResponse,
    BarcodeMatchResponse, ConvenienceProduct
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
    # 정렬 옵션 (ILIKE 검색용)
    order_by = {
        "relevance": "name ASC",
        "calories_asc": "calories ASC",
        "calories_desc": "calories DESC",
        "protein_desc": "protein DESC",
        "protein_asc": "protein ASC",
        "sugar_asc": "sugar ASC",
        "sugar_desc": "sugar DESC"
    }.get(sort, "name ASC")

    # ILIKE 검색 (한글에 적합)
    search_pattern = f"%{q.strip()}%"

    # WHERE 조건
    where_clause = "name ILIKE $1"
    params = [search_pattern]

    if category:
        where_clause += " AND category_large = $2"
        params.append(category)

    # 총 개수
    count_query = f"SELECT COUNT(*) FROM foods WHERE {where_clause}"
    total = await fetch_val(count_query, *params)

    # 검색 실행
    search_query = f"""
        SELECT id, food_code, name, manufacturer, category_large, category_medium, category_small,
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
            category_small=r["category_small"],
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
        category_small=row["category_small"],
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
    sugar_limit: int = Query(50),
    goal_type: str = Query("maintain", description="bulk, diet, diabetes, maintain")
):
    """
    STOPPER 핵심 기능: 현실 기준 식품 스캔

    - effective_protein: 마케팅 숫자 무력화, 실제 섭취 가능량 기준
    - meal_type 기반 자동 분류
    - 현실 기준 메시지 시스템
    """
    row = await fetch_one("SELECT * FROM foods WHERE id = $1", food_id)
    if not row:
        raise HTTPException(404, "Food not found")

    # 원본 영양 정보
    calories = float(row["calories"] or 0)
    protein_raw = float(row["protein"] or 0)
    sugar = float(row["sugar"] or 0)
    sodium = float(row["sodium"] or 0)

    # meal_type 자동 분류
    category_small = row["category_small"] or ""
    product_name = row["name"] or ""
    meal_type = get_meal_type(category_small, product_name)

    # 🔥 STOPPER 핵심: effective_protein (현실 기준)
    protein_effective = effective_protein(protein_raw, meal_type)

    # % 계산 (effective_protein 사용)
    cal_pct = round(calories / calorie_goal * 100) if calorie_goal > 0 else 0
    pro_pct = round(protein_effective / protein_goal * 100) if protein_goal > 0 else 0
    sug_pct = round(sugar / sugar_limit * 100) if sugar_limit > 0 else 0
    sod_pct = round(sodium / 2000 * 100)  # 나트륨 기준 2000mg

    # STOPPER 메시지 시스템
    protein_msg = get_protein_verdict(protein_effective, protein_goal, meal_type)
    calorie_msg = get_calorie_verdict(calories, calorie_goal, meal_type)
    sugar_msg = get_sugar_verdict(sugar, sugar_limit, meal_type)

    overall = get_overall_verdict(
        protein_msg["verdict"],
        calorie_msg["verdict"],
        sugar_msg["verdict"],
        goal_type
    )

    return {
        "food": {
            "id": row["id"],
            "name": row["name"],
            "manufacturer": row["manufacturer"],
            "category_small": category_small,
            "meal_type": meal_type,
            "serving_size": row["serving_size"],
            "calories": calories,
            "protein_raw": protein_raw,  # 표기값
            "protein_effective": protein_effective,  # 현실값 (STOPPER)
            "sugar": sugar,
            "sodium": sodium,
            "fat": float(row["fat"] or 0),
            "carbohydrate": float(row["carbohydrate"] or 0)
        },
        "percentages": {
            "calories": cal_pct,
            "protein": pro_pct,  # effective 기준
            "sugar": sug_pct,
            "sodium": sod_pct
        },
        "messages": {
            "protein": protein_msg,
            "calorie": calorie_msg,
            "sugar": sugar_msg,
            "overall": overall
        },
        "stopper_note": {
            "protein_capped": protein_effective < protein_raw,
            "protein_cap_reason": f"{meal_type} 타입은 현실 기준 {protein_effective}g까지 인정" if protein_effective < protein_raw else None
        }
    }


@app.get("/api/barcode/{barcode}/scan")
async def scan_barcode(
    barcode: str,
    calorie_goal: int = Query(2000),
    protein_goal: int = Query(60),
    sugar_limit: int = Query(50),
    goal_type: str = Query("maintain", description="bulk, diet, diabetes, maintain")
):
    """
    바코드 스캔 → STOPPER 분석

    1. STOPPER DB에서 바코드 조회
    2. 없으면 Open Food Facts에서 실시간 조회
    3. OFF 제품을 STOPPER DB와 매칭
    4. 매칭 성공시 바코드 자동 업데이트
    5. STOPPER 분석 결과 반환
    """

    # 1. STOPPER DB에서 바코드 조회
    row = await fetch_one("SELECT * FROM foods WHERE barcode = $1", barcode)

    if row:
        # 기존 제품 → 스캔 결과 반환
        food_id = row["id"]

        # 원본 영양 정보
        calories = float(row["calories"] or 0)
        protein_raw = float(row["protein"] or 0)
        sugar = float(row["sugar"] or 0)
        sodium = float(row["sodium"] or 0)

        # meal_type 자동 분류
        category_small = row["category_small"] or ""
        product_name = row["name"] or ""
        meal_type = get_meal_type(category_small, product_name)

        # 🔥 STOPPER 핵심: effective_protein
        protein_effective = effective_protein(protein_raw, meal_type)

        # % 계산
        cal_pct = round(calories / calorie_goal * 100) if calorie_goal > 0 else 0
        pro_pct = round(protein_effective / protein_goal * 100) if protein_goal > 0 else 0
        sug_pct = round(sugar / sugar_limit * 100) if sugar_limit > 0 else 0
        sod_pct = round(sodium / 2000 * 100)

        # STOPPER 메시지
        protein_msg = get_protein_verdict(protein_effective, protein_goal, meal_type)
        calorie_msg = get_calorie_verdict(calories, calorie_goal, meal_type)
        sugar_msg = get_sugar_verdict(sugar, sugar_limit, meal_type)
        overall = get_overall_verdict(
            protein_msg["verdict"],
            calorie_msg["verdict"],
            sugar_msg["verdict"],
            goal_type
        )

        return {
            "source": "stopper_db",
            "food": {
                "id": row["id"],
                "name": row["name"],
                "manufacturer": row["manufacturer"],
                "category_small": category_small,
                "meal_type": meal_type,
                "serving_size": row["serving_size"],
                "barcode": barcode,
                "calories": calories,
                "protein_raw": protein_raw,
                "protein_effective": protein_effective,
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
            "messages": {
                "protein": protein_msg,
                "calorie": calorie_msg,
                "sugar": sugar_msg,
                "overall": overall
            },
            "stopper_note": {
                "protein_capped": protein_effective < protein_raw,
                "protein_cap_reason": f"{meal_type} 타입은 현실 기준 {protein_effective}g까지 인정" if protein_effective < protein_raw else None
            }
        }

    # 2. Open Food Facts에서 조회
    off_product = fetch_product_by_barcode(barcode)

    if not off_product:
        raise HTTPException(404, f"바코드 {barcode}를 찾을 수 없습니다")

    # 3. STOPPER DB와 매칭 시도
    stopper_foods = await fetch_all("SELECT id, name, manufacturer FROM foods LIMIT 1000")
    match_result = match_product_name(off_product, stopper_foods)

    if match_result and match_result['score'] >= 0.80:
        # 매칭 성공 → 바코드 업데이트
        matched_food = match_result['food']
        await execute(
            "UPDATE foods SET barcode = $1 WHERE id = $2",
            barcode, matched_food['id']
        )

        # 매칭된 제품으로 스캔 (재귀)
        row = await fetch_one("SELECT * FROM foods WHERE id = $1", matched_food['id'])

        # (위와 동일한 스캔 로직 - 중복 제거 위해 함수화 필요하지만 일단 단순 복사)
        calories = float(row["calories"] or 0)
        protein_raw = float(row["protein"] or 0)
        sugar = float(row["sugar"] or 0)
        sodium = float(row["sodium"] or 0)

        category_small = row["category_small"] or ""
        product_name = row["name"] or ""
        meal_type = get_meal_type(category_small, product_name)
        protein_effective = effective_protein(protein_raw, meal_type)

        cal_pct = round(calories / calorie_goal * 100) if calorie_goal > 0 else 0
        pro_pct = round(protein_effective / protein_goal * 100) if protein_goal > 0 else 0
        sug_pct = round(sugar / sugar_limit * 100) if sugar_limit > 0 else 0
        sod_pct = round(sodium / 2000 * 100)

        protein_msg = get_protein_verdict(protein_effective, protein_goal, meal_type)
        calorie_msg = get_calorie_verdict(calories, calorie_goal, meal_type)
        sugar_msg = get_sugar_verdict(sugar, sugar_limit, meal_type)
        overall = get_overall_verdict(
            protein_msg["verdict"],
            calorie_msg["verdict"],
            sugar_msg["verdict"],
            goal_type
        )

        return {
            "source": "matched",
            "match_score": match_result['score'],
            "food": {
                "id": row["id"],
                "name": row["name"],
                "manufacturer": row["manufacturer"],
                "category_small": category_small,
                "meal_type": meal_type,
                "serving_size": row["serving_size"],
                "barcode": barcode,
                "calories": calories,
                "protein_raw": protein_raw,
                "protein_effective": protein_effective,
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
            "messages": {
                "protein": protein_msg,
                "calorie": calorie_msg,
                "sugar": sugar_msg,
                "overall": overall
            },
            "stopper_note": {
                "protein_capped": protein_effective < protein_raw,
                "protein_cap_reason": f"{meal_type} 타입은 현실 기준 {protein_effective}g까지 인정" if protein_effective < protein_raw else None
            }
        }

    # 4. 매칭 실패 → Open Food Facts 데이터 그대로 반환
    return {
        "source": "openfoodfacts",
        "food": {
            "name": off_product['name'],
            "manufacturer": off_product['brand'],
            "barcode": barcode,
            "calories": off_product['calories'],
            "protein": off_product['protein'],
            "fat": off_product['fat'],
            "carbohydrate": off_product['carbohydrate'],
            "sugar": off_product['sugar'],
            "sodium": off_product['sodium'],
            "serving_size": off_product['serving_size'],
            "image_url": off_product.get('image_url'),
        },
        "note": "STOPPER DB에 없는 제품입니다. Open Food Facts 데이터를 표시합니다."
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


# ============== Recommendations ==============

@app.get("/api/recommendations/categories")
async def get_recommendation_categories():
    """추천용 소분류 목록 (벤치마크 포함)"""
    rows = await fetch_all("""
        SELECT cb.category_small, cb.category_medium, cb.category_large,
               cb.food_count,
               ROUND(cb.avg_protein::numeric, 1) as avg_protein,
               ROUND(cb.avg_sugar::numeric, 1) as avg_sugar,
               ROUND(cb.avg_calories::numeric, 0) as avg_calories,
               ROUND(cb.top25_protein_min::numeric, 1) as top25_protein_min
        FROM category_benchmarks cb
        WHERE cb.food_count >= 10
        ORDER BY cb.food_count DESC
        LIMIT 50
    """)
    return {
        "categories": [
            {
                "name": r["category_small"],
                "medium": r["category_medium"],
                "large": r["category_large"],
                "count": r["food_count"],
                "avg": {
                    "protein": float(r["avg_protein"] or 0),
                    "sugar": float(r["avg_sugar"] or 0),
                    "calories": float(r["avg_calories"] or 0)
                },
                "top25_protein": float(r["top25_protein_min"] or 0)
            }
            for r in rows
        ]
    }


@app.get("/api/recommendations/{category_small}")
async def get_recommendations(
    category_small: str,
    goal: str = Query("bulk", description="목표: bulk, diet, diabetes, maintain"),
    limit: int = Query(10, le=50),
    convenience_only: bool = Query(True, description="편의점 간편식만 (도시락/김밥/샌드위치 등)")
):
    """카테고리 내 추천 제품 목록

    - bulk: 단백질 높은 순
    - diet: 칼로리 낮은 순 (단백질 유지)
    - diabetes: 당류 낮은 순
    - maintain: 균형 (칼로리 적당, 나트륨 낮음)
    - convenience_only: 편의점/1인가구 간편식으로 필터링
    """
    # 벤치마크 조회
    benchmark = await fetch_one("""
        SELECT * FROM category_benchmarks WHERE category_small = $1
    """, category_small)

    if not benchmark:
        raise HTTPException(404, "Category not found")

    # 소분류별 1인분 기준 가져오기
    serving_rule = get_serving_rule(category_small)
    min_cal = serving_rule["min_cal"]
    max_cal = serving_rule["max_cal"]
    max_protein = serving_rule.get("max_protein", 60)  # 카테고리별 단백질 상한 (기본 60g)

    # 1인분 필터 (소분류별 맞춤 칼로리 범위 + 단백질 이상치 제외)
    # + 묶음 데이터 제외 (단백질 비율이 비정상적으로 높은 경우)
    # + 카테고리별 단백질 상한 (빵류는 25g, 과자는 30g 등)
    serving_filter = f"""
        AND protein < {max_protein}
        AND calories BETWEEN {min_cal} AND {max_cal}
        AND sodium < 5000
        AND (protein * 4.0 / NULLIF(calories, 0) * 100) < 55
        AND (
            name LIKE '%프로틴%' OR name LIKE '%단백질%' OR name LIKE '%protein%'
            OR (protein * 4.0 / NULLIF(calories, 0) * 100) < 35
        )
    """

    # 편의점 간편식 필터 (도시락, 김밥, 샌드위치 등)
    if convenience_only:
        convenience_filter = """
            AND (
                name LIKE '%도시락%' OR name LIKE '%김밥%' OR name LIKE '%삼각%'
                OR name LIKE '%컵밥%' OR name LIKE '%샌드위치%' OR name LIKE '%샐러드%'
                OR name LIKE '%볼%' OR name LIKE '%bowl%' OR name LIKE '%덮밥%'
                OR name LIKE '%햄버거%' OR name LIKE '%버거%' OR name LIKE '%파스타%'
            )
        """
    else:
        convenience_filter = ""

    # 목표별 정렬 및 필터
    if goal == "bulk":
        order_by = "protein DESC"
        where_extra = ""
    elif goal == "diet":
        order_by = "calories ASC"
        where_extra = "AND protein > 3"  # 최소 단백질 보장
    elif goal == "diabetes":
        order_by = "sugar ASC"
        where_extra = ""
    else:  # maintain
        order_by = "sodium ASC"
        where_extra = ""

    # 제품 조회
    rows = await fetch_all(f"""
        SELECT id, name, manufacturer, category_small,
               calories, protein, fat, carbohydrate, sugar, sodium, serving_size
        FROM foods
        WHERE category_small = $1 {serving_filter} {convenience_filter} {where_extra}
        ORDER BY {order_by}
        LIMIT $2
    """, category_small, limit)

    # 벤치마크 정보
    benchmark_info = {
        "category": category_small,
        "total_products": benchmark["food_count"],
        "avg_protein": float(benchmark["avg_protein"] or 0),
        "avg_sugar": float(benchmark["avg_sugar"] or 0),
        "avg_calories": float(benchmark["avg_calories"] or 0),
        "top25_protein_min": float(benchmark["top25_protein_min"] or 0),
        "top25_sugar_max": float(benchmark["top25_sugar_max"] or 0),
        "serving_range": f"{min_cal}-{max_cal}kcal (1인분 기준)"
    }

    # 제품 목록
    products = []
    for r in rows:
        # 벤치마크 대비 평가
        protein_vs_avg = round((float(r["protein"] or 0) / float(benchmark["avg_protein"])) * 100 - 100) if benchmark["avg_protein"] else 0
        sugar_vs_avg = round((float(r["sugar"] or 0) / float(benchmark["avg_sugar"])) * 100 - 100) if benchmark["avg_sugar"] else 0

        products.append({
            "id": r["id"],
            "name": r["name"],
            "manufacturer": r["manufacturer"],
            "calories": float(r["calories"] or 0),
            "protein": float(r["protein"] or 0),
            "sugar": float(r["sugar"] or 0),
            "sodium": float(r["sodium"] or 0),
            "serving_size": r["serving_size"],
            "vs_category": {
                "protein": f"+{protein_vs_avg}%" if protein_vs_avg > 0 else f"{protein_vs_avg}%",
                "sugar": f"+{sugar_vs_avg}%" if sugar_vs_avg > 0 else f"{sugar_vs_avg}%"
            },
            "is_top25_protein": float(r["protein"] or 0) >= float(benchmark["top25_protein_min"] or 0)
        })

    return {
        "goal": goal,
        "benchmark": benchmark_info,
        "products": products,
        "message": _get_recommendation_message(goal, benchmark_info)
    }


def _get_recommendation_message(goal: str, benchmark: dict) -> str:
    """추천 메시지 생성"""
    cat = benchmark["category"]
    if goal == "bulk":
        return f"💪 {cat} 중 단백질 TOP 제품이에요. 평균 {benchmark['avg_protein']}g 대비 더 높은 제품들!"
    elif goal == "diet":
        return f"🥗 {cat} 중 저칼로리 제품이에요. 평균 {benchmark['avg_calories']}kcal 이하!"
    elif goal == "diabetes":
        return f"🩺 {cat} 중 저당 제품이에요. 상위 25%는 {benchmark['top25_sugar_max']}g 이하!"
    else:
        return f"⚖️ {cat} 중 균형 잡힌 제품이에요."


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


# ============== Barcode Registration ==============

@app.get("/api/barcode/{barcode}/match", response_model=BarcodeMatchResponse)
async def match_barcode(barcode: str):
    """
    바코드 → I2570 → 편의점 DB 매칭

    1. I2570 API로 바코드 조회 → 제품명, 제조사
    2. 편의점 DB에서 제품명으로 매칭
    3. 매칭된 제품 정보 반환 (영양정보 포함)

    사용자는 바코드 스캔만 하면 자동으로 제품 정보를 받음
    """
    # 1. I2570 API 조회
    i2570_result = lookup_barcode_i2570(barcode)

    if not i2570_result:
        raise HTTPException(404, f"바코드 {barcode}를 I2570에서 찾을 수 없습니다")

    i2570_name = i2570_result['name']
    i2570_manufacturer = i2570_result['manufacturer']

    # 2. 편의점 DB 매칭
    cvs_product = match_convenience_product(i2570_name, i2570_manufacturer)

    if not cvs_product:
        return BarcodeMatchResponse(
            barcode=barcode,
            i2570_name=i2570_name,
            i2570_manufacturer=i2570_manufacturer,
            matched=False,
            product=None
        )

    # 3. 매칭 성공
    return BarcodeMatchResponse(
        barcode=barcode,
        i2570_name=i2570_name,
        i2570_manufacturer=i2570_manufacturer,
        matched=True,
        product=ConvenienceProduct(**cvs_product)
    )


@app.post("/api/barcode/quick-register", response_model=ProductRegisterResponse)
async def quick_register_barcode(barcode: str, product: ConvenienceProduct):
    """
    편의점 제품 원클릭 등록

    - 편의점 DB의 영양정보를 그대로 STOPPER DB에 저장
    - 사용자는 타이핑/입력 없이 확인만 누르면 됨
    """
    # 기존 제품 확인
    existing = await fetch_one("SELECT id FROM foods WHERE barcode = $1", barcode)

    if existing:
        raise HTTPException(400, "이미 등록된 바코드입니다")

    # 새로 삽입
    food_id = await fetch_val("""
        INSERT INTO foods (
            name, manufacturer, serving_size, barcode,
            calories, protein, fat, carbohydrate, sugar, sodium, saturated_fat
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING id
    """, product.name, product.manufacturer, product.serving_size, barcode,
        product.calories, product.protein, product.fat, product.carbohydrate,
        product.sugar, product.sodium, product.saturated_fat)

    return ProductRegisterResponse(
        id=food_id,
        barcode=barcode,
        name=product.name,
        message="편의점 제품이 등록되었습니다"
    )


@app.get("/api/barcode/{barcode}/lookup", response_model=BarcodeLookupResponse)
async def lookup_barcode(barcode: str):
    """
    I2570 API로 바코드 조회 (제품명 자동 입력용)

    - 바코드로 I2570 검색
    - 제품명, 제조사 정보 반환
    - 등록 화면에서 자동으로 제품명 채우기
    """
    # I2570 API 조회
    result = lookup_barcode_i2570(barcode)

    if result:
        return BarcodeLookupResponse(
            barcode=barcode,
            name=result['name'],
            manufacturer=result['manufacturer'],
            found=True
        )
    else:
        return BarcodeLookupResponse(
            barcode=barcode,
            name=None,
            manufacturer=None,
            found=False
        )


@app.post("/api/barcode/register", response_model=ProductRegisterResponse)
async def register_product(req: ProductRegisterRequest):
    """
    바코드 제품 등록

    1. 바코드로 기존 제품 확인
    2. 있으면 업데이트, 없으면 삽입
    3. STOPPER DB에 저장
    """
    # 기존 제품 확인
    existing = await fetch_one("SELECT id FROM foods WHERE barcode = $1", req.barcode)

    if existing:
        # 업데이트
        await execute("""
            UPDATE foods SET
                name = $1,
                manufacturer = $2,
                category_small = $3,
                serving_size = $4,
                calories = $5,
                protein = $6,
                fat = $7,
                carbohydrate = $8,
                sugar = $9,
                sodium = $10,
                saturated_fat = $11
            WHERE barcode = $12
        """, req.name, req.manufacturer, req.category_small, req.serving_size,
            req.calories, req.protein, req.fat, req.carbohydrate,
            req.sugar, req.sodium, req.saturated_fat, req.barcode)

        return ProductRegisterResponse(
            id=existing['id'],
            barcode=req.barcode,
            name=req.name,
            message="제품 정보가 업데이트되었습니다"
        )
    else:
        # 새로 삽입
        food_id = await fetch_val("""
            INSERT INTO foods (
                name, manufacturer, category_small, serving_size, barcode,
                calories, protein, fat, carbohydrate, sugar, sodium, saturated_fat
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """, req.name, req.manufacturer, req.category_small, req.serving_size, req.barcode,
            req.calories, req.protein, req.fat, req.carbohydrate,
            req.sugar, req.sodium, req.saturated_fat)

        return ProductRegisterResponse(
            id=food_id,
            barcode=req.barcode,
            name=req.name,
            message="새 제품이 등록되었습니다"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
