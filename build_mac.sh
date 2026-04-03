#!/usr/bin/env bash
# ============================================================
#  Where Is My Id — macOS .app paketi
#  Kullanım: chmod +x build_mac.sh && ./build_mac.sh
# ============================================================
set -e

echo "📦 Gerekli paketler kontrol ediliyor..."
pip install customtkinter pillow pyinstaller --quiet

echo "🔨 PyInstaller çalıştırılıyor..."
pyinstaller \
  --name "Where Is My Id" \
  --windowed \
  --onefile \
  --clean \
  --add-data "config.py:." \
  --add-data "element_checker_ios.py:." \
  --add-data "element_checker_android.py:." \
  --add-data "build_summary.py:." \
  --hidden-import customtkinter \
  --hidden-import PIL \
  --hidden-import openpyxl \
  --hidden-import docx \
  --hidden-import appium \
  app.py

echo ""
echo "✅ Derleme tamamlandı!"
echo "   → dist/Where Is My Id.app"
echo ""
echo "💡 İlk çalıştırmada macOS Gatekeeper uyarısı çıkabilir."
echo "   System Preferences > Security & Privacy > Open Anyway"
