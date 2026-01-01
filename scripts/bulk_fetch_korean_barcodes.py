"""
Open Food Facts 한국 제품 바코드 대량 수집

한국 제품 바코드를 최대한 많이 수집하여 STOPPER DB에 추가
"""

import asyncio
import asyncpg
import requests
import json
from difflib import SequenceMatcher
import time

OFF_API = "https://kr.openfoodfacts.org"
OFF_SEARCH = f"{OFF_API}/cgi/search.pl"

def normalize_name(name):
    """제품명 정규화"""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = normalized.replace(' ', '').replace('(', '').replace(')', '')
    normalized = normalized.replace('[', '').replace(']', '')
    return normalized

def similarity(a, b):
    """문자열 유사도"""
    return SequenceMatcher(None, a, b).ratio()

async def fetch_korean_products_page(page=1, page_size=100):
    """Open Food Facts에서 한국 제품 1페이지 가져오기"""
    params = {
        'action': 'process',
        'json': 1,
        'page': page,
        'page_size': page_size,
        'countries': 'South Korea',
        'fields': 'code,product_name,product_name_ko,brands,quantity,nutriments'
    }

    try:
        res = requests.get(OFF_SEARCH, params=params, timeout=30)
        data = res.json()
        return data.get('products', [])
    except Exception as e:
        print(f"  ❌ 페이지 {page} 오류: {e}")
        return []

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🌏 Open Food Facts 한국 제품 바코드 대량 수집 시작\n")

    # STOPPER DB 제품 목록 (한 번만 로드)
    print("📦 STOPPER DB 제품 로드 중...")
    stopper_foods = await conn.fetch("SELECT id, name, manufacturer FROM foods")
    print(f"✅ {len(stopper_foods):,}개 제품 로드 완료\n")

    all_products = []
    max_pages = 20  # 최대 20페이지 (2,000개) - 속도 개선

    # 페이지별 다운로드
    for page in range(1, max_pages + 1):
        print(f"📥 페이지 {page}/{max_pages} 다운로드 중...", end=' ', flush=True)
        products = await fetch_korean_products_page(page=page, page_size=100)

        if not products:
            print("❌ 더 이상 제품 없음")
            break

        all_products.extend(products)
        print(f"✅ {len(products)}개 (+{len(all_products)}개 누적)")

        # API 부하 방지
        if page < max_pages:
            await asyncio.sleep(0.5)  # 1초 → 0.5초

    print(f"\n📦 총 {len(all_products):,}개 한국 제품 다운로드 완료\n")

    # 바코드 매칭
    print("🔍 STOPPER DB와 매칭 중...")
    matches = []

    for i, off_prod in enumerate(all_products, 1):
        if i % 50 == 0:
            print(f"  진행: {i}/{len(all_products)} ({len(matches)}개 매칭)", flush=True)

        barcode = off_prod.get('code')
        off_name = off_prod.get('product_name_ko') or off_prod.get('product_name', '')
        off_brand = off_prod.get('brands', '')

        if not barcode or not off_name:
            continue

        # 이미 바코드가 있는지 확인
        existing = await conn.fetchval(
            "SELECT id FROM foods WHERE barcode = $1",
            barcode
        )
        if existing:
            continue  # 이미 있으면 스킵

        off_name_norm = normalize_name(off_name)
        off_len = len(off_name_norm)

        # STOPPER DB에서 가장 유사한 제품 찾기 (최적화)
        best_match = None
        best_score = 0.0

        for food in stopper_foods:
            food_name_norm = normalize_name(food['name'])
            food_len = len(food_name_norm)

            # 길이 차이가 너무 크면 스킵 (속도 최적화)
            if abs(off_len - food_len) > max(off_len, food_len) * 0.5:
                continue

            score = similarity(off_name_norm, food_name_norm)

            # 제조사 일치시 보너스
            if off_brand and food['manufacturer']:
                brand_norm = normalize_name(off_brand)
                mfg_norm = normalize_name(food['manufacturer'])
                if brand_norm in mfg_norm or mfg_norm in brand_norm:
                    score += 0.15

            if score > best_score:
                best_score = score
                best_match = food

        # 유사도 75% 이상만 매칭
        if best_score >= 0.75:
            matches.append({
                'food_id': best_match['id'],
                'barcode': barcode,
                'food_name': best_match['name'],
                'off_name': off_name,
                'score': best_score
            })

    print(f"\n✅ 매칭 완료: {len(matches):,}개\n")

    # DB 업데이트
    if matches:
        print("💾 바코드 업데이트 중...")
        updated = 0

        for match in matches:
            try:
                await conn.execute(
                    "UPDATE foods SET barcode = $1 WHERE id = $2",
                    match['barcode'], match['food_id']
                )
                updated += 1
                if updated % 100 == 0:
                    print(f"  업데이트: {updated}/{len(matches)}")
            except Exception as e:
                print(f"  ❌ 업데이트 실패 [{match['food_id']}]: {e}")

        print(f"\n✅ 총 {updated:,}개 바코드 업데이트 완료")

        # 결과 저장
        with open('/Users/js/Documents/stopper/data/barcode_bulk_matches.json', 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)

        print(f"💾 매칭 결과 저장: barcode_bulk_matches.json")

    # 최종 통계
    total_barcodes = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE barcode IS NOT NULL")
    print(f"\n📊 최종 바코드 보유 제품: {total_barcodes:,}개")

    # 상위 10개 출력
    samples = await conn.fetch('''
        SELECT name, barcode, manufacturer
        FROM foods
        WHERE barcode IS NOT NULL
        ORDER BY id DESC
        LIMIT 10
    ''')

    print("\n📊 최근 추가된 바코드 샘플:")
    for s in samples:
        print(f"  {s['barcode']:13s} | {s['name'][:45]:45s} | {s['manufacturer'] or 'N/A'}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
