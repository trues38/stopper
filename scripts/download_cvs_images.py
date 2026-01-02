"""
편의점 제품 이미지 일괄 다운로드
"""
import json
import requests
from pathlib import Path
import time


# 경로 설정
DATA_FILE = Path("/Users/js/Documents/stopper/data/convenience_products.json")
IMAGES_DIR = Path("/Users/js/Documents/stopper/data/convenience_crawl/images")
IMAGES_DIR.mkdir(exist_ok=True)


def download_image(url, save_path):
    """이미지 다운로드"""
    try:
        # Fix double slash in URL (cu.bgfretail.com// -> direct CDN URL)
        if '//' in url[8:]:  # Skip protocol part (https://)
            url = url.replace('cu.bgfretail.com//', '')
            if not url.startswith('http'):
                url = 'https://' + url

        if url.startswith('//'):
            url = 'https:' + url

        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0'
        })

        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"   실패: {url[:50]}... - {e}")
    return False


def main():
    """메인 실행"""
    print("📥 편의점 제품 이미지 다운로드 시작\n")

    # JSON 로드
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        products = json.load(f)

    print(f"총 {len(products)}개 제품")

    downloaded = 0
    failed = 0

    for idx, product in enumerate(products, 1):
        img_url = product.get('image_url')
        if not img_url:
            failed += 1
            continue

        # 파일명: store_index.jpg
        store = product['store'].lower().replace('-', '')
        filename = f"{store}_{idx:04d}.jpg"
        save_path = IMAGES_DIR / filename

        if download_image(img_url, save_path):
            product['image_file'] = filename
            downloaded += 1
        else:
            failed += 1

        if idx % 50 == 0:
            print(f"진행: {idx}/{len(products)} (성공: {downloaded}, 실패: {failed})")

        time.sleep(0.1)

    # 업데이트된 JSON 저장
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료!")
    print(f"   성공: {downloaded}개")
    print(f"   실패: {failed}개")
    print(f"   이미지 폴더: {IMAGES_DIR}")


if __name__ == "__main__":
    main()
