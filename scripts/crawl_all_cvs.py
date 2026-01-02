"""
3대 편의점 Freshfood 크롤링 (개선 버전)
- 7-Eleven: Selenium + JavaScript 변수 추출
- CU: Requests + AJAX API
- GS25: Selenium + HTML 파싱
"""
import os
import json
import time
import re
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup


# 출력 디렉토리
OUTPUT_DIR = Path("/Users/js/Documents/stopper/data/convenience_crawl")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGES_DIR = OUTPUT_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)


def init_driver(headless=False):
    """Chrome driver 초기화"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def download_image(url, save_path):
    """이미지 다운로드"""
    try:
        # Fix double slash in URL
        if '//' in url[8:]:
            url = url.replace('cu.bgfretail.com//', '')
            if not url.startswith('http'):
                url = 'https://' + url

        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            # Relative URL - skip for now
            return None

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0'
        })

        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return str(save_path.name)
    except Exception as e:
        print(f"   이미지 실패: {url[:50]}...")
    return None


def crawl_7eleven():
    """7-Eleven - Selenium + JavaScript 변수 추출"""
    print("\n🔍 7-Eleven 크롤링 시작...")

    driver = init_driver(headless=False)
    products = []

    try:
        url = "https://www.7-eleven.co.kr/product/bestdosirakList.asp"
        driver.get(url)
        time.sleep(2)

        # MORE 버튼 클릭해서 전체 로드
        click_count = 0
        max_clicks = 50

        while click_count < max_clicks:
            try:
                more_btn = driver.find_element(By.CLASS_NAME, "btn_more")

                if "none" in more_btn.get_attribute("style") or not more_btn.is_displayed():
                    print(f"   더 이상 제품 없음 (클릭 {click_count}회)")
                    break

                driver.execute_script("arguments[0].click();", more_btn)
                click_count += 1

                if click_count % 10 == 0:
                    print(f"   MORE 버튼 클릭: {click_count}회")

                time.sleep(1)

            except NoSuchElementException:
                print(f"   MORE 버튼 없음 (클릭 {click_count}회)")
                break
            except Exception as e:
                print(f"   클릭 중단: {e}")
                break

        # JavaScript 변수 galleryArray 추출
        page_source = driver.page_source
        match = re.search(r'galleryArray\s*=\s*\[(.*?)\];', page_source, re.DOTALL)

        if match:
            array_content = match.group(1)
            # 개별 객체 추출
            objects = re.findall(r'\{([^}]+)\}', array_content)
            print(f"   galleryArray: {len(objects)}개 제품 발견")

            for obj_str in objects:
                # 필드 파싱
                name_match = re.search(r"alt:\s*'([^']+)'", obj_str)
                price_match = re.search(r"price:\s*'([^']+)'", obj_str)
                img_match = re.search(r"src:\s*'([^']+)'", obj_str)

                if name_match:
                    name = name_match.group(1)
                    price = price_match.group(1).replace(',', '') if price_match else None
                    img_url = img_match.group(1) if img_match else None

                    # 상대 경로를 절대 경로로
                    if img_url and img_url.startswith('/'):
                        img_url = f"https://www.7-eleven.co.kr{img_url}"

                    products.append({
                        "store": "7-ELEVEN",
                        "name": name,
                        "price": price,
                        "image_url": img_url
                    })

        print(f"\n✅ 7-Eleven: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ 7-Eleven 크롤링 오류: {e}")
    finally:
        driver.quit()

    return products


def crawl_cu():
    """CU - Requests + AJAX API (기존 방식)"""
    print("\n🔍 CU 크롤링 시작...")

    products = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://cu.bgfretail.com/product/product.do'
        }

        for depth3 in range(1, 11):
            print(f"\n   카테고리 depth3={depth3} 크롤링...")

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

                if page == 1:
                    print(f"      페이지 {page}: {len(items)}개 제품")

                for item in items:
                    try:
                        name_elem = item.select_one('.prodName, .prod_name, .name')
                        if not name_elem:
                            continue

                        name = name_elem.get_text().strip()

                        price = None
                        price_elem = item.select_one('.price em, .cost em, .price')
                        if price_elem:
                            price = price_elem.get_text().strip().replace(',', '').replace('원', '')

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

                    except Exception:
                        continue

                time.sleep(0.3)

        print(f"\n✅ CU: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ CU 크롤링 오류: {e}")

    return products


def crawl_gs25():
    """GS25 - Selenium + HTML 파싱"""
    print("\n🔍 GS25 크롤링 시작...")

    driver = init_driver(headless=False)
    products = []

    try:
        url = "http://gs25.gsretail.com/gscvs/ko/products/youus-freshfood"
        driver.get(url)
        time.sleep(3)

        # 스크롤 다운으로 제품 로드
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 30

        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height
            scroll_count += 1

            if scroll_count % 5 == 0:
                print(f"   스크롤: {scroll_count}회")

        # 페이지 소스에서 제품 추출
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 다양한 셀렉터 시도
        selectors = [
            '.prod_box',
            '.product-list-item',
            '.prod_list li',
            'div.prod',
            'li[class*="prod"]'
        ]

        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                print(f"   셀렉터 '{selector}': {len(items)}개 발견")
                break

        if not items:
            # li 태그 전체 중에서 이미지가 있는 것만
            all_lis = soup.find_all('li')
            items = [li for li in all_lis if li.find('img', src=True)]
            print(f"   이미지 포함 LI: {len(items)}개")

        for item in items:
            try:
                # 제품명
                name_elem = item.select_one('.tit, .prod_name, .name, .prodName')
                if not name_elem:
                    # alt 속성에서 찾기
                    img = item.find('img')
                    if img:
                        name = img.get('alt', '').strip()
                    else:
                        continue
                else:
                    name = name_elem.get_text().strip()

                if not name or len(name) < 3:
                    continue

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

            except Exception:
                continue

        print(f"\n✅ GS25: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ GS25 크롤링 오류: {e}")
    finally:
        driver.quit()

    return products


def download_all_images(products):
    """이미지 일괄 다운로드"""
    print("\n📥 이미지 다운로드 시작...")

    downloaded = 0
    failed = 0

    for idx, product in enumerate(products, 1):
        img_url = product.get('image_url')
        if not img_url:
            failed += 1
            continue

        # 파일명: store_제품명처음10자_index.jpg
        store = product['store'].lower().replace('-', '')
        safe_name = re.sub(r'[^\w가-힣]', '', product['name'][:10])
        filename = f"{store}_{safe_name}_{idx:04d}.jpg"
        save_path = IMAGES_DIR / filename

        result = download_image(img_url, save_path)
        if result:
            product['image_file'] = result
            downloaded += 1
        else:
            failed += 1

        if idx % 50 == 0:
            print(f"   진행: {idx}/{len(products)} (성공: {downloaded}, 실패: {failed})")

    print(f"\n✅ 이미지 다운로드 완료: {downloaded}개 성공, {failed}개 실패")


def main():
    """메인 실행"""
    print("="*60)
    print("🏪 3대 편의점 Freshfood 크롤링")
    print("="*60)

    all_products = []

    # 1. 7-Eleven
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
    print(f"7-Eleven: {len(products_7eleven)}개")
    print(f"CU: {len(products_cu)}개")
    print(f"GS25: {len(products_gs25)}개")
    print(f"총합: {len(all_products)}개")

    # JSON 저장 (이미지 다운로드 전)
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
