"""
식품의약품안전처 유통바코드 API (I2570) 데이터 수집 및 STOPPER DB 매칭

API 문서: https://www.data.go.kr/data/15064775/openapi.do
"""

import asyncio
import asyncpg
import requests
import json
import time
from difflib import SequenceMatcher

API_KEY = "14588a0a32f2476a8797"
API_BASE = "http://openapi.foodsafetykorea.go.kr/api"
SERVICE_NAME = "I2570"

def normalize_name(name):
    """제품명 정규화"""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = normalized.replace(' ', '').replace('(', '').replace(')', '')
    normalized = normalized.replace('[', '').replace(']', '').replace('-', '')
    return normalized

def similarity(a, b):
    """문자열 유사도"""
    return SequenceMatcher(None, a, b).ratio()

def fetch_mfds_page(start_idx=1, end_idx=1000):
    """식약처 유통바코드 API 페이지 가져오기"""
    url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/{start_idx}/{end_idx}"

    try:
        print(f"  📥 요청: {start_idx}-{end_idx}...", end=' ', flush=True)
        res = requests.get(url, timeout=30)
        data = res.json()

        # API 응답 확인
        if SERVICE_NAME not in data:
            print("❌ API 응답 구조 오류")
            return [], 0

        service_data = data[SERVICE_NAME]

        # 결과 확인
        if 'RESULT' in service_data:
            result = service_data['RESULT']
            if result.get('CODE') != 'INFO-000':
                print(f"❌ API 오류: {result.get('MSG')}")
                return [], 0

        # 총 개수
        total_count = int(service_data.get('total_count', 0))

        # 데이터 추출
        items = service_data.get('row', [])
        if not items:
            print("❌ 데이터 없음")
            return [], total_count

        print(f"✅ {len(items)}개")
        return items, total_count

    except Exception as e:
        print(f"❌ 오류: {e}")
        return [], 0

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🏛️  식품의약품안전처 유통바코드 수집 시작\n")

    # STOPPER DB 제품 목록 로드
    print("📦 STOPPER DB 제품 로드 중...")
    stopper_foods = await conn.fetch("SELECT id, name, manufacturer FROM foods")
    print(f"✅ {len(stopper_foods):,}개 제품 로드 완료\n")

    all_items = []
    page_size = 1000
    total_count = 0

    # 첫 페이지로 총 개수 확인
    print("📥 식약처 데이터 다운로드 중...\n")
    first_items, total_count = fetch_mfds_page(1, page_size)

    if total_count == 0:
        print("❌ 다운로드할 데이터가 없습니다.")
        await conn.close()
        return

    print(f"\n📊 전체 데이터: {total_count:,}개\n")
    all_items.extend(first_items)

    # 나머지 페이지 다운로드
    max_items = min(total_count, 50000)  # 최대 50,000개로 제한
    num_pages = (max_items + page_size - 1) // page_size

    for page in range(2, num_pages + 1):
        start_idx = (page - 1) * page_size + 1
        end_idx = min(page * page_size, max_items)

        items, _ = fetch_mfds_page(start_idx, end_idx)

        if not items:
            break

        all_items.extend(items)

        # API 부하 방지
        time.sleep(0.3)

    print(f"\n✅ 총 {len(all_items):,}개 다운로드 완료\n")

    # 바코드가 있는 항목만 필터링
    barcode_items = [
        item for item in all_items
        if item.get('BRCD_NO') and item.get('PRDT_NM')
    ]
    print(f"📊 바코드 보유 제품: {len(barcode_items):,}개\n")

    # STOPPER DB와 매칭
    print("🔍 STOPPER DB와 매칭 중...\n")
    matches = []

    for i, mfds_item in enumerate(barcode_items, 1):
        if i % 100 == 0:
            print(f"  진행: {i}/{len(barcode_items)} ({len(matches)}개 매칭)", flush=True)

        barcode = mfds_item.get('BRCD_NO', '').strip()
        mfds_name = mfds_item.get('PRDT_NM', '').strip()
        mfds_company = mfds_item.get('CMPNY_NM', '').strip()

        if not barcode or not mfds_name:
            continue

        # 이미 바코드가 있는지 확인
        existing = await conn.fetchval(
            "SELECT id FROM foods WHERE barcode = $1",
            barcode
        )
        if existing:
            continue  # 이미 있으면 스킵

        mfds_name_norm = normalize_name(mfds_name)
        mfds_len = len(mfds_name_norm)

        # STOPPER DB에서 가장 유사한 제품 찾기
        best_match = None
        best_score = 0.0

        for food in stopper_foods:
            food_name_norm = normalize_name(food['name'])
            food_len = len(food_name_norm)

            # 길이 차이가 너무 크면 스킵 (속도 최적화)
            if abs(mfds_len - food_len) > max(mfds_len, food_len) * 0.6:
                continue

            score = similarity(mfds_name_norm, food_name_norm)

            # 제조사 일치시 보너스
            if mfds_company and food['manufacturer']:
                company_norm = normalize_name(mfds_company)
                mfg_norm = normalize_name(food['manufacturer'])
                if company_norm in mfg_norm or mfg_norm in company_norm:
                    score += 0.15

            if score > best_score:
                best_score = score
                best_match = food

        # 유사도 80% 이상만 매칭 (식약처는 정부 데이터라 신뢰도 높음)
        if best_score >= 0.80:
            matches.append({
                'food_id': best_match['id'],
                'barcode': barcode,
                'food_name': best_match['name'],
                'mfds_name': mfds_name,
                'mfds_company': mfds_company,
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
        output_file = '/Users/js/Documents/stopper/data/mfds_barcode_matches.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)

        print(f"💾 매칭 결과 저장: {output_file}")

    # 최종 통계
    total_barcodes = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE barcode IS NOT NULL")
    print(f"\n📊 최종 바코드 보유 제품: {total_barcodes:,}개")

    # 상위 20개 출력
    samples = await conn.fetch('''
        SELECT name, barcode, manufacturer
        FROM foods
        WHERE barcode IS NOT NULL
        ORDER BY id DESC
        LIMIT 20
    ''')

    print("\n📊 최근 추가된 바코드 샘플:")
    for s in samples:
        print(f"  {s['barcode']:13s} | {s['name'][:45]:45s} | {s['manufacturer'] or 'N/A'}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
