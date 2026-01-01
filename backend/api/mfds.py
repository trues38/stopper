"""
식약처(MFDS) I2570 유통바코드 API 연동
"""
import requests
from typing import Optional, Dict

API_KEY = "14588a0a32f2476a8797"
API_BASE = "http://openapi.foodsafetykorea.go.kr/api"
SERVICE_NAME = "I2570"


def lookup_barcode_i2570(barcode: str) -> Optional[Dict]:
    """
    I2570 API로 바코드 조회

    Args:
        barcode: 13자리 바코드 번호

    Returns:
        {
            'barcode': '8801234567890',
            'name': '제품명',
            'manufacturer': '제조사명',
            'report_no': '품목보고번호'
        }
        또는 None (바코드 없음)
    """
    try:
        # BRCD_NO 파라미터로 바코드 직접 검색
        url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/1/5/BRCD_NO={barcode}"

        res = requests.get(url, timeout=10)
        data = res.json()

        if SERVICE_NAME not in data:
            return None

        items = data[SERVICE_NAME].get('row', [])

        if not items:
            return None

        # 첫 번째 결과 반환
        item = items[0]
        return {
            'barcode': barcode,
            'name': item.get('PRDT_NM', '').strip(),
            'manufacturer': item.get('CMPNY_NM', '').strip(),
            'report_no': item.get('PRDLST_REPORT_NO', '').strip()
        }

    except Exception as e:
        print(f"I2570 API 오류: {e}")
        return None


def search_product_name_i2570(product_name: str, max_results: int = 10) -> list:
    """
    I2570 API로 제품명 검색

    Args:
        product_name: 검색할 제품명
        max_results: 최대 결과 수

    Returns:
        [{
            'barcode': '8801234567890',
            'name': '제품명',
            'manufacturer': '제조사명',
            'report_no': '품목보고번호'
        }, ...]
    """
    try:
        url = f"{API_BASE}/{API_KEY}/{SERVICE_NAME}/json/1/{max_results}/PRDT_NM={product_name}"

        res = requests.get(url, timeout=10)
        data = res.json()

        if SERVICE_NAME not in data:
            return []

        items = data[SERVICE_NAME].get('row', [])

        results = []
        for item in items:
            results.append({
                'barcode': item.get('BRCD_NO', '').strip(),
                'name': item.get('PRDT_NM', '').strip(),
                'manufacturer': item.get('CMPNY_NM', '').strip(),
                'report_no': item.get('PRDLST_REPORT_NO', '').strip()
            })

        return results

    except Exception as e:
        print(f"I2570 API 오류: {e}")
        return []
