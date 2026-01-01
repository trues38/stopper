"""
식약처 바코드 매칭 - 샘플 100개만
"""
import asyncio
import asyncpg
import requests
import re
from typing import List

API_KEY = "14588a0a32f2476a8797"
API_BASE = "http://openapi.foodsafetykorea.go.kr/api"
SERVICE_NAME = "I2570"

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

async def find_candidates(conn, mfds_name_norm, mfds_company_norm, mfds_tokens):
    candidates = []

    # 1차: 제조사
    if mfds_company_norm:
        try:
            mfg_matches = await conn.fetch("""
                SELECT id, name, name_norm, manufacturer, tokens
                FROM foods
                WHERE manufacturer_norm = $1
                LIMIT 10
            """, mfds_company_norm)
            candidates.extend([dict(r) for r in mfg_matches])
        except:
            pass

    # 2차: 토큰
    if len(candidates) < 3 and mfds_tokens:
        try:
            token_matches = await conn.fetch("""
                SELECT id, name, name_norm, manufacturer, tokens
                FROM foods
                WHERE tokens && $1
                LIMIT 10
            """, mfds_tokens)
            existing_ids = {c['id'] for c in candidates}
            for row in token_matches:
                if row['id'] not in existing_ids:
                    candidates.append(dict(row))
        except:
            pass

    # 3차: similarity
    if len(candidates) < 3 and mfds_name_norm:
        try:
            sim_matches = await conn.fetch("""
                SELECT id, name, name_norm, manufacturer, tokens,
                       similarity(name_norm, $1) as sim
                FROM foods
                WHERE similarity(name_norm, $1) > 0.3
                ORDER BY sim DESC
                LIMIT 10
            """, mfds_name_norm)
            existing_ids = {c['id'] for c in candidates}
            for row in sim_matches:
                if row['id'] not in existing_ids:
                    candidates.append(dict(row))
        except:
            pass

    return candidates

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🧪 식약처 바코드 매칭 테스트 (100개 샘플)\n")

    # 식약처 데이터 100개만 다운로드
    print("📥 식약처 데이터 100개 다운로드...")
    url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/1/100"
    res = requests.get(url, timeout=30)
    data = res.json()

    items = data[SERVICE_NAME]['row']
    print(f"✅ {len(items)}개 다운로드\n")

    # 매칭
    print("🔍 매칭 시작...\n")

    auto_count = 0
    review_count = 0
    fail_count = 0

    for i, item in enumerate(items, 1):
        barcode = item.get('BRCD_NO', '').strip()
        name = item.get('PRDT_NM', '').strip()
        company = item.get('CMPNY_NM', '').strip()

        if not barcode or not name:
            continue

        # 이미 바코드 있으면 스킵
        existing = await conn.fetchval("SELECT id FROM foods WHERE barcode = $1", barcode)
        if existing:
            continue

        name_norm = normalize_text(name)
        company_norm = normalize_text(company)
        tokens = extract_tokens(name)

        candidates = await find_candidates(conn, name_norm, company_norm, tokens)

        if candidates:
            print(f"[{i:3d}] {name[:40]:40s} → {len(candidates)}개 후보")
            print(f"      제조사: {company[:30]}")
            print(f"      후보: {candidates[0]['name'][:40]}")
            auto_count += 1
        else:
            fail_count += 1

    print(f"\n📊 결과:")
    print(f"   후보 발견: {auto_count}")
    print(f"   후보 없음: {fail_count}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
