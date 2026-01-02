"""
3대 편의점 Freshfood 크롤링 (Requests 기반)
- 세븐일레븐, CU, GS25
- API 직접 호출 방식
"""
import os
import json
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re


# 출력 디렉토리
OUTPUT_DIR = Path("/Users/js/Documents/stopper/data/convenience_crawl")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGES_DIR = OUTPUT_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)


def download_image(url, save_path):
    """이미지 다운로드"""
    try:
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            return None

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return str(save_path)
    except Exception as e:
        print(f"   이미지 다운로드 실패: {url[:50]}... - {e}")
    return None


def crawl_7eleven():
    """세븐일레븐 freshfood 크롤링 (AJAX API 직접 호출)"""
    print("\n🔍 세븐일레븐 크롤링 시작...")

    products = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.7-eleven.co.kr/product/bestdosirakList.asp'
        }

        # 초기 페이지 로드
        response = requests.get(
            'https://www.7-eleven.co.kr/product/bestdosirakList.asp',
            headers=headers
        )

        soup = BeautifulSoup(response.text, 'html.parser')

        # 제품 리스트 파싱
        product_items = soup.select('.wrap_list_02 li')
        print(f"   초기 페이지: {len(product_items)}개 제품 발견")

        for item in product_items:
            try:
                img_elem = item.find('img')
                if not img_elem:
                    continue

                name = img_elem.get('alt', '').strip()
                img_url = img_elem.get('src', '')

                # 가격 추출
                price = None
                text = item.get_text()
                if '원' in text:
                    price_match = re.search(r'([\d,]+)원', text)
                    if price_match:
                        price = price_match.group(1).replace(',', '')

                if img_url.startswith('/'):
                    img_url = f"https://www.7-eleven.co.kr{img_url}"

                if name:
                    products.append({
                        "store": "7-ELEVEN",
                        "name": name,
                        "price": price,
                        "image_url": img_url
                    })

            except Exception as e:
                continue

        # MORE 버튼 AJAX 호출 (페이지 확장)
        page_size = 4
        max_pages = 50

        for page in range(1, max_pages):
            try:
                ajax_url = "https://www.7-eleven.co.kr/product/dosirakNewMoreAjax.asp"
                ajax_data = {
                    'intPageSize': page_size * (page + 1),
                    'pTab': '1'
                }

                ajax_response = requests.post(ajax_url, data=ajax_data, headers=headers, timeout=10)

                if ajax_response.status_code != 200:
                    break

                ajax_soup = BeautifulSoup(ajax_response.text, 'html.parser')
                ajax_items = ajax_soup.select('li')

                if not ajax_items:
                    break

                print(f"   페이지 {page + 1}: {len(ajax_items)}개 추가 제품")

                for item in ajax_items:
                    try:
                        img_elem = item.find('img')
                        if not img_elem:
                            continue

                        name = img_elem.get('alt', '').strip()
                        img_url = img_elem.get('src', '')

                        price = None
                        text = item.get_text()
                        if '원' in text:
                            price_match = re.search(r'([\d,]+)원', text)
                            if price_match:
                                price = price_match.group(1).replace(',', '')

                        if img_url.startswith('/'):
                            img_url = f"https://www.7-eleven.co.kr{img_url}"

                        if name and name not in [p['name'] for p in products]:
                            products.append({
                                "store": "7-ELEVEN",
                                "name": name,
                                "price": price,
                                "image_url": img_url
                            })

                    except Exception as e:
                        continue

                time.sleep(0.5)

            except Exception as e:
                print(f"   페이지 {page + 1} 로드 실패: {e}")
                break

        print(f"\n✅ 세븐일레븐: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ 세븐일레븐 크롤링 오류: {e}")

    return products


