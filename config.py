# WHERE IS MY ID — config.py  (03.04.2026 10:48)
PLATFORM = "android"
BLACKLIST_IDS = ["statusBarBackground", "content", "action_bar_root", "navigationBarBackground", "exo_content_frame"]
OUTPUT_FORMAT = "word+excel"
DOCUMENT_SECTIONS = ["unique", "undefined", "duplicate", "missing"]
OUTPUT_DIR = "/Users/yunus.sahin/Desktop/elemet reporter app çıktı"
APPIUM_SERVER = "http://127.0.0.1:4723"
ANDROID = {
    "device_name":      "ce04171418dee0010c",
    "platform_version": "9",
    "app_package":      "test.com.piac.thepiaapp.android",
    "app_activity":     "com.piamobile.MainActivity",
    "no_reset":         True,
}
IOS = {}
