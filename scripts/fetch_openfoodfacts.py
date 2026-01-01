"""
Open Food Facts 한국 제품 데이터 다운로드 및 매칭

1. Open Food Facts API로 한국 제품 검색
2. 제품명 기반 STOPPER DB 매칭
3. barcode 업데이트
"""

import asyncio
import asyncpg
import requests
import json
from difflib import SequenceMatcher
from urllib.parse import quote

# Open Food Facts API
OFF_API = "https://kr.openfoodfacts.org"
OFF_SEARCH = f"{OFF_API}/cgi/search.pl"

async def fetch_korean_products(page=1, page_size=100):
    """Open Food Facts에서 한국 제품 검색"""
    params = {
        'action': 'process',
        'json': 1,
        'page': page,
        'page_size': page_size,
        'countries': 'South Korea',  # 한국 제품
        'fields': 'code,product_name,product_name_ko,brands,quantity,nutriments'
    }

    try:
        res = requests.get(OFF_SEARCH, params=params, timeout=30)
        data = res.json()
        return data.get('products', [])
    except Exception as e:
        print(f"API 오류: {e}")
        return []

def normalize_name(name):
    """제품명 정규화 (공백, 특수문자 제거)"""
    if not name:
        return ""
    # 공백, 괄호, 특수문자 제거
    normalized = name.lower().strip()
    normalized = normalized.replace(' ', '').replace('(', '').replace(')', '')
    normalized = normalized.replace('[', '').replace(']', '')
    return normalized

def similarity(a, b):
    """문자열 유사도 (0~1)"""
    return SequenceMatcher(None, a, b).ratio()

async def match_products(conn, off_products):
    """Open Food Facts 제품과 STOPPER DB 매칭"""
    matches = []

    # STOPPER DB에서 모든 제품 가져오기
    stopper_foods = await conn.fetch("SELECT id, name, manufacturer FROM foods")

    print(f"\n🔍 매칭 시작: OFF {len(off_products)}개 vs STOPPER {len(stopper_foods)}개")

    for off_prod in off_products:
        barcode = off_prod.get('code')
        off_name = off_prod.get('product_name_ko') or off_prod.get('product_name', '')
        off_brand = off_prod.get('brands', '')

        if not barcode or not off_name:
            continue

        off_name_norm = normalize_name(off_name)

        # STOPPER DB에서 가장 유사한 제품 찾기
        best_match = None
        best_score = 0.0

        for food in stopper_foods:
            food_name_norm = normalize_name(food['name'])

            # 제품명 유사도 계산
            score = similarity(off_name_norm, food_name_norm)

            # 제조사 일치시 보너스
            if off_brand and food['manufacturer']:
                brand_norm = normalize_name(off_brand)
                mfg_norm = normalize_name(food['manufacturer'])
                if brand_norm in mfg_norm or mfg_norm in brand_norm:
                    score += 0.2

            if score > best_score:
                best_score = score
                best_match = food

        # 유사도 80% 이상만 매칭
        if best_score >= 0.8:
            matches.append({
                'food_id': best_match['id'],
                'barcode': barcode,
                'food_name': best_match['name'],
                'off_name': off_name,
                'score': best_score
            })
            print(f"✅ [{best_score:.2f}] {barcode} → {best_match['name'][:30]}")

    return matches

async def main():
    # PostgreSQL 연결
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🌏 Open Food Facts 한국 제품 다운로드 중...")

    all_products = []

    # 최대 5페이지 (500개 제품)
    for page in range(1, 6):
        print(f"  페이지 {page}/5 다운로드 중...")
        products = await fetch_korean_products(page=page, page_size=100)

        if not products:
            break

        all_products.extend(products)
        await asyncio.sleep(1)  # API 부하 방지

    print(f"\n📦 총 {len(all_products)}개 제품 다운로드 완료")

    # 매칭 실행
    matches = await match_products(conn, all_products)

    print(f"\n🎯 매칭 결과: {len(matches)}개")

    # 매칭 결과 저장
    if matches:
        with open('/Users/js/Documents/stopper/data/barcode_matches.json', 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)

        print(f"💾 매칭 결과 저장: /Users/js/Documents/stopper/data/barcode_matches.json")

        # 상위 10개 출력
        print("\n📊 매칭 샘플 (상위 10개):")
        for m in matches[:10]:
            print(f"  {m['barcode']:13s} | {m['score']:.2f} | {m['food_name'][:40]}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
