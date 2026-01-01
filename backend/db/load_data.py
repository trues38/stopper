"""가공식품 CSV → PostgreSQL 로드"""

import asyncio
import asyncpg
import pandas as pd
import os
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://stopper:stopper2026@localhost:5432/stopper"
)

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "가공식품_lite.csv"


async def create_schema(conn):
    """스키마 생성"""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema = f.read()
    await conn.execute(schema)
    print("✓ Schema created")


async def load_foods(conn):
    """가공식품 데이터 로드"""
    print(f"Loading data from: {DATA_PATH}")

    # CSV 읽기
    df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')
    print(f"Total rows: {len(df)}")

    # 컬럼 매핑
    df = df.rename(columns={
        '식품코드': 'food_code',
        '식품명': 'name',
        '식품대분류명': 'category_large',
        '식품중분류명': 'category_medium',
        '에너지(kcal)': 'calories',
        '단백질(g)': 'protein',
        '지방(g)': 'fat',
        '탄수화물(g)': 'carbohydrate',
        '당류(g)': 'sugar',
        '나트륨(mg)': 'sodium',
        '포화지방산(g)': 'saturated_fat',
        '제조사명': 'manufacturer',
        '1회섭취참고량': 'serving_size'
    })

    # 결측값 처리
    df = df.fillna({
        'calories': 0,
        'protein': 0,
        'fat': 0,
        'carbohydrate': 0,
        'sugar': 0,
        'sodium': 0,
        'saturated_fat': 0,
        'manufacturer': '',
        'category_large': '',
        'category_medium': '',
        'serving_size': ''
    })

    # 식품명 앞의 BOM 제거
    df['name'] = df['name'].str.replace('\ufeff', '').str.strip()

    # 배치 삽입
    batch_size = 5000
    total = len(df)

    for i in range(0, total, batch_size):
        batch = df.iloc[i:i+batch_size]

        # 데이터 준비
        records = [
            (
                row['food_code'],
                row['name'],
                row['manufacturer'],
                row['category_large'],
                row['category_medium'],
                float(row['calories']),
                float(row['protein']),
                float(row['fat']),
                float(row['carbohydrate']),
                float(row['sugar']),
                float(row['sodium']),
                float(row['saturated_fat']),
                row['serving_size']
            )
            for _, row in batch.iterrows()
        ]

        # 배치 삽입
        await conn.executemany('''
            INSERT INTO foods (
                food_code, name, manufacturer,
                category_large, category_medium,
                calories, protein, fat, carbohydrate,
                sugar, sodium, saturated_fat, serving_size
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (food_code) DO NOTHING
        ''', records)

        print(f"  Loaded {min(i + batch_size, total)}/{total} ({(min(i + batch_size, total))*100//total}%)")

    # 최종 카운트
    count = await conn.fetchval("SELECT COUNT(*) FROM foods")
    print(f"✓ Foods loaded: {count:,} items")


