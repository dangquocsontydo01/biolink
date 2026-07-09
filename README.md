# Bio Link Hub — Hướng dẫn triển khai & chiến lược

## 1. Cấu trúc file

Toàn bộ là **1 file HTML** duy nhất (`biolink.html`). Không cần build, không cần npm. Mở bằng trình duyệt là chạy.

Tất cả nội dung chỉnh trong **object `CONFIG`** ở cuối file. Không cần đụng đến HTML/CSS.

---

## 2. Tuỳ chỉnh nội dung

Mở `biolink.html`, kéo xuống dòng có `const CONFIG = {`. Chỉnh các phần:

| Field | Ý nghĩa |
|---|---|
| `profile` | Tên, handle, bio, avatar (URL ảnh hoặc để rỗng dùng chữ cái) |
| `socials` | Link các tài khoản MXH của bạn (TikTok, IG, FB, YouTube...) |
| `stats` | 3 chip "social proof" hiển thị dưới avatar |
| `categories` | Các tab filter. `id` dùng để match với link, `label` là chữ hiển thị |
| `featured` | 1–3 deal nổi bật (có ảnh, giá, % giảm) |
| `links` | Danh sách deal chính (không giới hạn số lượng) |

Mỗi link có field `category` phải khớp với một `id` trong `categories`.

---

## 3. Deploy — 4 lựa chọn

### Lựa chọn A — Deploy lên VPS hiện có (167.179.89.119)

Vì bạn đã có Caddy chạy sẵn, thêm 1 site mới:

```bash
# Trên VPS
mkdir -p /var/www/biolink
# Copy file lên
# (chạy từ Mac:)
scp biolink.html user@167.179.89.119:/var/www/biolink/index.html
```

Trong Caddyfile thêm:

```caddy
biolink.yourdomain.com {
    root * /var/www/biolink
    file_server
    encode gzip
    header Cache-Control "public, max-age=3600"
}
```

Reload: `caddy reload --config /etc/caddy/Caddyfile`

Caddy tự lo SSL via Let's Encrypt.

### Lựa chọn B — GitHub Pages (free, ổn nhất cho beginner)

1. Tạo repo `biolink` (public)
2. Push `biolink.html` rename thành `index.html`
3. Settings → Pages → Source: `main` branch
4. URL: `https://yourname.github.io/biolink`

### Lựa chọn C — Cloudflare Pages (free, fast CDN)

1. Đẩy code lên GitHub
2. Cloudflare Dashboard → Pages → Connect repo
3. Build command: để trống. Output dir: `/`
4. Domain tuỳ chỉnh free

### Lựa chọn D — Netlify (drag-drop)

1. Vào netlify.com → kéo thả file `biolink.html` (đổi tên thành `index.html`)
2. Done. Có URL trong 5 giây.

---

## 4. Chiến lược tracking đa nền tảng

**Mục tiêu**: Biết platform nào (TikTok / IG / FB / YouTube) đem về nhiều click & conversion nhất → đầu tư đúng kênh.

### Cách dùng URL khác nhau cho từng MXH

Thay vì đặt cùng `biolink.yourdomain.com` ở mọi bio, gắn thêm `?ref=...`:

| Bio ở | URL gắn |
|---|---|
| TikTok | `biolink.yourdomain.com?ref=tiktok` |
| Instagram | `biolink.yourdomain.com?ref=ig` |
| Facebook | `biolink.yourdomain.com?ref=fb` |
| YouTube | `biolink.yourdomain.com?ref=youtube` |
| Threads | `biolink.yourdomain.com?ref=threads` |

Trang sẽ tự đọc `?ref=` rồi gắn vào UTM của link Shopee outbound:
`https://shopee.vn/...?utm_source=tiktok&utm_medium=link`

→ Vào Shopee Affiliate dashboard sẽ thấy source riêng từng MXH.

### Xem stats nhanh

Mở trang biolink trong browser → bấm F12 → Console tab → gõ:
```js
showStats()
```

Sẽ in bảng số click từng link (lưu trong localStorage trên máy bạn).

### Tracking server-side (option nâng cao)

Sẵn có VPS rồi, bạn có thể setup endpoint nhận tracking:

