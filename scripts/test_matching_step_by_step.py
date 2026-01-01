"""
매칭 스크립트 디버그 - 단계별 테스트
"""
import asyncio
import asyncpg

async def main():
    print("1. DB 연결 중...")
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')
    print("   ✅ 연결 완료\n")

    print("2. 정규화 상태 확인...")
    normalized = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE name_norm IS NOT NULL")
    total = await conn.fetchval("SELECT COUNT(*) FROM foods")
    print(f"   ✅ {normalized:,}/{total:,} 정규화됨\n")

    print("3. 샘플 식약처 바코드로 후보 찾기 테스트...")

    # 테스트용 샘플 데이터
    test_name = "황금빛하늘내린황태포5미370g"
    test_company = "용대황태연합단대륙영농조합법인"
    test_barcode = "8809360172547"

    print(f"   테스트 제품: {test_name}")
    print(f"   제조사: {test_company}\n")

    # 정규화
    import re
    def normalize_text(text):
        if not text:
            return ""
        normalized = text.lower().strip()
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)
        normalized = re.sub(r'\d+\.?\d*(g|ml|kg|l|mg|개|입|ea|EA)', '', normalized)
        normalized = re.sub(r'[^\w가-힣]', '', normalized)
        return normalized

    name_norm = normalize_text(test_name)
    company_norm = normalize_text(test_company)
    print(f"   정규화된 이름: {name_norm}")
    print(f"   정규화된 제조사: {company_norm}\n")

    print("4. 제조사로 후보 찾기...")
    try:
        candidates = await conn.fetch("""
            SELECT id, name, manufacturer
            FROM foods
            WHERE manufacturer_norm = $1
            LIMIT 10
        """, company_norm)
        print(f"   ✅ {len(candidates)}개 후보 발견")
        for c in candidates[:3]:
            print(f"      - {c['name'][:50]}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    print("\n5. similarity 함수 테스트...")
    try:
        result = await conn.fetchrow("""
            SELECT id, name, similarity(name_norm, $1) as sim
            FROM foods
            WHERE similarity(name_norm, $1) > 0.3
            ORDER BY sim DESC
            LIMIT 1
        """, name_norm)
        if result:
            print(f"   ✅ 가장 유사한 제품: {result['name'][:50]} (유사도: {result['sim']:.2f})")
        else:
            print("   ⚠️  유사한 제품 없음")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    print("\n✅ 모든 테스트 완료!")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
