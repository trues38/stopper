"""
편의점 제품 DB 관리
"""
import json
import os
from typing import Optional, Dict, List
from pathlib import Path


# 편의점 제품 DB 경로
CONVENIENCE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "convenience_products.json"

# 메모리 캐시
_convenience_products = None


def load_convenience_products() -> List[Dict]:
    """
    편의점 제품 DB 로드 (메모리 캐시)

    Returns:
        [
            {
                "name": "삼립)메가불고기버터갈릭버거",
                "price": "3,700",
                "calories": 320,
                "protein": 12.5,
                "sugar": 8.0,
                "sodium": 450,
                "fat": 15.0,
                "carbohydrate": 45.0,
                "manufacturer": "삼립식품",
                "serving_size": "1개(200g)"
            },
            ...
        ]
    """
    global _convenience_products

    if _convenience_products is not None:
        return _convenience_products

    if not CONVENIENCE_DB_PATH.exists():
        print(f"⚠️ 편의점 DB 파일 없음: {CONVENIENCE_DB_PATH}")
        return []

    try:
        with open(CONVENIENCE_DB_PATH, 'r', encoding='utf-8') as f:
            _convenience_products = json.load(f)
        print(f"✅ 편의점 제품 {len(_convenience_products)}개 로드 완료")
        return _convenience_products
    except Exception as e:
        print(f"❌ 편의점 DB 로드 실패: {e}")
        return []


def normalize_product_name(name: str) -> str:
    """
    제품명 정규화 (매칭용)

    - 괄호를 공백으로 변환: 삼립)메가불고기 → 삼립 메가불고기
    - 소문자 변환
    - 공백 정리
    """
    import re

    # 괄호를 공백으로 변환 (키워드 분리를 위해)
    normalized = re.sub(r'[\(\)\[\]）]', ' ', name)

    # 소문자 변환
    normalized = normalized.lower().strip()

    # 연속 공백 → 하나로
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized


def extract_keywords(name: str) -> set:
    """제품명에서 핵심 키워드 추출"""
    import re

    normalized = normalize_product_name(name)

    # 한글 단어 추출 (2글자 이상)
    korean_words = re.findall(r'[가-힣]{2,}', normalized)

    # 영어 단어 추출
    english_words = re.findall(r'[a-z]{2,}', normalized)

    return set(korean_words + english_words)


def match_convenience_product(i2570_name: str, manufacturer: str = None) -> Optional[Dict]:
    """
    I2570 제품명으로 편의점 DB 매칭

    Args:
        i2570_name: I2570 API에서 받은 제품명 (예: "삼)딸기샌드위치")
        manufacturer: 제조사 (선택, 매칭 정확도 향상)

    Returns:
        편의점 제품 정보 또는 None
    """
    products = load_convenience_products()

    if not products:
        return None

    # I2570 제품명 정규화
    i2570_norm = normalize_product_name(i2570_name)
    i2570_keywords = extract_keywords(i2570_name)

    # 1차: 정확한 이름 매칭
    for product in products:
        cvs_name = product.get('name', '')
        cvs_norm = normalize_product_name(cvs_name)

        if i2570_norm in cvs_norm or cvs_norm in i2570_norm:
            return product

    # 2차: 키워드 매칭 (제조사 무관, 핵심 단어만 매칭)
    best_match = None
    max_match_score = 0

    for product in products:
        cvs_name = product.get('name', '')
        cvs_keywords = extract_keywords(cvs_name)

        # 공통 키워드 수
        common_keywords = i2570_keywords & cvs_keywords
        match_score = len(common_keywords)

        # 최소 1개 이상 키워드 일치 (3글자 이상 키워드만)
        # "딸기샌드위치" 같은 고유명사는 1개만 일치해도 충분
        long_keywords = [k for k in common_keywords if len(k) >= 3]
        if long_keywords and match_score > max_match_score:
            max_match_score = match_score
            best_match = product

    if best_match:
        return best_match

    # 3차: 제조사 + 키워드 매칭
    if manufacturer:
        mfr_norm = normalize_product_name(manufacturer)

        for product in products:
            cvs_mfr = product.get('manufacturer', '')
            if not cvs_mfr:
                continue

            cvs_mfr_norm = normalize_product_name(cvs_mfr)

            # 제조사 일치 확인
            if mfr_norm in cvs_mfr_norm or cvs_mfr_norm in mfr_norm:
                cvs_keywords = extract_keywords(product.get('name', ''))
                common = i2570_keywords & cvs_keywords

                if len(common) >= 1:
                    return product

    return None


def search_convenience_products(query: str, limit: int = 20) -> List[Dict]:
    """
    편의점 제품 검색

    Args:
        query: 검색어
        limit: 최대 결과 수

    Returns:
        매칭된 제품 리스트
    """
    products = load_convenience_products()

    if not products:
        return []

    query_norm = normalize_product_name(query)
    results = []

    for product in products:
        name = product.get('name', '')
        name_norm = normalize_product_name(name)

        if query_norm in name_norm:
            results.append(product)

            if len(results) >= limit:
                break

    return results
