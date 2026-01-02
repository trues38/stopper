"""
3대 편의점 Freshfood 크롤링
- 세븐일레븐, CU, GS25
- 제품명, 가격, 이미지 URL 수집 및 이미지 다운로드
"""
import os
import json
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# 출력 디렉토리
OUTPUT_DIR = Path("/Users/js/Documents/stopper/data/convenience_crawl")
OUTPUT_DIR.mkdir(exist_ok=True)

IMAGES_DIR = OUTPUT_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)


def init_driver(headless=True):
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
        # 상대 경로를 절대 경로로 변환
        if url.startswith('/'):
            # 각 사이트의 base URL 추가 필요
            return None

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return str(save_path)
    except Exception as e:
        print(f"이미지 다운로드 실패: {url} - {e}")
    return None


def crawl_7eleven():
    """세븐일레븐 freshfood 크롤링"""
    print("\n🔍 세븐일레븐 크롤링 시작...")

    driver = init_driver(headless=False)
    products = []

    try:
        url = "https://www.7-eleven.co.kr/product/bestdosirakList.asp"
        driver.get(url)

        # 페이지 로드 대기
        time.sleep(2)

        # MORE 버튼 반복 클릭
        click_count = 0
        max_clicks = 50  # 최대 클릭 횟수

        while click_count < max_clicks:
            try:
                # MORE 버튼 찾기
                more_btn = driver.find_element(By.CLASS_NAME, "btn_more")

                # 버튼이 숨겨져 있으면 중단
                if "none" in more_btn.get_attribute("style") or not more_btn.is_displayed():
                    print("   더 이상 제품이 없습니다.")
                    break

                # 버튼 클릭
                driver.execute_script("arguments[0].click();", more_btn)
                click_count += 1
                print(f"   MORE 버튼 클릭: {click_count}회")

                # 로딩 대기
                time.sleep(1.5)

            except NoSuchElementException:
                print("   MORE 버튼을 찾을 수 없습니다.")
                break
            except Exception as e:
                print(f"   MORE 버튼 클릭 오류: {e}")
                break

        # 전체 제품 수집
        print("\n   제품 정보 수집 중...")

        product_items = driver.find_elements(By.CSS_SELECTOR, ".wrap_list_02 li")
        print(f"   총 {len(product_items)}개 제품 발견")

        for idx, item in enumerate(product_items, 1):
            try:
                # 이미지
                img_elem = item.find_element(By.TAG_NAME, "img")
                img_url = img_elem.get_attribute("src")

                # 제품명 (alt 속성 또는 title)
                name = img_elem.get_attribute("alt") or img_elem.get_attribute("title") or ""
                name = name.strip()

                # 가격 추출 (이미지 옆 텍스트에서)
                try:
                    # 가격은 보통 "원" 앞의 숫자
                    price_text = item.text
                    if "원" in price_text:
                        price = price_text.split("원")[0].strip().split()[-1]
                        price = price.replace(",", "")
                    else:
                        price = None
                except:
                    price = None

                if not name:
                    continue

                # 이미지 URL 절대 경로 변환
                if img_url.startswith('/'):
                    img_url = f"https://www.7-eleven.co.kr{img_url}"

                product = {
                    "store": "7-ELEVEN",
                    "name": name,
                    "price": price,
                    "image_url": img_url
                }

                products.append(product)

                if idx % 10 == 0:
                    print(f"   진행: {idx}/{len(product_items)}")

            except Exception as e:
                print(f"   제품 {idx} 파싱 오류: {e}")
                continue

        print(f"\n✅ 세븐일레븐: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ 세븐일레븐 크롤링 오류: {e}")
    finally:
        driver.quit()

    return products


