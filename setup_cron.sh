#!/bin/bash
# ============================================================
# setup_cron.sh — Tự động sync sản phẩm Shopee mỗi ngày
# Chạy 1 lần để cài đặt cron job:  bash setup_cron.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/sync.log"
CRON_JOB="0 6 * * * cd \"$SCRIPT_DIR\" && python3 sync_products.py >> \"$LOG_FILE\" 2>&1 && git add products.json && git commit -m \"auto: daily sync \$(date +%Y-%m-%d)\" && git push origin main >> \"$LOG_FILE\" 2>&1"

echo "📦 Script dir: $SCRIPT_DIR"
echo "📋 Log file:   $LOG_FILE"
echo ""

# Kiểm tra python3
if ! command -v python3 &>/dev/null; then
  echo "❌ Không tìm thấy python3. Hãy cài đặt trước."
  exit 1
fi

# Kiểm tra playwright
if ! python3 -c "import playwright" &>/dev/null; then
  echo "⚠️  Playwright chưa cài. Đang cài..."
  pip3 install playwright --break-system-packages
  python3 -m playwright install chromium
fi

# Thêm cron job (tránh trùng)
EXISTING=$(crontab -l 2>/dev/null | grep "sync_products.py")
if [ -n "$EXISTING" ]; then
  echo "ℹ️  Cron job đã tồn tại:"
  echo "   $EXISTING"
  echo ""
  read -p "Ghi đè không? (y/n): " confirm
  if [ "$confirm" != "y" ]; then
    echo "Huỷ."
    exit 0
  fi
  # Xoá cron cũ
  crontab -l 2>/dev/null | grep -v "sync_products.py" | crontab -
fi

# Thêm cron mới
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Đã cài cron job!"
echo ""
echo "📅 Lịch chạy: Mỗi ngày lúc 06:00 sáng"
echo "📄 Log tại:   $LOG_FILE"
echo ""
echo "Kiểm tra bằng lệnh:"
echo "  crontab -l"
echo ""
echo "Chạy thử ngay (không cần đợi 6h):"
echo "  cd \"$SCRIPT_DIR\" && python3 sync_products.py"
