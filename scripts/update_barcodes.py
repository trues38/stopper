"""
Barcode 컬럼 추가 및 매칭 데이터 업데이트
"""

import asyncio
import asyncpg
import json

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    # 1. barcode 컬럼 추가 (이미 있으면 스킵)
    print("🔧 barcode 컬럼 추가 중...")
    try:
        await conn.execute('''
            ALTER TABLE foods
            ADD COLUMN IF NOT EXISTS barcode VARCHAR(20)
        ''')
        print("✅ barcode 컬럼 추가 완료")
    except Exception as e:
        print(f"⚠️ 컬럼 추가 오류 (이미 있을 수 있음): {e}")

    # 2. 인덱스 생성
    print("🔧 barcode 인덱스 생성 중...")
    try:
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_foods_barcode
            ON foods(barcode)
        ''')
        print("✅ 인덱스 생성 완료")
    except Exception as e:
        print(f"⚠️ 인덱스 생성 오류: {e}")

    # 3. 매칭 결과 로드
    print("\n📂 매칭 결과 로드 중...")
    with open('/Users/js/Documents/stopper/data/barcode_matches.json', 'r', encoding='utf-8') as f:
        matches = json.load(f)

    print(f"📦 {len(matches)}개 매칭 데이터 로드 완료")

    # 4. 바코드 업데이트
    print("\n🔄 바코드 업데이트 중...")
    updated = 0

    for match in matches:
        food_id = match['food_id']
        barcode = match['barcode']

        try:
            await conn.execute('''
                UPDATE foods
                SET barcode = $1
                WHERE id = $2
            ''', barcode, food_id)
            updated += 1
            print(f"  ✅ {barcode} → {match['food_name'][:40]}")
        except Exception as e:
            print(f"  ❌ 업데이트 실패 [{food_id}]: {e}")

    print(f"\n✅ 총 {updated}개 바코드 업데이트 완료")

    # 5. 검증
    print("\n🔍 업데이트 검증 중...")
    count = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE barcode IS NOT NULL")
    print(f"📊 barcode가 있는 제품: {count}개")

    # 샘플 확인
    samples = await conn.fetch('''
        SELECT id, name, barcode, manufacturer
        FROM foods
        WHERE barcode IS NOT NULL
        LIMIT 5
    ''')

    print("\n📊 샘플 데이터:")
    for s in samples:
        print(f"  {s['barcode']:13s} | {s['name'][:40]:40s} | {s['manufacturer']}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
