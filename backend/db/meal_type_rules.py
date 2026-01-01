"""
STOPPER 핵심 철학: 현실 섭취 기준 meal_type 매핑

4가지 타입으로 200개 카테고리 자동 분류
- MEAL: 식사류 (도시락, 즉석식, 볶음밥, 만두, 죽/탕)
- SINGLE_PROTEIN: 단일 단백질 (닭가슴살, 햄, 소시지, 핫바, 계란)
- LIQUID: 음료/쉐이크/선식/RTD
- SNACK: 바/빵/과자/간식류
"""

# 현실 섭취 기준 단백질 상한 (g)
PROTEIN_CAP = {
    "MEAL": 35,              # 현실적 고단백 한 끼 상한
    "SINGLE_PROTEIN": 20,    # 단일 식품 현실 한계
    "LIQUID": 40,            # RTD 음료 최대 (닥터유 40g 기준)
    "SNACK": 15              # 바/빵/간식 상한
}

# 소분류 → meal_type 직접 매핑 (우선순위 최상)
CATEGORY_MEAL_TYPE = {
    # MEAL - 식사류
    "즉석조리식품": "MEAL",
    "즉석섭취식품": "MEAL",
    "도시락": "MEAL",
    "덮밥": "MEAL",
    "볶음밥": "MEAL",
    "컵밥": "MEAL",
    "만두": "MEAL",
    "숙면": "MEAL",
    "죽": "MEAL",
    "탕": "MEAL",
    "국": "MEAL",
    "간편조리세트": "MEAL",
    "신선편의식품": "MEAL",

    # MEAL - 면류
    "건면": "MEAL",
    "생면": "MEAL",
    "유탕면": "MEAL",
    "라면": "MEAL",
    "파스타": "MEAL",
    "국수": "MEAL",

    # SINGLE_PROTEIN - 단백질 식품
    "닭가슴살": "SINGLE_PROTEIN",
    "핫바": "SINGLE_PROTEIN",
    "햄": "SINGLE_PROTEIN",
    "생햄": "SINGLE_PROTEIN",
    "프레스햄": "SINGLE_PROTEIN",
    "소시지": "SINGLE_PROTEIN",
    "어육소시지": "SINGLE_PROTEIN",
    "양념육": "SINGLE_PROTEIN",
    "분쇄가공육제품": "SINGLE_PROTEIN",
    "계란": "SINGLE_PROTEIN",
    "알가열제품": "SINGLE_PROTEIN",
    "치즈": "SINGLE_PROTEIN",
    "가공치즈": "SINGLE_PROTEIN",
    "두부": "SINGLE_PROTEIN",
    "가공두부": "SINGLE_PROTEIN",
    "어묵": "SINGLE_PROTEIN",

    # LIQUID - 음료/쉐이크/선식
    "음료베이스": "LIQUID",
    "혼합음료": "LIQUID",
    "과·채주스": "LIQUID",
    "과·채음료": "LIQUID",
    "탄산음료": "LIQUID",
    "액상차": "LIQUID",
    "고형차": "LIQUID",
    "발효유": "LIQUID",
    "농후발효유": "LIQUID",
    "유산균음료": "LIQUID",
    "가공두유": "LIQUID",
    "우유": "LIQUID",
    "가공유": "LIQUID",
    "프로틴쉐이크": "LIQUID",
    "선식": "LIQUID",
    "미숫가루": "LIQUID",

    # SNACK - 바/빵/과자
    "빵류": "SNACK",
    "과자": "SNACK",
    "스낵": "SNACK",
    "캔디류": "SNACK",
    "초콜릿": "SNACK",
    "초콜릿가공품": "SNACK",
    "밀크초콜릿": "SNACK",
    "화이트초콜릿": "SNACK",
    "준초콜릿": "SNACK",
    "기타 코코아가공품": "SNACK",
    "떡류": "SNACK",
    "아이스크림": "SNACK",
    "아이스밀크": "SNACK",
    "샤베트": "SNACK",
    "비유지방아이스크림": "SNACK",
    "땅콩 또는 견과류가공품": "SNACK",
    "땅콩버터": "SNACK",
}

# 키워드 기반 자동 분류 (fallback)
KEYWORD_RULES = {
    "MEAL": [
        "도시락", "덮밥", "볶음밥", "김밥", "샌드위치", "햄버거", "버거",
        "만두", "죽", "탕", "국", "면", "파스타", "라면", "국수",
        "즉석", "간편", "편의", "세트", "meal", "bowl", "컵밥"
    ],
    "SINGLE_PROTEIN": [
        "닭가슴살", "핫바", "햄", "소시지", "계란", "치즈", "두부",
        "양념육", "육", "고기", "생선", "어묵", "protein", "단백"
    ],
    "LIQUID": [
        "음료", "주스", "쉐이크", "shake", "드링크", "drink", "차", "tea",
        "우유", "milk", "두유", "발효유", "요거트", "선식", "미숫가루",
        "탄산", "콜라", "사이다", "커피", "coffee", "라떼"
    ],
    "SNACK": [
        "빵", "과자", "스낵", "캔디", "초콜릿", "쿠키", "cookie", "바",
        "bar", "떡", "아이스크림", "ice", "견과", "칩", "크래커"
    ]
}


def get_meal_type(category_small: str, product_name: str = "") -> str:
    """
    소분류와 제품명 기반으로 meal_type 자동 분류

    Args:
        category_small: 소분류 카테고리명
        product_name: 제품명 (옵션)

    Returns:
        meal_type: MEAL, SINGLE_PROTEIN, LIQUID, SNACK 중 하나
    """
    if not category_small:
        return "SNACK"  # 기본값

    # 1. 직접 매핑 (최우선)
    if category_small in CATEGORY_MEAL_TYPE:
        return CATEGORY_MEAL_TYPE[category_small]

    # 2. 키워드 기반 분류
    cat_lower = category_small.lower()
    name_lower = product_name.lower() if product_name else ""
    combined = cat_lower + " " + name_lower

    # 각 타입별 키워드 매칭 점수 계산
    scores = {}
    for meal_type, keywords in KEYWORD_RULES.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[meal_type] = score

    # 최고 점수 타입 반환
    if scores:
        return max(scores, key=scores.get)

    # 3. 기본값 (분류 불가)
    return "SNACK"


def get_protein_cap(meal_type: str) -> int:
    """meal_type에 맞는 단백질 상한 반환 (g)"""
    return PROTEIN_CAP.get(meal_type, 15)


def effective_protein(protein_g: float, meal_type: str) -> float:
    """
    현실 섭취 기준 단백질 계산 (STOPPER 핵심 로직)

    표기값이 아니라 "실제로 먹을 수 있는 양" 기준

    Args:
        protein_g: 제품 표기 단백질 (g)
        meal_type: MEAL, SINGLE_PROTEIN, LIQUID, SNACK

    Returns:
        현실 기준 단백질 (g) - 상한 적용됨
    """
    cap = get_protein_cap(meal_type)
    return min(protein_g, cap)


def classify_all_categories(categories: list) -> dict:
    """
    전체 카테고리 리스트를 meal_type으로 분류

    Args:
        categories: [{"category_small": "빵류", ...}, ...]

    Returns:
        {
            "빵류": "SNACK",
            "즉석조리식품": "MEAL",
            ...
        }
    """
    result = {}
    for cat in categories:
        cat_name = cat.get("category_small") or cat.get("name")
        if cat_name:
            result[cat_name] = get_meal_type(cat_name)
    return result
