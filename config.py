# ============================================================
#  ELEMENTS REPORTER — CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# PLATFORM SEÇİMİ:  "ios"  veya  "android"
# ------------------------------------------------------------
PLATFORM = "android"

BLACKLIST_IDS = [
    "statusBarBackground",
    "content",
    "action_bar_root",
    "navigationBarBackground"
]

# Çıktı formatı: "word"  |  "excel"  |  "word+excel"
OUTPUT_FORMAT = "word+excel"

# Çıktı olarak alınacak ID ler (Çıktı bu sıraya göre oluşacaktır, istenilmeyen alanlar silinebilir)
# Kullanılabilir değerler:
#   "missing"   → Accessibility ID'si olmayan elementler
#   "undefined" → ID var ama içinde "undefined" geçen (undefinedName, undefined_name vb.)
#   "duplicate" → Aynı ID'yi paylaşan elementler
#   "unique"    → Geçerli ve tekil ID'ye sahip elementler

DOCUMENT_SECTIONS = ["missing", "undefined", "duplicate", "unique"]

# Çıktı klasörü
OUTPUT_DIR = "/Users/yunus.sahin/PycharmProjects/PythonProject/PIA_Elements"

# Appium server adresi
APPIUM_SERVER = "http://127.0.0.1:4723"


# ------------------------------------------------------------
# iOS AYARLARI  (PLATFORM = "ios" ise geçerli)
# ------------------------------------------------------------
IOS = {
    "device_name":      "iPhone 16",
    "platform_version": "18.6",
    "bundle_id":        "test.com.hitit.pia",
    "udid":             "AD21A917-5271-4DF1-8C5D-E64A0DE8EAD9",
    "no_reset":         True,
}

# KZR IOS package ve activity

# "bundle_id":        "test.kz.flyarystan",

# PIA IOS package ve activity

# "bundle_id":        "test.com.hitit.pia",

# ------------------------------------------------------------
# ANDROID AYARLARI  (PLATFORM = "android" ise geçerli)
# ------------------------------------------------------------
ANDROID = {
    "device_name":      "ce04171418dee0010c",
    "platform_version": "9",
    "app_package":      "test.com.piac.thepiaapp.android",
    "app_activity":     "com.piamobile.MainActivity",
    "no_reset":         True,
}

# KZR Android package ve activity

# app_package":      "test.kz.flyarystan",
# "app_activity":     "kz.flyarystan.MainActivity",

# PIA Android package ve activity

# app_package":      "test.com.piac.thepiaapp.android",
# "app_activity":     "com.piamobile.MainActivity",