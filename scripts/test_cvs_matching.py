"""
편의점 크롤링 데이터 ↔ STOPPER DB 매칭 테스트
"""
import asyncio
import asyncpg
import json
import re

def parse_product_name(full_name):
    """
    '삼립)메가불고기버터갈릭버거' → manufacturer='삼립', name='메가불고기버터갈릭버거'
    """
    if ')' in full_name:
        parts = full_name.split(')', 1)
        return parts[0].strip(), parts[1].strip()
    return None, full_name.strip()

def normalize_text(text):
    if not text:
        return ""
    normalized = text.lower().strip()
    normalized = re.sub(r'\([^)]*\)', '', normalized)
    normalized = re.sub(r'\[[^\]]*\]', '', normalized)
    normalized = re.sub(r'\d+\.?\d*(g|ml|kg|l|mg|개|입|ea|EA)', '', normalized)
    normalized = re.sub(r'[^\w가-힣]', '', normalized)
    return normalized

def extract_tokens(text):
    if not text:
        return []
    normalized = normalize_text(text)
    tokens = []
    korean_tokens = re.findall(r'[가-힣]{2,}', normalized)
    tokens.extend(korean_tokens)
    english_tokens = re.findall(r'[a-z]{3,}', normalized)
    tokens.extend(english_tokens)
    tokens = [t for t in tokens if not t.isdigit()]
    return list(set(tokens))

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("📦 편의점 크롤링 데이터 ↔ STOPPER DB 매칭 테스트\n")

    # 편의점 데이터 로드
    with open('/Users/js/Downloads/products.json', 'r') as f:
        cvs_products = json.load(f)

    print(f"편의점 제품: {len(cvs_products)}개\n")

    results = {
        'exact_match': 0,
        'fuzzy_match': 0,
        'manufacturer_match': 0,
        'no_match': 0,
        'details': []
    }

    for cvs in cvs_products:
        cvs_name = cvs['name']
        manufacturer, product_name = parse_product_name(cvs_name)

        print(f"🔍 {cvs_name}")
        if manufacturer:
            print(f"   제조사: {manufacturer} / 제품명: {product_name}")

        # 1차: 정확한 이름 매칭
        exact = await conn.fetchrow("""
            SELECT id, name, manufacturer, calories, protein, sugar, sodium
            FROM foods
            WHERE name ILIKE $1
            LIMIT 1
        """, f"%{product_name}%")

        if exact:
            print(f"   ✅ EXACT MATCH: {exact['name']}")
            print(f"      영양정보: {exact['calories']}kcal, 단백질 {exact['protein']}g, 당 {exact['sugar']}g")
            results['exact_match'] += 1
            results['details'].append({
                'cvs_name': cvs_name,
                'match_type': 'exact',
                'matched_name': exact['name'],
                'nutrition': {
                    'calories': exact['calories'],
                    'protein': exact['protein'],
                    'sugar': exact['sugar'],
                    'sodium': exact['sodium']
                }
            })
            print()
            continue

        # 2차: 제조사 + 토큰 매칭
        if manufacturer:
            manufacturer_norm = normalize_text(manufacturer)
            tokens = extract_tokens(product_name)

            fuzzy = await conn.fetchrow("""
                SELECT id, name, manufacturer, calories, protein, sugar, sodium
                FROM foods
                WHERE manufacturer_norm = $1
                  AND tokens && $2
                ORDER BY array_length(tokens, 1) DESC
                LIMIT 1
            """, manufacturer_norm, tokens)

            if fuzzy:
                print(f"   🟡 FUZZY MATCH: {fuzzy['name']}")
                print(f"      영양정보: {fuzzy['calories']}kcal, 단백질 {fuzzy['protein']}g, 당 {fuzzy['sugar']}g")
                results['fuzzy_match'] += 1
                results['details'].append({
                    'cvs_name': cvs_name,
                    'match_type': 'fuzzy',
                    'matched_name': fuzzy['name'],
                    'nutrition': {
                        'calories': fuzzy['calories'],
                        'protein': fuzzy['protein'],
                        'sugar': fuzzy['sugar'],
                        'sodium': fuzzy['sodium']
                    }
                })
                print()
                continue

            # 3차: 제조사만 매칭 (토큰 없이)
            mfr_only = await conn.fetchrow("""
                SELECT id, name, manufacturer, calories, protein, sugar, sodium
                FROM foods
                WHERE manufacturer_norm = $1
                LIMIT 1
            """, manufacturer_norm)

            if mfr_only:
                print(f"   🟠 MANUFACTURER ONLY: {mfr_only['name']}")
                print(f"      영양정보: {mfr_only['calories']}kcal, 단백질 {mfr_only['protein']}g, 당 {mfr_only['sugar']}g")
                results['manufacturer_match'] += 1
                results['details'].append({
                    'cvs_name': cvs_name,
                    'match_type': 'manufacturer_only',
                    'matched_name': mfr_only['name'],
                    'nutrition': {
                        'calories': mfr_only['calories'],
                        'protein': mfr_only['protein'],
                        'sugar': mfr_only['sugar'],
                        'sodium': mfr_only['sodium']
                    }
                })
                print()
                continue

        # 4차: 매칭 실패
        print(f"   ❌ NO MATCH")
        results['no_match'] += 1
        results['details'].append({
            'cvs_name': cvs_name,
            'match_type': 'none',
            'matched_name': None,
            'nutrition': None
        })
        print()

    # 결과 요약
    print("\n" + "="*60)
    print("📊 매칭 결과 요약")
    print("="*60)
    print(f"✅ EXACT MATCH (정확한 이름):        {results['exact_match']}개")
    print(f"🟡 FUZZY MATCH (제조사+토큰):        {results['fuzzy_match']}개")
    print(f"🟠 MANUFACTURER ONLY (제조사만):     {results['manufacturer_match']}개")
    print(f"❌ NO MATCH (매칭 실패):             {results['no_match']}개")
    print()

    total_with_nutrition = results['exact_match'] + results['fuzzy_match'] + results['manufacturer_match']
    match_rate = (total_with_nutrition / len(cvs_products)) * 100 if cvs_products else 0

    print(f"💡 영양정보 매칭률: {match_rate:.1f}% ({total_with_nutrition}/{len(cvs_products)})")
    print()

    if results['exact_match'] > 0:
        print("✅ EXACT MATCH가 있으므로 일부 제품은 정확히 매칭 가능!")
    if results['fuzzy_match'] > 0:
        print("🟡 FUZZY MATCH가 있으므로 유사 제품으로 대체 가능!")
    if results['no_match'] == len(cvs_products):
        print("❌ 매칭되는 제품이 없습니다. STOPPER DB에 편의점 최신 제품 데이터가 부족합니다.")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