def crawl_cu():
    """CU freshfood 크롤링"""
    print("\n🔍 CU 크롤링 시작...")

    driver = init_driver(headless=False)
    products = []

    try:
        # depth3=1부터 시작해서 여러 카테고리 크롤링
        categories = [1, 2, 3, 4, 5]  # freshfood 하위 카테고리

        for depth3 in categories:
            url = f"https://cu.bgfretail.com/product/product.do?category=product&depth2=4&depth3={depth3}"
            print(f"\n   카테고리 {depth3} 크롤링...")

            driver.get(url)
            time.sleep(2)

            # 스크롤을 내려서 모든 제품 로드
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count = 0
            max_scrolls = 10

            while scroll_count < max_scrolls:
                # 페이지 끝까지 스크롤
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                # 새로운 높이 계산
                new_height = driver.execute_script("return document.body.scrollHeight")

                # 더 이상 로드되지 않으면 중단
                if new_height == last_height:
                    break

                last_height = new_height
                scroll_count += 1
                print(f"      스크롤: {scroll_count}회")

            # 제품 수집
            try:
                product_items = driver.find_elements(By.CSS_SELECTOR, "#dataTable .prodListWrap li")
                print(f"      {len(product_items)}개 제품 발견")

                for item in product_items:
                    try:
                        # 제품명
                        name_elem = item.find_element(By.CSS_SELECTOR, ".prodName")
                        name = name_elem.text.strip()

                        # 가격
                        try:
                            price_elem = item.find_element(By.CSS_SELECTOR, ".price em")
                            price = price_elem.text.strip().replace(",", "")
                        except:
                            price = None

                        # 이미지
                        try:
                            img_elem = item.find_element(By.TAG_NAME, "img")
                            img_url = img_elem.get_attribute("src")

                            # 절대 경로 변환
                            if img_url and img_url.startswith('/'):
                                img_url = f"https://cu.bgfretail.com{img_url}"
                        except:
                            img_url = None

                        if name:
                            product = {
                                "store": "CU",
                                "name": name,
                                "price": price,
                                "image_url": img_url
                            }
                            products.append(product)

                    except Exception as e:
                        continue

            except NoSuchElementException:
                print(f"      카테고리 {depth3}에 제품이 없습니다.")
                continue

        print(f"\n✅ CU: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ CU 크롤링 오류: {e}")
    finally:
        driver.quit()

    return products


def crawl_gs25():
    """GS25 freshfood 크롤링"""
    print("\n🔍 GS25 크롤링 시작...")

    driver = init_driver(headless=False)
    products = []

    try:
        url = "http://gs25.gsretail.com/gscvs/ko/products/youus-freshfood"
        driver.get(url)

        # 페이지 로드 대기
        time.sleep(3)

        # 스크롤을 내려서 모든 제품 로드
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        max_scrolls = 20

        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height
            scroll_count += 1
            print(f"   스크롤: {scroll_count}회")

        # "더보기" 버튼 클릭 시도
        try:
            while True:
                more_btn = driver.find_element(By.CSS_SELECTOR, ".btn_more, .mCSB_buttonDown")
                if more_btn.is_displayed():
                    driver.execute_script("arguments[0].click();", more_btn)
                    time.sleep(2)
                else:
                    break
        except:
            pass

        # 제품 수집
        product_items = driver.find_elements(By.CSS_SELECTOR, ".prod_list li, .product-list-item")
        print(f"   {len(product_items)}개 제품 발견")

        for item in product_items:
            try:
                # 제품명
                name_elem = item.find_element(By.CSS_SELECTOR, ".tit, .prod_name, .name")
                name = name_elem.text.strip()

                # 가격
                try:
                    price_elem = item.find_element(By.CSS_SELECTOR, ".price, .cost em")
                    price = price_elem.text.strip().replace(",", "").replace("원", "")
                except:
                    price = None

                # 이미지
                try:
                    img_elem = item.find_element(By.TAG_NAME, "img")
                    img_url = img_elem.get_attribute("src")

                    if img_url and img_url.startswith('/'):
                        img_url = f"http://gs25.gsretail.com{img_url}"
                except:
                    img_url = None

                if name:
                    product = {
                        "store": "GS25",
                        "name": name,
                        "price": price,
                        "image_url": img_url
                    }
                    products.append(product)

            except Exception as e:
                continue

        print(f"\n✅ GS25: {len(products)}개 제품 수집 완료")

    except Exception as e:
        print(f"❌ GS25 크롤링 오류: {e}")
    finally:
        driver.quit()

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

        # 파일명: store_index.jpg
        store = product['store'].lower().replace('-', '')
        filename = f"{store}_{idx:04d}.jpg"
        save_path = IMAGES_DIR / filename

        if download_image(img_url, save_path):
            product['image_path'] = str(save_path)
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
