"""
STOPPER UI 말투 시스템

핵심 철학: "숫자가 아니라 현실 기준으로 말한다"
- LLM처럼 불확실하게 말하지 않음
- 마케팅 숫자를 무력화
- 실제로 먹을 수 있는 양 기준
"""

from typing import Dict


def get_protein_verdict(
    effective_protein: float,
    goal_protein: float,
    meal_type: str
) -> Dict[str, str]:
    """
    단백질 판정 메시지 생성

    Args:
        effective_protein: 현실 기준 단백질 (상한 적용됨)
        goal_protein: 1일 목표 단백질
        meal_type: MEAL, SINGLE_PROTEIN, LIQUID, SNACK

    Returns:
        {
            "verdict": "👍 단백질 충분",
            "detail": "이 한 끼로 현실 기준 단백질 상위 90%입니다",
            "percentage": "목표의 68%를 안전하게 채웠어요"
        }
    """
    pct = (effective_protein / goal_protein) * 100

    # meal_type별 기준 다름
    if meal_type == "MEAL":
        # 식사는 목표의 30% 이상이면 우수
        if pct >= 50:
            verdict = "👍 단백질 충분"
            detail = f"이 한 끼로 **현실 기준 단백질 상위 90%**입니다"
        elif pct >= 30:
            verdict = "✅ 단백질 적정"
            detail = f"고단백 식사로 인정받는 수준입니다"
        elif pct >= 15:
            verdict = "⚠️ 단백질 보통"
            detail = f"한 끼 치고는 평범한 수준이에요"
        else:
            verdict = "❌ 단백질 부족"
            detail = f"단백질이 거의 없는 식사입니다"

    elif meal_type == "SINGLE_PROTEIN":
        # 단일 단백질은 목표의 20% 이상이면 우수
        if pct >= 30:
            verdict = "👍 단백질 충분"
            detail = f"**현실 기준 단백질 간식 최상위**입니다"
        elif pct >= 20:
            verdict = "✅ 단백질 적정"
            detail = f"단백질 보충용으로 좋아요"
        elif pct >= 10:
            verdict = "⚠️ 단백질 보통"
            detail = f"간식으로는 평범한 수준"
        else:
            verdict = "❌ 단백질 부족"
            detail = f"단백질 효과는 기대하기 어려워요"

    elif meal_type == "LIQUID":
        # 음료는 목표의 25% 이상이면 우수
        if pct >= 35:
            verdict = "👍 단백질 충분"
            detail = f"**현실 기준 단백질 음료 최상위**입니다"
        elif pct >= 25:
            verdict = "✅ 단백질 적정"
            detail = f"단백질 보충용으로 훌륭해요"
        elif pct >= 15:
            verdict = "⚠️ 단백질 보통"
            detail = f"음료치고는 괜찮은 편"
        else:
            verdict = "❌ 단백질 부족"
            detail = f"단백질 음료라고 보기 어려워요"

    else:  # SNACK
        # 간식은 목표의 15% 이상이면 우수
        if pct >= 20:
            verdict = "👍 단백질 충분"
            detail = f"**간식 중 단백질 최상위 등급**입니다"
        elif pct >= 15:
            verdict = "✅ 단백질 적정"
            detail = f"고단백 간식으로 인정받는 수준"
        elif pct >= 8:
            verdict = "⚠️ 단백질 보통"
            detail = f"간식으로는 평범한 수준"
        else:
            verdict = "❌ 단백질 부족"
            detail = f"단백질은 거의 없는 간식이에요"

    percentage = f"오늘 목표의 **{pct:.0f}%**를 안전하게 채웠어요"

    return {
        "verdict": verdict,
        "detail": detail,
        "percentage": percentage
    }


