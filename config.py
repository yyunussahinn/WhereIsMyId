# WHERE IS MY ID — config.py  (28.04.2026 14:10)
PLATFORM = "ios"
BLACKLIST_IDS = ["text-input-flat-label-inactive", "text-input-underline", "right-icon-adornment-container", "right-icon-adornment", "text-input-flat", "statusBarBackground", "content", "action_bar_root", "navigationBarBackground", "exo_content_frame"]
OUTPUT_FORMAT = "word+excel+json"
DOCUMENT_SECTIONS = ["unique", "undefined", "duplicate", "missing"]
OUTPUT_DIR = "/Users/yunus.sahin/Library/CloudStorage/OneDrive-TESTINIUMTeknolojiYazılımA.Ş/Test"
APPIUM_SERVER = "http://127.0.0.1:4723"
IOS = {
    "device_name":      "iPhone 16",
    "platform_version": "18.6",
    "bundle_id":        "test.com.hitit.pia",
    "udid":             "AD21A917-5271-4DF1-8C5D-E64A0DE8EAD9",
    "no_reset":         True,
}
ANDROID = {}
