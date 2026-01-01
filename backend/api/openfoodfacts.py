"""
Open Food Facts API 연동
"""

import requests
from typing import Optional, Dict
from difflib import SequenceMatcher

OFF_API = "https://world.openfoodfacts.org/api/v2"

def fetch_product_by_barcode(barcode: str) -> Optional[Dict]:
    """
    Open Food Facts에서 바코드로 제품 조회

    Args:
        barcode: 제품 바코드 (13자리)

    Returns:
        제품 정보 dict 또는 None
    """
    try:
        url = f"{OFF_API}/product/{barcode}"
        res = requests.get(url, timeout=10)
        data = res.json()

        if data.get('status') != 1:
            return None

        product = data.get('product', {})

        # 한국어 정보 우선, 없으면 영어
        name = (
            product.get('product_name_ko') or
            product.get('product_name_kr') or
            product.get('product_name') or
            ''
        )

        brand = product.get('brands', '')

        # 영양성분
        nutriments = product.get('nutriments', {})

        return {
            'barcode': barcode,
            'name': name.strip(),
            'brand': brand.strip(),
            'calories': nutriments.get('energy-kcal_100g', 0),
            'protein': nutriments.get('proteins_100g', 0),
            'fat': nutriments.get('fat_100g', 0),
            'carbohydrate': nutriments.get('carbohydrates_100g', 0),
            'sugar': nutriments.get('sugars_100g', 0),
            'sodium': nutriments.get('sodium_100g', 0) * 1000,  # g → mg
            'serving_size': product.get('serving_size', '100g'),
            'image_url': product.get('image_url'),
            'categories': product.get('categories', ''),
        }

    except Exception as e:
        print(f"Open Food Facts API 오류: {e}")
        return None


def normalize_name(name: str) -> str:
    """제품명 정규화"""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = normalized.replace(' ', '').replace('(', '').replace(')', '')
    normalized = normalized.replace('[', '').replace(']', '')
    return normalized


def similarity(a: str, b: str) -> float:
    """문자열 유사도 (0~1)"""
    return SequenceMatcher(None, a, b).ratio()


def match_product_name(off_product: Dict, stopper_foods: list) -> Optional[Dict]:
    """
    Open Food Facts 제품을 STOPPER DB와 매칭

    Args:
        off_product: OFF 제품 정보
        stopper_foods: STOPPER DB 제품 리스트

    Returns:
        매칭된 제품 dict 또는 None
    """
    off_name = off_product.get('name', '')
    off_brand = off_product.get('brand', '')

    if not off_name:
        return None

    off_name_norm = normalize_name(off_name)

    best_match = None
    best_score = 0.0

    for food in stopper_foods:
        food_name_norm = normalize_name(food['name'])

        # 제품명 유사도
        score = similarity(off_name_norm, food_name_norm)

        # 제조사 매칭시 보너스
        if off_brand and food.get('manufacturer'):
            brand_norm = normalize_name(off_brand)
            mfg_norm = normalize_name(food['manufacturer'])
            if brand_norm in mfg_norm or mfg_norm in brand_norm:
                score += 0.15

        if score > best_score:
            best_score = score
            best_match = food

    # 유사도 75% 이상만 매칭
    if best_score >= 0.75:
        return {
            'food': best_match,
            'score': best_score
        }

    return None