def get_calorie_verdict(
    calories: float,
    goal_calories: float,
    meal_type: str
) -> Dict[str, str]:
    """
    칼로리 판정 메시지 생성
    """
    pct = (calories / goal_calories) * 100

    if meal_type == "MEAL":
        # 식사는 20-40%가 이상적
        if pct > 45:
            verdict = "🛑 칼로리 초과"
            detail = "한 끼 치고는 과도한 칼로리입니다"
        elif pct > 35:
            verdict = "⚠️ 칼로리 높음"
            detail = "조금 많은 편이에요"
        elif pct >= 20:
            verdict = "✅ 칼로리 적정"
            detail = "한 끼로 딱 좋은 칼로리입니다"
        else:
            verdict = "👍 칼로리 낮음"
            detail = "저칼로리 식사예요"

    else:  # 간식/음료/단백질
        if pct > 25:
            verdict = "🛑 칼로리 초과"
            detail = f"{meal_type} 치고는 칼로리가 높아요"
        elif pct > 15:
            verdict = "⚠️ 칼로리 높음"
            detail = "간식으로는 부담될 수 있어요"
        elif pct >= 5:
            verdict = "✅ 칼로리 적정"
            detail = f"{meal_type}로 적당한 수준"
        else:
            verdict = "👍 칼로리 낮음"
            detail = "저칼로리 제품이에요"

    percentage = f"오늘 칼로리의 **{pct:.0f}%**"

    return {
        "verdict": verdict,
        "detail": detail,
        "percentage": percentage
    }


def get_sugar_verdict(
    sugar: float,
    sugar_limit: float,
    meal_type: str
) -> Dict[str, str]:
    """
    당류 판정 메시지 생성
    """
    pct = (sugar / sugar_limit) * 100

    if pct > 30:
        verdict = "🛑 당류 매우 높음"
        detail = "당류가 과도하게 많습니다"
    elif pct > 20:
        verdict = "⚠️ 당류 높음"
        detail = "당류에 주의가 필요해요"
    elif pct > 10:
        verdict = "⚠️ 당류 보통"
        detail = "일반적인 수준의 당류"
    elif pct > 5:
        verdict = "✅ 당류 낮음"
        detail = "저당 제품이에요"
    else:
        verdict = "👍 당류 매우 낮음"
        detail = "무설탕 수준입니다"

    percentage = f"당 권장량의 **{pct:.0f}%**"

    return {
        "verdict": verdict,
        "detail": detail,
        "percentage": percentage
    }


def get_overall_verdict(
    protein_verdict: str,
    calorie_verdict: str,
    sugar_verdict: str,
    goal_type: str
) -> str:
    """
    종합 판정 메시지

    Args:
        protein_verdict: "👍 단백질 충분" 등
        calorie_verdict: "✅ 칼로리 적정" 등
        sugar_verdict: "✅ 당류 낮음" 등
        goal_type: bulk, diet, diabetes, maintain

    Returns:
        종합 판정 문구
    """
    if goal_type == "bulk":
        # 벌크업: 단백질 > 칼로리 > 당류
        if "충분" in protein_verdict or "적정" in protein_verdict:
            if "초과" not in calorie_verdict:
                return "💪 벌크업에 **최적**입니다"
            else:
                return "💪 단백질은 좋지만 칼로리를 주의하세요"
        else:
            return "⚠️ 벌크업에는 단백질이 부족해요"

    elif goal_type == "diet":
        # 다이어트: 칼로리 낮고 단백질 있으면 좋음
        if "낮음" in calorie_verdict or "적정" in calorie_verdict:
            if "부족" not in protein_verdict:
                return "🥗 다이어트에 **최적**입니다"
            else:
                return "🥗 저칼로리지만 단백질이 부족해요"
        else:
            return "⚠️ 다이어트에는 칼로리가 높아요"

    elif goal_type == "diabetes":
        # 당뇨: 당류 최우선
        if "매우 낮음" in sugar_verdict or "낮음" in sugar_verdict:
            return "💉 당뇨 관리에 **안전**합니다"
        elif "보통" in sugar_verdict:
            return "⚠️ 당류를 주의하며 드세요"
        else:
            return "🛑 당뇨 관리에 **부적합**합니다"

    else:  # maintain
        # 균형: 모두 적정하면 좋음
        if "적정" in protein_verdict and "적정" in calorie_verdict and "낮음" in sugar_verdict:
            return "⚖️ 균형 잡힌 **완벽한 식사**입니다"
        else:
            return "⚖️ 일반적인 식사입니다"


# 예시 메시지 출력
if __name__ == "__main__":
    # 테스트
    result = get_protein_verdict(
        effective_protein=22.0,  # 닭가슴살 100g (현실 상한 20g 적용)
        goal_protein=60.0,
        meal_type="SINGLE_PROTEIN"
    )

    print("=" * 60)
    print("STOPPER 메시지 테스트")
    print("=" * 60)
    print(f"판정: {result['verdict']}")
    print(f"설명: {result['detail']}")
    print(f"비율: {result['percentage']}")
    print("=" * 60)