async def load_seed_combinations(conn):
    """시드 조합 데이터 로드 (Neo4j-ready 구조)"""
    import json
    import uuid
    from datetime import datetime

    def gen_combo_id(suffix):
        return f"combo_seed_{suffix}"

    seed_combos = [
        {
            "combo_id": gen_combo_id("001"),
            "name": "단백질 폭탄 세트",
            "description": "한 끼 단백질 50g+",
            "author_id": "user_stopper_official",
            "items": [
                {"food_id": "food_sample_1", "name": "닭가슴살바", "qty": 1, "calories": 180, "protein": 25, "sugar": 2, "sodium": 300},
                {"food_id": "food_sample_2", "name": "프로틴 음료", "qty": 1, "calories": 150, "protein": 20, "sugar": 3, "sodium": 200},
                {"food_id": "food_sample_3", "name": "삶은계란 2구", "qty": 1, "calories": 140, "protein": 12, "sugar": 1, "sodium": 150}
            ],
            "intent": {"goal": "bulk", "target_protein": 50, "limit_sugar": 20},
            "result": {"calories": 470, "protein": 57, "sugar": 6, "sodium": 650, "percent_of_daily": 24},
            "signals": {"worked": None, "repeat_count": 0, "next_combo_hint": None},
            "tags": ["벌크업", "고단백", "헬스"],
            "is_official": True
        },
        {
            "combo_id": gen_combo_id("002"),
            "name": "저칼로리 점심 세트",
            "description": "400kcal 이하로 배부르게",
            "author_id": "user_stopper_official",
            "items": [
                {"food_id": "food_sample_4", "name": "닭가슴살 샐러드", "qty": 1, "calories": 250, "protein": 22, "sugar": 4, "sodium": 400},
                {"food_id": "food_sample_5", "name": "제로콜라", "qty": 1, "calories": 0, "protein": 0, "sugar": 0, "sodium": 20}
            ],
            "intent": {"goal": "diet", "target_calories": 400, "limit_sugar": 15},
            "result": {"calories": 250, "protein": 22, "sugar": 4, "sodium": 420, "percent_of_daily": 13},
            "signals": {"worked": None, "repeat_count": 0, "next_combo_hint": None},
            "tags": ["다이어트", "저칼로리", "점심"],
            "is_official": True
        },
        {
            "combo_id": gen_combo_id("003"),
            "name": "당뇨 안심 세트",
            "description": "당류 10g 이하",
            "author_id": "user_stopper_official",
            "items": [
                {"food_id": "food_sample_6", "name": "닭가슴살", "qty": 1, "calories": 165, "protein": 31, "sugar": 0, "sodium": 350},
                {"food_id": "food_sample_7", "name": "무가당 두유", "qty": 1, "calories": 80, "protein": 8, "sugar": 2, "sodium": 100},
                {"food_id": "food_sample_8", "name": "견과류", "qty": 1, "calories": 180, "protein": 5, "sugar": 3, "sodium": 50}
            ],
            "intent": {"goal": "diabetes", "limit_sugar": 10, "limit_sodium": 800},
            "result": {"calories": 425, "protein": 44, "sugar": 5, "sodium": 500, "percent_of_daily": 21},
            "signals": {"worked": None, "repeat_count": 0, "next_combo_hint": None},
            "tags": ["당뇨", "저당", "안심"],
            "is_official": True
        },
        {
            "combo_id": gen_combo_id("004"),
            "name": "야식 참기 세트",
            "description": "100kcal 이하 간식",
            "author_id": "user_stopper_official",
            "items": [
                {"food_id": "food_sample_9", "name": "곤약젤리", "qty": 1, "calories": 15, "protein": 0, "sugar": 2, "sodium": 10},
                {"food_id": "food_sample_10", "name": "제로음료", "qty": 1, "calories": 0, "protein": 0, "sugar": 0, "sodium": 15}
            ],
            "intent": {"goal": "diet", "target_calories": 100, "limit_sugar": 10},
            "result": {"calories": 15, "protein": 0, "sugar": 2, "sodium": 25, "percent_of_daily": 1},
            "signals": {"worked": None, "repeat_count": 0, "next_combo_hint": None},
            "tags": ["다이어트", "야식", "간식"],
            "is_official": True
        },
        {
            "combo_id": gen_combo_id("005"),
            "name": "가성비 단백질",
            "description": "5천원 이하 단백질 40g",
            "author_id": "user_stopper_official",
            "items": [
                {"food_id": "food_sample_11", "name": "닭가슴살 삼각김밥", "qty": 1, "calories": 200, "protein": 12, "sugar": 3, "sodium": 400},
                {"food_id": "food_sample_12", "name": "단백질바", "qty": 1, "calories": 200, "protein": 20, "sugar": 5, "sodium": 150}
            ],
            "intent": {"goal": "bulk", "target_protein": 40},
            "result": {"calories": 400, "protein": 32, "sugar": 8, "sodium": 550, "percent_of_daily": 20},
            "signals": {"worked": None, "repeat_count": 0, "next_combo_hint": None},
            "tags": ["고단백", "가성비", "편의점"],
            "is_official": True
        }
    ]

    for combo in seed_combos:
        await conn.execute('''
            INSERT INTO combinations (
                combo_id, name, description, author_id,
                items, intent, result, signals, tags, is_official
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (combo_id) DO NOTHING
        ''',
            combo["combo_id"],
            combo["name"],
            combo["description"],
            combo["author_id"],
            json.dumps(combo["items"]),
            json.dumps(combo["intent"]),
            json.dumps(combo["result"]),
            json.dumps(combo["signals"]),
            combo["tags"],
            combo["is_official"]
        )

    count = await conn.fetchval("SELECT COUNT(*) FROM combinations")
    print(f"✓ Seed combinations loaded: {count} items")


async def main():
    """메인 실행"""
    print("=" * 50)
    print("🛑 STOPPER - Database Setup")
    print("=" * 50)

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        await create_schema(conn)
        await load_foods(conn)
        await load_seed_combinations(conn)

        print("=" * 50)
        print("✓ Database setup complete!")
        print("=" * 50)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
