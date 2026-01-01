"""
기존 STOPPER DB 데이터 정규화
"""
import asyncio
import asyncpg
import re

def normalize_text(text):
    """텍스트 정규화"""
    if not text:
        return ""

    # 소문자 변환
    normalized = text.lower().strip()

    # 괄호 내용 제거 (용량, 설명 등)
    normalized = re.sub(r'\([^)]*\)', '', normalized)
    normalized = re.sub(r'\[[^\]]*\]', '', normalized)

    # 용량 표기 제거 (숫자+단위)
    normalized = re.sub(r'\d+\.?\d*(g|ml|kg|l|mg|개|입|ea|EA)', '', normalized)

    # 특수문자 제거 (공백, 하이픈, 언더스코어 등)
    normalized = re.sub(r'[^\w가-힣]', '', normalized)

    return normalized

def extract_tokens(text):
    """의미 있는 토큰 추출"""
    if not text:
        return []

    normalized = normalize_text(text)

    # 2글자 이상 토큰만
    tokens = []

    # 한글 2글자 이상
    korean_tokens = re.findall(r'[가-힣]{2,}', normalized)
    tokens.extend(korean_tokens)

    # 영어 3글자 이상
    english_tokens = re.findall(r'[a-z]{3,}', normalized)
    tokens.extend(english_tokens)

    # 숫자 제거
    tokens = [t for t in tokens if not t.isdigit()]

    return list(set(tokens))  # 중복 제거

async def main():
    conn = await asyncpg.connect('postgresql://stopper:stopper2026@localhost:5433/stopper')

    print("🔧 STOPPER DB 데이터 정규화 시작\n")

    # 전체 제품 수
    total = await conn.fetchval("SELECT COUNT(*) FROM foods")
    print(f"📊 전체 제품: {total:,}개\n")

    # 배치 단위로 처리
    batch_size = 1000
    updated = 0

    print("🔄 정규화 중...\n")

    for offset in range(0, total, batch_size):
        foods = await conn.fetch(
            "SELECT id, name, manufacturer FROM foods LIMIT $1 OFFSET $2",
            batch_size, offset
        )

        for food in foods:
            name_norm = normalize_text(food['name'])
            manufacturer_norm = normalize_text(food['manufacturer'])
            tokens = extract_tokens(food['name'])

            await conn.execute("""
                UPDATE foods
                SET name_norm = $1,
                    manufacturer_norm = $2,
                    tokens = $3
                WHERE id = $4
            """, name_norm, manufacturer_norm, tokens, food['id'])

            updated += 1

        if updated % 10000 == 0:
            print(f"  진행: {updated:,}/{total:,} ({updated*100//total}%)")

    print(f"\n✅ 총 {updated:,}개 제품 정규화 완료\n")

    # 통계
    with_tokens = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE tokens IS NOT NULL AND array_length(tokens, 1) > 0")
    print(f"📊 토큰 보유 제품: {with_tokens:,}개")

    with_mfg = await conn.fetchval("SELECT COUNT(*) FROM foods WHERE manufacturer_norm IS NOT NULL AND manufacturer_norm != ''")
    print(f"📊 제조사 정규화 완료: {with_mfg:,}개")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
