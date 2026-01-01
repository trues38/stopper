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

# xlsx 파일 (24만건 전체)
DATA_PATH = Path(__file__).parent.parent.parent / "data" / "20251230_가공식품DB_244834건.xlsx"


async def create_schema(conn):
    """스키마 생성"""
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema = f.read()
    await conn.execute(schema)
    print("✓ Schema created")


async def load_foods(conn):
    """가공식품 데이터 로드 (xlsx 24만건)"""
    print(f"Loading data from: {DATA_PATH}")

    # xlsx 읽기
    df = pd.read_excel(DATA_PATH)
    print(f"Total rows: {len(df):,}")

    # 컬럼 매핑
    df = df.rename(columns={
        '식품코드': 'food_code',
        '식품명': 'name',
        '식품대분류명': 'category_large',
        '식품중분류명': 'category_medium',
        '식품소분류명': 'category_small',
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
        'category_small': '',
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
                str(row['food_code']),
                str(row['name']),
                str(row['manufacturer']),
                str(row['category_large']),
                str(row['category_medium']),
                str(row['category_small']),
                float(row['calories']),
                float(row['protein']),
                float(row['fat']),
                float(row['carbohydrate']),
                float(row['sugar']),
                float(row['sodium']),
                float(row['saturated_fat']),
                str(row['serving_size'])
            )
            for _, row in batch.iterrows()
        ]

        # 배치 삽입
        await conn.executemany('''
            INSERT INTO foods (
                food_code, name, manufacturer,
                category_large, category_medium, category_small,
                calories, protein, fat, carbohydrate,
                sugar, sodium, saturated_fat, serving_size
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (food_code) DO NOTHING
        ''', records)

        print(f"  Loaded {min(i + batch_size, total):,}/{total:,} ({(min(i + batch_size, total))*100//total}%)")

    # 최종 카운트
    count = await conn.fetchval("SELECT COUNT(*) FROM foods")
    print(f"✓ Foods loaded: {count:,} items")


async def calculate_benchmarks(conn):
    """카테고리별 벤치마크 계산"""
    print("Calculating category benchmarks...")

    # 소분류별 통계 계산
    await conn.execute('''
        INSERT INTO category_benchmarks (
            category_small, category_medium, category_large, food_count,
            avg_calories, avg_protein, avg_sugar, avg_sodium,
            top25_protein_min, top25_sugar_max, top25_sodium_max
        )
        SELECT
            category_small,
            MAX(category_medium) as category_medium,
            MAX(category_large) as category_large,
            COUNT(*) as food_count,
            AVG(calories) as avg_calories,
            AVG(protein) as avg_protein,
            AVG(sugar) as avg_sugar,
            AVG(sodium) as avg_sodium,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY protein) as top25_protein_min,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sugar) as top25_sugar_max,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sodium) as top25_sodium_max
        FROM foods
        WHERE category_small IS NOT NULL AND category_small != ''
        GROUP BY category_small
        ON CONFLICT (category_small) DO UPDATE SET
            food_count = EXCLUDED.food_count,
            avg_calories = EXCLUDED.avg_calories,
            avg_protein = EXCLUDED.avg_protein,
            avg_sugar = EXCLUDED.avg_sugar,
            avg_sodium = EXCLUDED.avg_sodium,
            top25_protein_min = EXCLUDED.top25_protein_min,
            top25_sugar_max = EXCLUDED.top25_sugar_max,
            top25_sodium_max = EXCLUDED.top25_sodium_max,
            updated_at = NOW()
    ''')

    # 최고 단백질 제품 업데이트
    await conn.execute('''
        UPDATE category_benchmarks cb
        SET best_protein_food_id = (
            SELECT id FROM foods f
            WHERE f.category_small = cb.category_small
            ORDER BY f.protein DESC
            LIMIT 1
        )
    ''')

    # 최저 당류 제품 업데이트
    await conn.execute('''
        UPDATE category_benchmarks cb
        SET best_lowsugar_food_id = (
            SELECT id FROM foods f
            WHERE f.category_small = cb.category_small AND f.sugar >= 0
            ORDER BY f.sugar ASC
            LIMIT 1
        )
    ''')

    # 최저 나트륨 제품 업데이트
    await conn.execute('''
        UPDATE category_benchmarks cb
        SET best_lowsodium_food_id = (
            SELECT id FROM foods f
            WHERE f.category_small = cb.category_small AND f.sodium >= 0
            ORDER BY f.sodium ASC
            LIMIT 1
        )
    ''')

    count = await conn.fetchval("SELECT COUNT(*) FROM category_benchmarks")
    print(f"✓ Benchmarks calculated: {count} categories")


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
        await calculate_benchmarks(conn)
        await load_seed_combinations(conn)

        print("=" * 50)
        print("✓ Database setup complete!")
        print("=" * 50)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