def crawl_cu():
    """CU freshfood 크롤링 (AJAX API 직접 호출)"""
    print("\n🔍 CU 크롤링 시작...")

    products = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://cu.bgfretail.com/product/product.do'
        }

        # depth3 카테고리 순회 (1~10까지 시도)
        for depth3 in range(1, 11):
            try:
                print(f"\n   카테고리 depth3={depth3} 크롤링...")

                # AJAX 엔드포인트 호출
                ajax_url = "https://cu.bgfretail.com/product/productAjax.do"

                for page in range(1, 20):
                    ajax_data = {
                        'pageIndex': page,
                        'listType': 'list',
                        'category': 'product',
                        'depth2': '4',
                        'depth3': str(depth3)
                    }

                    response = requests.post(ajax_url, data=ajax_data, headers=headers, timeout=10)

                    if response.status_code != 200:
                        break

                    soup = BeautifulSoup(response.text, 'html.parser')
                    items = soup.select('li')

                    if not items:
                        break

                    print(f"      페이지 {page}: {len(items)}개 제품")

                    for item in items:
                        try:
                            # 제품명
                            name_elem = item.select_one('.prodName, .prod_name, .name')
                            if not name_elem:
                                continue

                            name = name_elem.get_text().strip()

                            # 가격
                            price = None
                            price_elem = item.select_one('.price em, .cost em, .price')
                            if price_elem:
                                price = price_elem.get_text().strip().replace(',', '').replace('원', '')

                            # 이미지
                            img_elem = item.find('img')
                            img_url = None
                            if img_elem:
                                img_url = img_elem.get('src', '')
                                if img_url.startswith('/'):
                                    img_url = f"https://cu.bgfretail.com{img_url}"

                            if name and name not in [p['name'] for p in products]:
                                products.append({
                                    "store": "CU",
                                    "name": name,
                                    "price": price,
                                    "image_url": img_url
                                })

                        except Exception as e:
                            continue

                    time.sleep(0.3)

            except Exception as e:
                print(f"   카테고리 {depth3} 오류: {e}")
                continue

        print(f"\n✅ CU: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ CU 크롤링 오류: {e}")

    return products


def crawl_gs25():
    """GS25 freshfood 크롤링"""
    print("\n🔍 GS25 크롤링 시작...")

    products = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'http://gs25.gsretail.com/gscvs/ko/products/youus-freshfood'
        }

        # 카테고리 페이지 조회
        response = requests.get(
            'http://gs25.gsretail.com/gscvs/ko/products/youus-freshfood',
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(response.text, 'html.parser')

        # 제품 리스트 파싱
        items = soup.select('.prod_box, .product-list-item, .prod_list li')
        print(f"   {len(items)}개 제품 발견")

        for item in items:
            try:
                # 제품명
                name_elem = item.select_one('.tit, .prod_name, .name')
                if not name_elem:
                    continue

                name = name_elem.get_text().strip()

                # 가격
                price = None
                price_elem = item.select_one('.price, .cost em, .cost')
                if price_elem:
                    price = price_elem.get_text().strip().replace(',', '').replace('원', '')

                # 이미지
                img_elem = item.find('img')
                img_url = None
                if img_elem:
                    img_url = img_elem.get('src', '')
                    if img_url.startswith('/'):
                        img_url = f"http://gs25.gsretail.com{img_url}"

                if name:
                    products.append({
                        "store": "GS25",
                        "name": name,
                        "price": price,
                        "image_url": img_url
                    })

            except Exception as e:
                continue

        print(f"\n✅ GS25: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ GS25 크롤링 오류: {e}")

    return products


def download_all_images(products):
    """수집한 제품의 이미지 일괄 다운로드"""
    print("\n📥 이미지 다운로드 시작...")

    downloaded = 0
    failed = 0

    for idx, product in enumerate(products, 1):
        img_url = product.get('image_url')
        if not img_url:
            continue

        # 파일명: store_제품명처음10자_index.jpg
        store = product['store'].lower().replace('-', '')
        safe_name = re.sub(r'[^\w가-힣]', '', product['name'][:10])
        filename = f"{store}_{safe_name}_{idx:04d}.jpg"
        save_path = IMAGES_DIR / filename

        if download_image(img_url, save_path):
            product['image_path'] = filename  # 상대 경로만 저장
            downloaded += 1
        else:
            failed += 1

        if idx % 20 == 0:
            print(f"   진행: {idx}/{len(products)} (성공: {downloaded}, 실패: {failed})")

    print(f"\n✅ 이미지 다운로드 완료: {downloaded}개 성공, {failed}개 실패")


def main():
    """메인 실행"""
    print("="*60)
    print("🏪 3대 편의점 Freshfood 크롤링")
    print("="*60)

    all_products = []

    # 1. 세븐일레븐
    products_7eleven = crawl_7eleven()
    all_products.extend(products_7eleven)

    # 2. CU
    products_cu = crawl_cu()
    all_products.extend(products_cu)

    # 3. GS25
    products_gs25 = crawl_gs25()
    all_products.extend(products_gs25)

    print("\n" + "="*60)
    print(f"📊 전체 수집 결과")
    print("="*60)
    print(f"세븐일레븐: {len(products_7eleven)}개")
    print(f"CU: {len(products_cu)}개")
    print(f"GS25: {len(products_gs25)}개")
    print(f"총합: {len(all_products)}개")

    # JSON 저장
    output_file = OUTPUT_DIR / "convenience_products_all.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"\n💾 데이터 저장: {output_file}")

    # 이미지 다운로드
    download_all_images(all_products)

    # 이미지 다운로드 후 최종 JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 크롤링 완료!")
    print(f"   데이터: {output_file}")
    print(f"   이미지: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
