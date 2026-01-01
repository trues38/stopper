"""
식약처 바코드 최적화 매칭
- 전수 비교 금지
- 제조사 + 토큰 인덱스 활용
- 후보 축소 후 fuzzy matching
"""

import asyncio
import asyncpg
import requests
import json
import time
import re
from typing import List, Dict, Optional

API_KEY = "14588a0a32f2476a8797"
API_BASE = "http://openapi.foodsafetykorea.go.kr/api"
SERVICE_NAME = "I2570"

def normalize_text(text):
    """텍스트 정규화"""
    if not text:
        return ""
    normalized = text.lower().strip()
    normalized = re.sub(r'\([^)]*\)', '', normalized)
    normalized = re.sub(r'\[[^\]]*\]', '', normalized)
    normalized = re.sub(r'\d+\.?\d*(g|ml|kg|l|mg|개|입|ea|EA)', '', normalized)
    normalized = re.sub(r'[^\w가-힣]', '', normalized)
    return normalized

def extract_tokens(text):
    """의미 있는 토큰 추출"""
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

def token_overlap_score(tokens1: List[str], tokens2: List[str]) -> float:
    """토큰 겹침 비율"""
    if not tokens1 or not tokens2:
        return 0.0
    set1 = set(tokens1)
    set2 = set(tokens2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0

def string_similarity(a: str, b: str) -> float:
    """간단한 문자열 유사도 (trigram 방식)"""
    if not a or not b:
        return 0.0

    # 3-gram 생성
    def trigrams(s):
        s = f"  {s} "  # 패딩
        return [s[i:i+3] for i in range(len(s)-2)]

    tri_a = set(trigrams(a))
    tri_b = set(trigrams(b))

    if not tri_a or not tri_b:
        return 0.0

    intersection = len(tri_a & tri_b)
    union = len(tri_a | tri_b)

    return intersection / union if union > 0 else 0.0

async def find_candidates(
    conn,
    mfds_name_norm: str,
    mfds_company_norm: str,
    mfds_tokens: List[str]
) -> List[Dict]:
    """후보 제품 찾기 (인덱스 활용)"""

    candidates = []

    # 1차 후보: 제조사 일치
    if mfds_company_norm:
        mfg_matches = await conn.fetch("""
            SELECT id, name, name_norm, manufacturer, manufacturer_norm, tokens
            FROM foods
            WHERE manufacturer_norm = $1
            LIMIT 50
        """, mfds_company_norm)
        candidates.extend([dict(r) for r in mfg_matches])

    # 2차 후보: 토큰 겹침 (제조사 일치 없을 때)
    if len(candidates) < 5 and mfds_tokens:
        token_matches = await conn.fetch("""
            SELECT id, name, name_norm, manufacturer, manufacturer_norm, tokens
            FROM foods
            WHERE tokens && $1
            ORDER BY array_length(tokens, 1) DESC
            LIMIT 50
        """, mfds_tokens)

        # 중복 제거
        existing_ids = {c['id'] for c in candidates}
        for row in token_matches:
            if row['id'] not in existing_ids:
                candidates.append(dict(row))
                existing_ids.add(row['id'])

    # 3차 후보: pg_trgm 유사도 (위 방법으로 찾지 못했을 때)
    if len(candidates) < 5 and mfds_name_norm:
        # pg_trgm similarity threshold
        similarity_matches = await conn.fetch("""
            SELECT id, name, name_norm, manufacturer, manufacturer_norm, tokens,
                   similarity(name_norm, $1) as sim
            FROM foods
            WHERE similarity(name_norm, $1) > 0.3
            ORDER BY sim DESC
            LIMIT 50
        """, mfds_name_norm)

        existing_ids = {c['id'] for c in candidates}
        for row in similarity_matches:
            if row['id'] not in existing_ids:
                candidates.append(dict(row))
                existing_ids.add(row['id'])

    return candidates[:50]  # 최대 50개로 제한

async def match_product(
    conn,
    barcode: str,
    mfds_name: str,
    mfds_company: str
) -> Optional[Dict]:
    """제품 매칭 (최적화)"""

    # 이미 바코드가 있으면 스킵
    existing = await conn.fetchval(
        "SELECT id FROM foods WHERE barcode = $1",
        barcode
    )
    if existing:
        return None

    # 정규화
    mfds_name_norm = normalize_text(mfds_name)
    mfds_company_norm = normalize_text(mfds_company)
    mfds_tokens = extract_tokens(mfds_name)

    if not mfds_name_norm:
        return None

    # 후보 찾기 (인덱스 활용)
    candidates = await find_candidates(conn, mfds_name_norm, mfds_company_norm, mfds_tokens)

    if not candidates:
        return {
            'barcode': barcode,
            'food_id': None,
            'mfds_name': mfds_name,
            'mfds_company': mfds_company,
            'confidence': 0.0,
            'status': 'FAIL'
        }

    # 최고 점수 찾기
    best_match = None
    best_score = 0.0

    for candidate in candidates:
        # 이름 유사도
        name_sim = string_similarity(mfds_name_norm, candidate['name_norm'])

        # 토큰 겹침
        token_overlap = token_overlap_score(mfds_tokens, candidate['tokens'] or [])

        # 제조사 보너스
        mfg_bonus = 0.0
        if mfds_company_norm and candidate['manufacturer_norm']:
            if mfds_company_norm == candidate['manufacturer_norm']:
                mfg_bonus = 0.2
            elif mfds_company_norm in candidate['manufacturer_norm'] or \
                 candidate['manufacturer_norm'] in mfds_company_norm:
                mfg_bonus = 0.1

        # 최종 점수
        final_score = 0.5 * name_sim + 0.3 * token_overlap + 0.2 * mfg_bonus

        if final_score > best_score:
            best_score = final_score
            best_match = candidate

    # 상태 결정
    if best_score >= 0.85:
        status = 'AUTO'
    elif best_score >= 0.65:
        status = 'REVIEW'
    else:
        status = 'FAIL'

    return {
        'barcode': barcode,
        'food_id': best_match['id'] if best_match else None,
        'food_name': best_match['name'] if best_match else None,
        'mfds_name': mfds_name,
        'mfds_company': mfds_company,
        'confidence': best_score,
        'status': status
    }

def fetch_mfds_page(start_idx=1, end_idx=1000):
    """식약처 유통바코드 API 페이지 가져오기"""
    url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/{start_idx}/{end_idx}"

    try:
        res = requests.get(url, timeout=30)
        data = res.json()

        if SERVICE_NAME not in data:
            return [], 0

        service_data = data[SERVICE_NAME]

        if 'RESULT' in service_data:
            result = service_data['RESULT']
            if result.get('CODE') != 'INFO-000':
                return [], 0

        total_count = int(service_data.get('total_count', 0))
        items = service_data.get('row', [])

        return items, total_count

    except Exception as e:
        print(f"❌ API 오류: {e}")
        return [], 0

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🚀 최적화된 식약처 바코드 매칭 시작\n")

    # 정규화 확인
    normalized_count = await conn.fetchval(
        "SELECT COUNT(*) FROM foods WHERE name_norm IS NOT NULL"
    )
    total_count = await conn.fetchval("SELECT COUNT(*) FROM foods")

    print(f"📊 STOPPER DB 정규화 상태: {normalized_count:,}/{total_count:,}")

    if normalized_count < total_count * 0.5:
        print("⚠️  데이터 정규화가 50% 미만입니다. normalize_existing_data.py를 먼저 실행하세요.\n")
        await conn.close()
        return
    elif normalized_count < total_count * 0.9:
        print(f"⚠️  일부 제품만 정규화됨 ({normalized_count*100//total_count}%). 매칭 정확도가 낮을 수 있습니다.\n")

    # 식약처 데이터 다운로드
    print("\n📥 식약처 데이터 다운로드 중...\n")

    all_items = []
    page_size = 1000

    first_items, total_mfds = fetch_mfds_page(1, page_size)

    if total_mfds == 0:
        print("❌ 식약처 데이터 없음")
        await conn.close()
        return

    print(f"📊 전체 식약처 데이터: {total_mfds:,}개\n")
    all_items.extend(first_items)

    # 최대 50,000개
    max_items = min(total_mfds, 50000)
    num_pages = (max_items + page_size - 1) // page_size

    for page in range(2, num_pages + 1):
        start_idx = (page - 1) * page_size + 1
        end_idx = min(page * page_size, max_items)

        items, _ = fetch_mfds_page(start_idx, end_idx)
        if not items:
            break

        all_items.extend(items)

        if page % 10 == 0:
            print(f"  다운로드: {len(all_items):,}/{max_items:,}")

        time.sleep(0.2)

    print(f"\n✅ 다운로드 완료: {len(all_items):,}개\n")

    # 바코드 매칭
    print("🔍 최적화된 매칭 시작...\n")

    matches = []
    auto_count = 0
    review_count = 0
    fail_count = 0

    for i, item in enumerate(all_items, 1):
        barcode = item.get('BRCD_NO', '').strip()
        name = item.get('PRDT_NM', '').strip()
        company = item.get('CMPNY_NM', '').strip()

        if not barcode or not name:
            continue

        match = await match_product(conn, barcode, name, company)

        if match:
            matches.append(match)

            if match['status'] == 'AUTO':
                auto_count += 1
            elif match['status'] == 'REVIEW':
                review_count += 1
            else:
                fail_count += 1

        if i % 500 == 0:
            print(f"  진행: {i:,}/{len(all_items):,} | AUTO: {auto_count} | REVIEW: {review_count} | FAIL: {fail_count}")

    print(f"\n✅ 매칭 완료\n")
    print(f"📊 결과:")
    print(f"  - AUTO (≥85%): {auto_count:,}개")
    print(f"  - REVIEW (65-85%): {review_count:,}개")
    print(f"  - FAIL (<65%): {fail_count:,}개\n")

    # barcode_matches 테이블에 저장
    print("💾 결과 저장 중...")

    for match in matches:
        await conn.execute("""
            INSERT INTO barcode_matches (barcode, food_id, mfds_name, mfds_company, confidence, status)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, match['barcode'], match['food_id'], match['mfds_name'],
             match['mfds_company'], match['confidence'], match['status'])

    print(f"✅ {len(matches):,}개 저장 완료\n")

    # AUTO 매칭만 실제 바코드 업데이트
    print("💾 AUTO 매칭 바코드 업데이트 중...")

    auto_matches = [m for m in matches if m['status'] == 'AUTO']
    updated = 0

    for match in auto_matches:
        if match['food_id']:
            await conn.execute(
                "UPDATE foods SET barcode = $1 WHERE id = $2",
                match['barcode'], match['food_id']
            )
            updated += 1

    print(f"✅ {updated:,}개 바코드 업데이트 완료\n")

    # 최종 통계
    total_barcodes = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE barcode IS NOT NULL")
    print(f"📊 최종 바코드 보유 제품: {total_barcodes:,}개")

    # JSON 저장
    output_file = '/Users/js/Documents/stopper/data/mfds_barcode_matches_optimized.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    print(f"💾 매칭 결과 저장: {output_file}\n")

    # AUTO 매칭 샘플
    auto_samples = await conn.fetch("""
        SELECT f.name, f.barcode, bm.mfds_name, bm.confidence
        FROM barcode_matches bm
        JOIN foods f ON f.id = bm.food_id
        WHERE bm.status = 'AUTO'
        ORDER BY bm.confidence DESC
        LIMIT 20
    """)

    print("📊 AUTO 매칭 샘플 (상위 20개):")
    for s in auto_samples:
        print(f"  [{s['confidence']:.2f}] {s['name'][:30]:30s} ↔ {s['mfds_name'][:30]:30s} | {s['barcode']}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
