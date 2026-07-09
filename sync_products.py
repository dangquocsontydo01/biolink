#!/usr/bin/env python3
"""
sync_products.py
=================
Đọc danh sách link sản phẩm Shopee trong `product_urls.txt`, tự động lấy
tên / ảnh / mô tả / giá từ metadata công khai (og:title, og:image,
og:description) của từng trang sản phẩm, rồi ghi ra `products.json` để
`index.html` tự nạp khi load trang (không cần sửa HTML/CONFIG tay nữa).

QUAN TRỌNG — đọc trước khi chạy:
- Đây KHÔNG phải API chính chủ của Shopee. Shopee không cung cấp API công
  khai để đọc bộ sưu tập affiliate (collshp.com/...). Script này chỉ đọc
  metadata công khai của TỪNG trang sản phẩm — giống cách Facebook/Zalo
  tạo link preview khi bạn dán link vào khung chat.
- Việc parse GIÁ dựa trên tìm chuỗi JSON nhúng trong HTML (best-effort).
  Shopee có thể đổi cấu trúc trang bất cứ lúc nào khiến phần này gãy —
  không coi đây là nguồn dữ liệu giá tuyệt đối chính xác, luôn có thể
  override giá thủ công trong product_urls.txt (xem cột `price_override`).
- Chưa test được với shopee.vn thật (môi trường sandbox tạo file này không
  có quyền truy cập mạng ra shopee.vn). Chạy thử `python sync_products.py`
  với 1-2 link thật trên máy/VPS của bạn trước, kiểm tra products.json
  sinh ra có đúng không rồi hẵng đưa vào cron.
- Nếu Shopee chặn bot (403 / trang trắng / captcha), script sẽ báo lỗi rõ
  ràng cho từng URL và BỎ QUA (không crash toàn bộ), sản phẩm đó bạn điền
  tay trong CONFIG.links như cũ.

Cách dùng:
  1. Mở product_urls.txt, mỗi dòng 1 sản phẩm:
       <url>, <category_id>, [emoji], [tag], [price_override]
     Ví dụ:
       https://s.shopee.vn/3B5PGyz8YC, hot, 🔥, hot,
       https://shopee.vn/product/xxx/yyy, home, 🏠, , 199000

  2. Chạy:
       pip install requests beautifulsoup4 --break-system-packages
       python sync_products.py

  3. products.json được ghi ra cùng thư mục. Upload/deploy file này cùng
     index.html lên VPS (hoặc dùng rsync/scp, hoặc git push nếu bạn deploy
     qua GitHub Pages/Cloudflare Pages).

  4. (Tuỳ chọn) Đặt cron trên VPS để tự refresh giá + phát hiện sản phẩm
     hết hàng định kỳ, ví dụ mỗi ngày 1 lần:
       0 6 * * * cd /var/www/biolink && /usr/bin/python3 sync_products.py >> sync.log 2>&1

Quy trình thêm sản phẩm mới của bạn từ giờ:
  Thêm 1 dòng URL vào product_urls.txt → chạy script → deploy products.json.
  (Không còn phải tự tay copy tên/ảnh/giá/mô tả nữa.)
"""

import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from html import unescape

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Thiếu thư viện. Chạy: pip install requests beautifulsoup4 --break-system-packages")
    sys.exit(1)

INPUT_FILE = Path(__file__).parent / "product_urls.txt"
OUTPUT_FILE = Path(__file__).parent / "products.json"
REQUEST_DELAY_SEC = 2.0  # nghỉ giữa các request để tránh bị chặn/rate-limit

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# Các pattern giá thường gặp trong JSON nhúng của trang Shopee (best-effort,
# có thể cần chỉnh lại nếu Shopee đổi cấu trúc trang).
PRICE_PATTERNS = [
    r'"price"\s*:\s*(\d{6,})',       # đơn vị micro (giá thật * 100000)
    r'"price_min"\s*:\s*(\d{6,})',
    r'"priceMin"\s*:\s*(\d{6,})',
]


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split(",")]
    url = parts[0]
    category = parts[1] if len(parts) > 1 and parts[1] else "all"
    emoji = parts[2] if len(parts) > 2 and parts[2] else "🛍️"
    tag = parts[3] if len(parts) > 3 and parts[3] else ""
    price_override = parts[4] if len(parts) > 4 and parts[4] else ""
    return {
        "url": url,
        "category": category,
        "emoji": emoji,
        "tag": tag,
        "price_override": price_override,
    }


def clean_text(text: str, max_len: int = None) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def format_price_vnd(amount: int) -> str:
    return f"{amount:,.0f}".replace(",", ".") + "₫"


def extract_price(html: str) -> str:
    for pattern in PRICE_PATTERNS:
        m = re.search(pattern, html)
        if m:
            raw = int(m.group(1))
            vnd = raw / 100000  # Shopee internal API dùng đơn vị micro (x100000)
            if 1000 <= vnd <= 500_000_000:  # lọc giá trị vô lý
                return format_price_vnd(vnd)
    return ""


def fetch_product(item: dict) -> dict | None:
    url = item["url"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ Lỗi tải trang: {url}\n    {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def meta(prop):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return tag["content"].strip() if tag and tag.get("content") else ""

    title = clean_text(meta("og:title"), max_len=90)
    image = meta("og:image")
    desc = clean_text(meta("og:description"), max_len=80)

    if not title:
        print(f"  ✗ Không lấy được tên sản phẩm (có thể bị chặn bot / trang JS-render): {url}")
        return None

    price = ""
    if item["price_override"]:
        try:
            price = format_price_vnd(int(item["price_override"]))
        except ValueError:
            price = item["price_override"]
    else:
        price = extract_price(resp.text)
        if not price:
            print(f"  ⚠ Không parse được giá tự động, cần điền price_override tay: {url}")

    print(f"  ✓ {title[:50]}{'...' if len(title) > 50 else ''}")

    return {
        "title": title,
        "sub": desc,
        "url": url,  # giữ nguyên link affiliate gốc để không mất tracking
        "thumb": image,
        "price": price,
        "emoji": item["emoji"],
        "tag": item["tag"],
        "category": item["category"],
    }


def main():
    if not INPUT_FILE.exists():
        print(f"Không tìm thấy {INPUT_FILE.name}. Tạo file này với mỗi dòng 1 URL sản phẩm Shopee.")
        sys.exit(1)

    items = []
    with open(INPUT_FILE, encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                items.append(parsed)

    if not items:
        print(f"{INPUT_FILE.name} rỗng. Thêm ít nhất 1 URL sản phẩm.")
        sys.exit(1)

    print(f"Đang đồng bộ {len(items)} sản phẩm...")
    results = []
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['url']}")
        product = fetch_product(item)
        if product:
            results.append(product)
        if i < len(items):
            time.sleep(REQUEST_DELAY_SEC)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nXong. {len(results)}/{len(items)} sản phẩm được ghi vào {OUTPUT_FILE.name}")
    if len(results) < len(items):
        print("Một số sản phẩm bị bỏ qua (xem lỗi ✗ ở trên) — kiểm tra link hoặc điền tay vào CONFIG.links.")


if __name__ == "__main__":
    main()
