#!/usr/bin/env python3
"""
sync_products.py  (v3 - Playwright headless browser)
=====================================================
Dung Playwright de mo trang Shopee that, cho JS render xong
roi lay og:image / og:title / og:description / gia.

Yeu cau:
  pip3 install playwright --break-system-packages
  python3 -m playwright install chromium

Cookie:
  Dat cookie tu trinh duyet Chrome (dang nhap Shopee) vao file:
  .git/shopee_cookie.txt  (1 dong, cu phap: name=value; name2=value2)

Cach dung:
  python3 sync_products.py

product_urls.txt - moi dong 1 san pham:
  <url>, <category>, [emoji], [tag], [price_override]
"""

import json, re, sys, time, unicodedata
from pathlib import Path
from html import unescape

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Thieu Playwright. Chay:")
    print("  pip3 install playwright --break-system-packages")
    print("  python3 -m playwright install chromium")
    sys.exit(1)

INPUT_FILE   = Path(__file__).parent / "product_urls.txt"
OUTPUT_FILE  = Path(__file__).parent / "products.json"
COOKIE_FILE  = Path(__file__).parent / ".git" / "shopee_cookie.txt"
PAGE_TIMEOUT = 30_000   # ms
JS_WAIT      = 3_500    # ms cho JS render


def parse_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split(",")]
    return {
        "url":            parts[0],
        "category":       parts[1] if len(parts) > 1 and parts[1] else "all",
        "emoji":          parts[2] if len(parts) > 2 and parts[2] else "🛍️",
        "tag":            parts[3] if len(parts) > 3 and parts[3] else "",
        "price_override": parts[4] if len(parts) > 4 and parts[4] else "",
    }


def clean_text(text, max_len=None):
    if not text:
        return ""
    text = unescape(str(text))
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_len and len(text) > max_len:
        text = text[:max_len - 1].rstrip() + "…"
    return text


def format_price_vnd(amount):
    try:
        amount = int(float(amount))
        return f"{amount:,.0f}".replace(",", ".") + "đ"
    except Exception:
        return str(amount)


def parse_cookies(raw):
    cookies = []
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".shopee.vn",
                "path": "/",
            })
    return cookies


def get_meta(page, prop):
    try:
        sel = f'meta[property="{prop}"]'
        el = page.query_selector(sel)
        return (el.get_attribute("content") or "").strip() if el else ""
    except Exception:
        return ""


def extract_price_from_page(page):
    """Tim gia tu JSON nhung trong trang hoac tu element."""
    try:
        # Thu lay tu window.__INITIAL_STATE__ hoac JSON-LD
        price_raw = page.evaluate("""() => {
            // Thu JSON-LD
            const ld = document.querySelector('script[type="application/ld+json"]');
            if (ld) {
                try {
                    const d = JSON.parse(ld.textContent);
                    const offers = d.offers || (d['@graph'] || []).find(x => x.offers)?.offers;
                    if (offers && offers.price) return offers.price;
                } catch(e) {}
            }
            // Thu element gia tren trang
            const priceEl = document.querySelector('.pmmxKx, [class*="price"] .text-shopee-red, .pdp-price');
            if (priceEl) return priceEl.textContent.trim();
            return '';
        }""")
        return clean_text(str(price_raw)) if price_raw else ""
    except Exception:
        return ""


def fetch_product(page, entry):
    url = entry["url"]
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        page.wait_for_timeout(JS_WAIT)
    except Exception as e:
        print(f"    ✗ Loi tai trang: {e}")
        return None

    final_url = page.url
    print(f"    -> {final_url[:80]}")

    title = clean_text(get_meta(page, "og:title"), max_len=90)
    thumb = get_meta(page, "og:image")
    desc  = clean_text(get_meta(page, "og:description"), max_len=80)

    if not title:
        print("    ✗ Khong lay duoc ten (co the bi captcha hoac trang loi)")
        return None

    # Gia
    price = ""
    if entry["price_override"]:
        try:
            price = format_price_vnd(int(entry["price_override"]))
        except ValueError:
            price = entry["price_override"]
    else:
        price = extract_price_from_page(page)

    print(f"    ✓ {title[:60]}{'...' if len(title) > 60 else ''}")
    print(f"    🖼  {'OK: ' + thumb[:55] if thumb else 'TRONG - khong co anh'}")
    if price:
        print(f"    💰 {price}")

    return {
        "title":    title,
        "sub":      desc,
        "url":      url,
        "thumb":    thumb,
        "price":    price,
        "emoji":    entry["emoji"],
        "tag":      entry["tag"],
        "category": entry["category"],
    }


def main():
    if not INPUT_FILE.exists():
        print(f"Khong tim thay {INPUT_FILE.name}.")
        sys.exit(1)

    items = []
    with open(INPUT_FILE, encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                items.append(parsed)

    if not items:
        print(f"{INPUT_FILE.name} rong.")
        sys.exit(1)

    # Doc cookie
    cookies = []
    if COOKIE_FILE.exists():
        raw = COOKIE_FILE.read_text(encoding="utf-8").strip()
        cookies = parse_cookies(raw)
        print(f"Cookie: da load {len(cookies)} cookie tu {COOKIE_FILE.name}")
    else:
        print("⚠ Khong tim thay cookie file - chay khong co auth")

    print(f"\nDang dong bo {len(items)} san pham voi Playwright...\n")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="vi-VN",
            viewport={"width": 1280, "height": 800},
        )
        if cookies:
            ctx.add_cookies(cookies)

        page = ctx.new_page()
        # Chay trang chu truoc de set cookies / session
        page.goto("https://shopee.vn", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1500)

        for i, item in enumerate(items, 1):
            print(f"[{i}/{len(items)}] {item['url']}")
            product = fetch_product(page, item)
            if product:
                results.append(product)
            # Delay nho tranh bot detection
            if i < len(items):
                time.sleep(1.2)

        browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nXong! {len(results)}/{len(items)} san pham -> {OUTPUT_FILE.name}")
    if len(results) < len(items):
        print("Mot so san pham bi bo qua — kiem tra log o tren.")


if __name__ == "__main__":
    main()
