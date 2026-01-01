"""
소분류별 1인분 기준 정의
- LLM 분석 + 식품 상식 기반
"""

CATEGORY_SERVING_RULES = {
    # 메인 식사류 (300-600g)
    "즉석조리식품": {"min_cal": 100, "max_cal": 900, "typical_serving": "300-500g"},
    "도시락": {"min_cal": 250, "max_cal": 800, "typical_serving": "350-450g"},
    "덮밥": {"min_cal": 250, "max_cal": 800, "typical_serving": "300-500g"},
    "볶음밥": {"min_cal": 250, "max_cal": 800, "typical_serving": "300-450g"},
    "즉석섭취식품": {"min_cal": 100, "max_cal": 700, "typical_serving": "100-400g"},

    # 김밥/샌드위치류 (150-300g)
    "김밥": {"min_cal": 150, "max_cal": 600, "typical_serving": "180-280g"},
    "샌드위치": {"min_cal": 150, "max_cal": 500, "typical_serving": "150-250g"},

    # 햄버거류 (150-300g)
    "햄버거": {"min_cal": 200, "max_cal": 800, "typical_serving": "150-280g"},

    # 면류 (200-400g)
    "국수": {"min_cal": 150, "max_cal": 700, "typical_serving": "200-400g"},
    "라면": {"min_cal": 200, "max_cal": 700, "typical_serving": "200-350g"},
    "파스타": {"min_cal": 200, "max_cal": 800, "typical_serving": "250-400g"},

    # 간식/사이드류 (30-150g)
    "빵류": {"min_cal": 50, "max_cal": 500, "typical_serving": "40-120g", "max_protein": 25},  # 단백질바 40g/10g 기준
    "과자": {"min_cal": 80, "max_cal": 600, "typical_serving": "50-150g", "max_protein": 30},
    "스낵": {"min_cal": 100, "max_cal": 600, "typical_serving": "60-150g", "max_protein": 30},

    # 단백질 간편식 (50-150g)
    "닭가슴살": {"min_cal": 80, "max_cal": 250, "typical_serving": "80-150g"},
    "계란": {"min_cal": 50, "max_cal": 200, "typical_serving": "50-100g"},
    "두부": {"min_cal": 40, "max_cal": 200, "typical_serving": "100-200g"},

    # 국/탕류 (200-400ml)
    "국": {"min_cal": 30, "max_cal": 300, "typical_serving": "200-350ml"},
    "탕": {"min_cal": 50, "max_cal": 400, "typical_serving": "250-400ml"},

    # 샐러드/볼류 (150-400g)
    "샐러드": {"min_cal": 50, "max_cal": 400, "typical_serving": "150-350g"},
    "볼": {"min_cal": 150, "max_cal": 700, "typical_serving": "200-400g"},

    # 기본값 (분류 불명시)
    "기본": {"min_cal": 50, "max_cal": 1000, "typical_serving": "100-400g"}
}


def get_serving_rule(category_small: str) -> dict:
    """소분류에 맞는 1인분 기준 반환"""
    # 키워드 매칭
    cat_lower = category_small.lower() if category_small else ""

    for key, rule in CATEGORY_SERVING_RULES.items():
        if key in cat_lower or cat_lower in key:
            return rule

    # 기본값
    return CATEGORY_SERVING_RULES["기본"]


def is_single_serving(category_small: str, name: str, calories: float, protein: float) -> bool:
    """1인분 제품인지 판단 (묶음 데이터 제외)"""
    rule = get_serving_rule(category_small)

    # 칼로리 범위 체크
    if not (rule["min_cal"] <= calories <= rule["max_cal"]):
        return False

    # 카테고리별 단백질 상한 체크 (빵류, 과자 등)
    if "max_protein" in rule and protein > rule["max_protein"]:
        return False  # 단백질바는 보통 40g에 10g 전후 -> 25g 이상이면 묶음

    # 단백질 이상치 제외 (100g당 기준으로 입력된 오류 데이터)
    if protein > 60:  # 비현실적
        return False

    # 단백질 비율 체크 (묶음/100g당 데이터 제외)
    if calories > 0:
        protein_pct = (protein * 4 / calories) * 100

        # 제품명에 "프로틴", "단백질" 없는데 단백질 비율 > 35%면 의심 (묶음 데이터)
        is_protein_product = any(keyword in name for keyword in ["프로틴", "단백질", "protein", "PROTEIN"])

        if not is_protein_product and protein_pct > 35:
            return False  # 일반 빵/과자가 단백질 35% 이상? 묶음 데이터

        # 프로틴 제품도 55% 넘으면 비현실적 (100g당 입력 오류)
        if protein_pct > 55:
            return False

    return True
