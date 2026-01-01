"""
편의점 제품명 → I2570 바코드 조회 테스트
"""
import json
import requests
import re

API_KEY = "14588a0a32f2476a8797"
API_BASE = "http://openapi.foodsafetykorea.go.kr/api"
SERVICE_NAME = "I2570"

def parse_product_name(full_name):
    """삼립)메가불고기버터갈릭버거 → manufacturer='삼립', name='메가불고기버터갈릭버거'"""
    if ')' in full_name:
        parts = full_name.split(')', 1)
        return parts[0].strip(), parts[1].strip()
    return None, full_name.strip()

def extract_keywords(product_name):
    """메가불고기버터갈릭버거 → ['불고기버거', '불고기', '버거'] 등"""
    # 숫자, 특수문자 제거
    cleaned = re.sub(r'[0-9]+', '', product_name)
    cleaned = re.sub(r'[^\w가-힣]', '', cleaned)

    keywords = []

    # 주요 음식 키워드
    food_patterns = [
        r'불고기.*?버거', r'치킨.*?버거', r'버거',
        r'김밥', r'도시락', r'샌드위치', r'샌드',
        r'파스타', r'삼각', r'치즈독',
        r'불고기', r'치킨', r'제육', r'딸기'
    ]

    for pattern in food_patterns:
        match = re.search(pattern, cleaned)
        if match:
            keywords.append(match.group())

    # 중복 제거, 긴 키워드 우선
    keywords = sorted(set(keywords), key=len, reverse=True)

    return keywords[:5] if keywords else [cleaned]

def search_i2570(keyword, max_results=100):
    """I2570 API로 제품명 검색"""
    url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/1/{max_results}/PRDT_NM={keyword}"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        if SERVICE_NAME not in data:
            return []

        items = data[SERVICE_NAME].get('row', [])
        return items
    except Exception as e:
        print(f"   ❌ API 오류: {e}")
        return []

def main():
    print("📦 편의점 제품명 → I2570 바코드 조회 테스트\n")

    # 편의점 데이터 로드
    with open('/Users/js/Downloads/products.json', 'r') as f:
        cvs_products = json.load(f)

    results = {
        'found': 0,
        'not_found': 0,
        'details': []
    }

    for cvs in cvs_products:
        cvs_name = cvs['name']
        manufacturer, product_name = parse_product_name(cvs_name)

        print(f"🔍 {cvs_name}")
        if manufacturer:
            print(f"   제조사: {manufacturer} / 제품명: {product_name}")

        # 키워드 추출
        keywords = extract_keywords(product_name)
        print(f"   검색 키워드: {keywords}")

        # 각 키워드로 검색
        all_matches = []
        for keyword in keywords:
            matches = search_i2570(keyword)
            if matches:
                print(f"   📥 '{keyword}' 검색 → {len(matches)}개 결과")
                all_matches.extend(matches)

            # 첫 번째 키워드에서 결과 나오면 충분
            if all_matches:
                break

        if all_matches:
            # 제조사 일치 우선
            best_match = None

            if manufacturer:
                for item in all_matches:
                    item_company = item.get('CMPNY_NM', '').strip()
                    if manufacturer.lower() in item_company.lower() or item_company.lower() in manufacturer.lower():
                        best_match = item
                        break

            # 제조사 매칭 안되면 첫 번째 결과
            if not best_match:
                best_match = all_matches[0]

            barcode = best_match.get('BRCD_NO', '').strip()
            matched_name = best_match.get('PRDT_NM', '').strip()
            matched_company = best_match.get('CMPNY_NM', '').strip()

            print(f"   ✅ 바코드 발견: {barcode}")
            print(f"      매칭 제품: {matched_name}")
            print(f"      제조사: {matched_company}")

            results['found'] += 1
            results['details'].append({
                'cvs_name': cvs_name,
                'barcode': barcode,
                'matched_name': matched_name,
                'matched_company': matched_company,
                'total_candidates': len(all_matches)
            })
        else:
            print(f"   ❌ 바코드 없음 (I2570에서 검색 결과 없음)")
            results['not_found'] += 1
            results['details'].append({
                'cvs_name': cvs_name,
                'barcode': None
            })

        print()

    # 결과 요약
    print("\n" + "="*60)
    print("📊 바코드 조회 결과 요약")
    print("="*60)
    print(f"✅ 바코드 발견:    {results['found']}개")
    print(f"❌ 바코드 없음:    {results['not_found']}개")
    print()

    success_rate = (results['found'] / len(cvs_products)) * 100 if cvs_products else 0
    print(f"💡 바코드 조회 성공률: {success_rate:.1f}% ({results['found']}/{len(cvs_products)})")
    print()

    if results['found'] > 0:
        print("✅ I2570 API로 바코드 조회 가능!")
        print("   → 편의점 제품명으로 바코드를 얻을 수 있습니다.")
        print("   → 영양정보는 외부에서 수집 후 STOPPER DB에 바코드와 함께 저장하면 됩니다.")

    if results['not_found'] > 0:
        print(f"⚠️  {results['not_found']}개 제품은 I2570에 없습니다.")
        print("   → 최신 제품이거나 I2570 DB에 미등록된 제품일 수 있습니다.")

if __name__ == '__main__':
    main()