```python
# Trong Flask API hiện có của bạn
@app.route('/api/biolink/track', methods=['POST'])
def track():
    data = request.get_json()
    # insert vào bảng biolink_clicks
    db.execute(
        "INSERT INTO biolink_clicks (type, name, url, ref, ua, ts) VALUES (%s,%s,%s,%s,%s,%s)",
        (data['type'], data['name'], data['url'], data.get('ref'), data['ua'], data['ts'])
    )
    return '', 204
```

Trong `CONFIG.tracking.endpoint` đặt `"https://api.yourdomain.com/api/biolink/track"`.

Có data → dashboard sau này.

---

## 5. Chiến lược marketing — từ góc độ Giám đốc Marketing

### a. Sản phẩm nên đưa lên trang này

**KHÔNG**: đưa tất cả link Shopee bạn có. Bio link mà có 50 link sẽ giảm conversion (paradox of choice).

**NÊN**:
- **3 featured deal** (đổi mỗi 3–7 ngày): những món đang hot trend, % giảm cao, hoặc đang flash sale
- **8–12 link thường**: chia đều 5–6 category
- **Đặt deal cao hoa hồng + bán chạy lên đầu** (ưu tiên hơn deal bạn thích nhưng ít người mua)

### b. Lựa chọn deal — Khung 3 yếu tố

Mỗi sản phẩm phải đạt **ít nhất 2/3** tiêu chí mới đưa lên:
1. **Hoa hồng cao** (≥5% với Shopee VN)
2. **Đã bán nhiều** (đánh giá ≥4.7, sold ≥1K) → giảm rủi ro người mua thất vọng
3. **Liên quan đến nội dung MXH** của bạn

### c. Mẫu CTA hiệu quả trên bio MXH

Kém: "Link in bio"
Khá: "🛒 Link Shopee trong bio"
Tốt: "👇 3 deal hot nhất tuần này (link bio)"
Rất tốt: "Mã giảm 50% cho 5 món bị bỏ lỡ → link bio"

→ Trang biolink phải có đúng deal tương ứng với content video/post.

### d. A/B testing

Mỗi 2 tuần đổi 1 thứ và đo:
- Thứ tự link (sản phẩm đắt vs rẻ lên đầu)
- Số lượng category
- Có/không stats chip ở header
- Featured 1 món vs 3 món

### e. Compliance — quan trọng

- **Disclosure ở footer đã có sẵn**: "Tiết lộ liên kết..." → bắt buộc theo chính sách Shopee Affiliate VN
- `rel="nofollow sponsored"` đã được thêm tự động vào mọi link affiliate
- KHÔNG được làm giả review hoặc tự nhận đã dùng nếu chưa dùng — Shopee có thể ban

### f. Tối ưu mobile (>85% traffic)

Trang đã tối ưu:
- Tap target ≥48px
- Font tiếng Việt dùng Be Vietnam Pro (dấu hiển thị đẹp)
- Dark mode tự động theo system
- Animation tôn trọng `prefers-reduced-motion`

---

## 6. Roadmap tiếp theo (nếu muốn nâng cấp)

- **Admin panel**: form đăng nhập + sửa link mà không cần edit code (cần Flask backend của bạn)
- **Auto-import từ Shopee Affiliate API**: pull link affiliate mới nhất + auto-update
- **Tích hợp giỏ hàng nhỏ**: cho phép gom nhiều món rồi check out → tăng AOV
- **AB test 2 phiên bản layout** ngẫu nhiên (50/50) → đo conversion
- **OG image động**: generate ảnh preview riêng cho từng deal khi share

---

## 7. Quick start checklist

- [ ] Mở `biolink.html`, sửa `CONFIG.profile`
- [ ] Update `socials` với link MXH thật của bạn
- [ ] Lấy 3 affiliate link Shopee đang chạy nhất → cho vào `featured`
- [ ] Thêm 8–12 link vào `links` với category đúng
- [ ] Test mở file trên điện thoại (kéo file vào iCloud/Drive rồi mở)
- [ ] Deploy lên VPS hoặc GitHub Pages
- [ ] Gắn `?ref=tiktok` `?ref=ig` `?ref=fb` vào bio các MXH khác nhau
- [ ] Sau 1 tuần: gõ `showStats()` trong console xem link nào hot nhất → ưu tiên deal đó
