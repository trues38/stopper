"""
7-Eleven Requests 기반 크롤링 (JavaScript 변수 파싱)
"""
import requests
import re
import json
from pathlib import Path


def crawl_7eleven_simple():
    """7-Eleven - Requests + JavaScript 파싱"""
    print("🔍 7-Eleven 크롤링 시작...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    products = []

    # 초기 페이지 로드
    response = requests.get('https://www.7-eleven.co.kr/product/bestdosirakList.asp', headers=headers)
    page_source = response.text

    # galleryArray 추출
    match = re.search(r'galleryArray\s*=\s*\[(.*?)\];', page_source, re.DOTALL)

    if match:
        array_content = match.group(1)
        objects = re.findall(r'\{([^}]+)\}', array_content)
        print(f"   초기 페이지: {len(objects)}개 제품")

        for obj_str in objects:
            name_match = re.search(r"(?:alt|title):\s*'([^']+)'", obj_str)
            price_match = re.search(r"price:\s*'([^']+)'", obj_str)
            img_match = re.search(r"src:\s*'([^']+)'", obj_str)

            if name_match:
                name = name_match.group(1)
                price = price_match.group(1).replace(',', '') if price_match else None
                img_url = img_match.group(1) if img_match else None

                if img_url and img_url.startswith('/'):
                    img_url = f"https://www.7-eleven.co.kr{img_url}"

                products.append({
                    "store": "7-ELEVEN",
                    "name": name,
                    "price": price,
                    "image_url": img_url
                })

    # 모든 탭 크롤링 (pTab=1~4: 전체, 도시락, 김밥, 샌드위치)
    for tab_id in [2, 3, 4]:  # tab 1은 이미 했으니 2~4만
        try:
            tab_url = f"https://www.7-eleven.co.kr/product/bestdosirakList.asp?pTab={tab_id}"
            response = requests.get(tab_url, headers=headers)

            match = re.search(r'galleryArray\s*=\s*\[(.*?)\];', response.text, re.DOTALL)
            if match:
                array_content = match.group(1)
                objects = re.findall(r'\{([^}]+)\}', array_content)
                print(f"   Tab {tab_id}: {len(objects)}개 제품")

                for obj_str in objects:
                    name_match = re.search(r"(?:alt|title):\s*'([^']+)'", obj_str)
                    price_match = re.search(r"price:\s*'([^']+)'", obj_str)
                    img_match = re.search(r"src:\s*'([^']+)'", obj_str)

                    if name_match:
                        name = name_match.group(1)

                        # 중복 체크
                        if name in [p['name'] for p in products]:
                            continue

                        price = price_match.group(1).replace(',', '') if price_match else None
                        img_url = img_match.group(1) if img_match else None

                        if img_url and img_url.startswith('/'):
                            img_url = f"https://www.7-eleven.co.kr{img_url}"

                        products.append({
                            "store": "7-ELEVEN",
                            "name": name,
                            "price": price,
                            "image_url": img_url
                        })
        except Exception as e:
            print(f"   Tab {tab_id} 오류: {e}")

    print(f"✅ 7-Eleven: {len(products)}개 제품")
    return products


if __name__ == "__main__":
    products = crawl_7eleven_simple()

    output_file = Path("/Users/js/Documents/stopper/data/convenience_crawl/7eleven_products.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"저장: {output_file}")
