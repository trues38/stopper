"""
LLM을 사용한 제품 데이터 검증
- OpenRouter API 사용
- 카테고리별 상위 제품의 1인분 타당성 검증
"""

import pandas as pd
import requests
import json
import os
from tqdm import tqdm

# OpenRouter API 설정
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 무료 모델 사용 (xiaomi/mimo-v2-flash:free)
MODEL = "xiaomi/mimo-v2-flash:free"


def validate_product_with_llm(category: str, products: list) -> dict:
    """LLM으로 제품들이 1인분인지 묶음인지 검증"""

    # 제품 정보를 간결하게 정리
    product_info = "\n".join([
        f"{i+1}. {p['name'][:50]}: {p['calories']}kcal, 단백질 {p['protein']}g, 탄수화물 {p['carbohydrate']}g, 지방 {p['fat']}g"
        for i, p in enumerate(products[:10])  # 상위 10개만
    ])

    prompt = f"""다음은 "{category}" 카테고리의 단백질 상위 제품들입니다.
각 제품이 **1인분(single serving)** 데이터인지, **묶음/다량 포장(multi-pack)** 데이터인지 판단해주세요.

{product_info}

판단 기준:
- 일반 빵/과자: 1개 기준 100-500kcal, 단백질 3-10g
- 단백질바: 1개 기준 150-250kcal, 단백질 10-20g
- 도시락: 1인분 기준 300-700kcal, 단백질 10-30g
- 비현실적으로 높은 칼로리/영양소 = 묶음 데이터

응답 형식 (JSON):
{{
  "category": "{category}",
  "products": [
    {{"rank": 1, "is_single_serving": true/false, "reason": "판단 이유"}},
    ...
  ]
}}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result['choices'][0]['message']['content']
        return json.loads(content)

    except Exception as e:
        print(f"  ❌ LLM 오류: {str(e)[:100]}")
        return None


def main():
    """메인 실행"""
    print("=" * 60)
    print("🤖 LLM 기반 제품 데이터 검증")
    print("=" * 60)

    # CSV 로드
    csv_path = "/Users/js/Documents/stopper/data/top_protein_by_category.csv"
    df = pd.read_csv(csv_path)

    print(f"\n총 {len(df)}개 제품, {df['category_small'].nunique()}개 카테고리")

    # API 키 확인
    if not OPENROUTER_API_KEY:
        print("\n⚠️  OPENROUTER_API_KEY 환경변수가 설정되지 않았습니다.")
        print("예시: export OPENROUTER_API_KEY='sk-or-...'")
        return

    # 카테고리별로 그룹화
    categories = df.groupby('category_small')

    # 검증 결과 저장
    validation_results = []

    # 주요 카테고리만 검증 (빵류, 즉석조리식품, 과자 등)
    priority_categories = ['빵류', '즉석조리식품', '과자', '캔디류', '음료', '면류']

    print(f"\n우선 검증할 카테고리: {', '.join(priority_categories)}\n")

    for category_name in priority_categories:
        if category_name not in categories.groups:
            continue

        group = categories.get_group(category_name)
        products = group.to_dict('records')

        print(f"\n📦 {category_name} ({len(products)}개)")
        print(f"  상위 3개: ", end="")
        for p in products[:3]:
            print(f"{p['name'][:20]}({p['protein']}g) ", end="")
        print()

        # LLM 검증
        result = validate_product_with_llm(category_name, products)

        if result:
            print(f"  ✓ LLM 분석 완료")

            # 묶음으로 판단된 제품 출력
            for item in result.get('products', []):
                if not item.get('is_single_serving', True):
                    product = products[item['rank'] - 1]
                    print(f"    ❌ {item['rank']}위: {product['name'][:40]}")
                    print(f"       이유: {item.get('reason', 'N/A')}")

            validation_results.append(result)

        # API Rate limit 방지
        import time
        time.sleep(2)

    # 결과 저장
    output_path = "/Users/js/Documents/stopper/data/llm_validation_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(validation_results, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 검증 결과 저장: {output_path}")

    # 요약
    total_checked = sum(len(r.get('products', [])) for r in validation_results)
    total_suspicious = sum(
        sum(1 for p in r.get('products', []) if not p.get('is_single_serving', True))
        for r in validation_results
    )

    print(f"\n{'='*60}")
    print(f"검증 완료: {total_checked}개 제품 중 {total_suspicious}개 의심 제품 발견")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
