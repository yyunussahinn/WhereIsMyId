# WHERE IS MY ID — config.py  (20.04.2026 16:10)
PLATFORM = "android"
BLACKLIST_IDS = ["text-input-flat-label-inactive", "text-input-underline", "right-icon-adornment-container", "right-icon-adornment", "text-input-flat", "statusBarBackground", "content", "action_bar_root", "navigationBarBackground", "exo_content_frame"]
OUTPUT_FORMAT = "word+excel"
DOCUMENT_SECTIONS = ["unique", "undefined", "duplicate", "missing"]
OUTPUT_DIR = "/Users/yunus.sahin/Library/CloudStorage/OneDrive-TESTINIUMTeknolojiYazılımA.Ş/whereismyid_reports"
APPIUM_SERVER = "http://127.0.0.1:4723"
ANDROID = {
    "device_name":      "ce04171418dee0010c",
    "platform_version": "9",
    "app_package":      "test.com.piac.thepiaapp.android",
    "app_activity":     "com.piamobile.MainActivity",
    "no_reset":         True,
}
IOS = {}
