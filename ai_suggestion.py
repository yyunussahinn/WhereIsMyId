"""
ai_suggestion.py
────────────────
Element taramasında AI Suggestion sütunu için Claude API'yi kullanır.

KURULUM:
  1. console.anthropic.com → API Keys → Create Key
  2. Aşağıdaki API_KEY satırına yapıştır.

İki görev:
  1. generate_json_suggestion(element, platform)
     → ID'si olan elementler için JSON yapısını üretir.
     → "key": acc_id'yi snake_case→camelCase dönüştürüp tip suffix'i ekler.
       Tamamen lokal, API çağrısı YOK.
       Örnek: acc_id="loyalty_login_text_field_emailOrMembership", type="EditText"
              → key="loyaltyLoginTextFieldEmailOrMembershipTextbox"

  2. generate_id_suggestion(element, existing_ids)
     → ID'si olmayan / duplicate / undefined elementler için
       mevcut ID'lere bakarak uyumlu bir ID önerir (API kullanır).
"""

import json
import re
import ssl
import urllib.request
import urllib.error

# ══════════════════════════════════════════════════════
# ▼▼▼  API KEY BURAYA  ▼▼▼
API_KEY = "sk-ant-api03-BURAYA_YAPISTIR"
# ▲▲▲  API KEY BURAYA  ▲▲▲
# ══════════════════════════════════════════════════════

API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-sonnet-4-20250514"

HEADERS = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
    "x-api-key": API_KEY,
}

# SSL sertifika doğrulamasını devre dışı bırak (macOS sertifika sorunu için)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE


# ── Element tipi → anlamlı suffix eşlemesi ────────────────────────────────
# iOS (XCUIElementType kısmı zaten kırpılmış gelir: "Button", "TextField" vb.)
# Android (son kısım gelir: "EditText", "Button", "CheckBox" vb.)
_TYPE_SUFFIX = {
    # Android
    "edittext":       ("textbox",           "Textbox"),
    "button":         ("btn",               "Btn"),
    "imagebutton":    ("btn",               "Btn"),
    "checkbox":       ("checkbox",          "Checkbox"),
    "radiobutton":    ("radio_btn",         "RadioBtn"),
    "switch":         ("toggle",            "Toggle"),
    "spinner":        ("dropdown",          "Dropdown"),
    "textview":       ("label",             "Label"),
    "imageview":      ("icon",              "Icon"),
    "framelayout":    ("container",         "Container"),
    "linearlayout":   ("container",         "Container"),
    "relativelayout": ("container",         "Container"),
    "viewgroup":      ("container",         "Container"),
    "view":           ("container",         "Container"),
    # iOS
    "textfield":      ("textbox",           "Textbox"),
    "securetextfield":("password_textbox",  "PasswordTextbox"),
    "cell":           ("cell",              "Cell"),
    "other":          ("view",              "View"),
}

def _type_hints(elem_type: str) -> tuple[str, str]:
    """
    Element tipinden (snake_case suffix, CamelCase suffix) döner.
    Örn: "EditText"  → ("textbox", "Textbox")
         "CheckBox"  → ("checkbox", "Checkbox")
         "ViewGroup" → ("container", "Container")
    """
    key = elem_type.lower().replace(".", "").replace("_", "")
    return _TYPE_SUFFIX.get(key, ("element", "Element"))


def _call_api(system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    """Claude API'yi çağırır, text yanıtını döner. Hata olursa boş string."""
    body = json.dumps({
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block["text"].strip()
    except Exception as e:
        print(f"   [AI] API hatası: {e}")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. ID'si olan elementler için JSON suggestion
# ─────────────────────────────────────────────────────────────────────────────

def _acc_id_to_camel(acc_id: str) -> str:
    """
    resource-id / accessibility-id değerini camelCase'e dönüştürür.
    Ayraçlar: _ - . / boşluk  (hepsini word sınırı sayar)
    Büyük/küçük harf korumalı: zaten camelCase/PascalCase parçalar bozulmaz.

    Örnek:
      "loyalty_login_text_field_emailOrMembership" → "loyaltyLoginTextFieldEmailOrMembership"
      "avail_search_dep_port_card"                 → "availSearchDepPortCard"
      "rememberMe"                                 → "rememberMe"  (değişmez)
    """
    # Önce ayraçlarla böl
    raw_parts = re.split(r"[_\-\.\s/]+", acc_id)
    result = []
    for i, part in enumerate(raw_parts):
        if not part:
            continue
        if i == 0:
            # İlk kelime: ilk harf küçük, geri kalanı koru
            result.append(part[0].lower() + part[1:])
        else:
            # Sonraki kelimeler: ilk harf büyük, geri kalanı koru
            result.append(part[0].upper() + part[1:])
    return "".join(result) or "element"


def _build_key(acc_id: str, elem_type: str) -> str:
    """
    acc_id'den camelCase üretir, sonuna tip suffix'i ekler.
    Suffix zaten varsa tekrar eklemez.

    Örnek:
      acc_id="loyalty_login_text_field_emailOrMembership", type="EditText"
      → "loyaltyLoginTextFieldEmailOrMembershipTextbox"

      acc_id="login_btn", type="Button"
      → "loginBtn"   (suffix zaten var, tekrar eklenmez)
    """
    _, camel_sfx = _type_hints(elem_type)
    base = _acc_id_to_camel(acc_id)

    # Suffix kontrolü (case-insensitive)
    if base.lower().endswith(camel_sfx.lower()):
        return base
    return base + camel_sfx


def generate_json_suggestion(element: dict, platform: str) -> str:
    """
    ID'si olan element için JSON suggestion üretir.
    "key": acc_id → camelCase + tip suffix  (tamamen lokal, API yok)
    element: {"type", "label", "value", "acc_id"}
    platform: "ios" | "android"
    """
    acc_id = element.get("acc_id", "")
    etype  = element.get("type", "")

    key = _build_key(acc_id, etype)

    return json.dumps({
        "key":           key,
        "androidValue":  acc_id,
        "androidType":   "id",
        "iosValue":      acc_id,
        "iosType":       "accessibilityId",
    }, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# 2. ID'si olmayan / duplicate / undefined elementler için ID önerisi
# ─────────────────────────────────────────────────────────────────────────────

_SYS_ID = """You are a mobile accessibility ID naming expert.
Given a UI element without a proper accessibility ID and a list of existing IDs in the same app,
suggest a single snake_case accessibility ID.

Rules:
- MUST reflect BOTH the element's semantic purpose (label/text) AND its UI type.
- Type suffix rules (MANDATORY — always append at the end):
    EditText / TextField           → _textbox          e.g. login_email_textbox
    SecureTextField                → _password_textbox  e.g. login_password_textbox
    Button / ImageButton           → _btn               e.g. login_btn, submit_payment_btn
    CheckBox                       → _checkbox          e.g. remember_me_checkbox
    RadioButton                    → _radio_btn         e.g. gender_male_radio_btn
    Switch                         → _toggle            e.g. notifications_toggle
    Spinner / Dropdown             → _dropdown          e.g. country_dropdown
    Cell                           → _cell              e.g. home_menu_cell
    TextView / Label               → _label             e.g. welcome_label
    ImageView / Icon               → _icon              e.g. profile_photo_icon
    ViewGroup / View / Container   → _container         e.g. header_container

- Analyse existing IDs to find the naming prefix pattern used in this screen and follow it.
  If existing IDs start with "loyalty_login_", your suggestion should also start with "loyalty_login_".
- BAD:  "remember_me", "enter", "home"  (missing type suffix)
- GOOD: "profile_remember_me_checkbox", "loyalty_login_btn", "search_dep_port_textbox"

Return ONLY the suggested ID string, nothing else. No explanation, no quotes."""


def generate_id_suggestion(element: dict, existing_ids: list[str]) -> str:
    """
    ID'si olmayan/duplicate/undefined element için ID önerisi üretir.
    existing_ids: mevcut unique ID listesi (naming pattern context için)
    """
    label  = element.get("label", "")
    value  = element.get("value", "")
    etype  = element.get("type", "")
    acc_id = element.get("acc_id", "")
    page   = element.get("page", "")

    snake_sfx, _ = _type_hints(etype)
    sample_ids   = existing_ids[:30]

    user_prompt = (
        f"Screen/Page context: {page}\n"
        f"Element type: {etype}  →  ID MUST end with '_{snake_sfx}'\n"
        f"Label/Text: {label}\n"
        f"Value: {value}\n"
        f"Current ID (if any): {acc_id}\n\n"
        f"Existing IDs in the app (analyse for naming pattern):\n"
        + "\n".join(f"  - {i}" for i in sample_ids)
    )

    raw = _call_api(_SYS_ID, user_prompt, max_tokens=60)
    if raw:
        suggestion = raw.splitlines()[0].strip().strip('"').strip("'")
        suggestion = re.sub(r"\s+", "_", suggestion).lower()
        return suggestion

    # Fallback
    base = _to_snake(label or value or etype or "element")
    return f"{base}_{snake_sfx}"


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı dönüşüm fonksiyonları
# ─────────────────────────────────────────────────────────────────────────────

def _to_camel(text: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().split()
    if not words:
        return "element"
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def _to_snake(text: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().split()
    return "_".join(w.lower() for w in words) or "element"


# ─────────────────────────────────────────────────────────────────────────────
# Toplu işlem: tüm element listesi için suggestion üret
# ─────────────────────────────────────────────────────────────────────────────

STATUS_UNIQUE    = "ID Var"
STATUS_DUPLICATE = "Duplicate"
STATUS_MISSING   = "ID Yok"
STATUS_UNDEFINED = "Undefined ID"


def enrich_elements(elements: list[dict], platform: str) -> list[dict]:
    """
    elements listesini işleyerek her elemente 'ai_suggestion' alanı ekler.
    - STATUS_UNIQUE → JSON suggestion (key + android/ios değerleri)
    - Diğerleri     → ID suggestion string
    Orijinal listeyi modify eder ve döner.
    """
    existing_ids = [
        e["acc_id"] for e in elements
        if e.get("status") == STATUS_UNIQUE and e.get("acc_id")
    ]

    total = len(elements)
    print(f"\n🤖 AI Suggestion üretiliyor ({total} element)...")

    for idx, elem in enumerate(elements, 1):
        status = elem.get("status", STATUS_MISSING)
        label  = elem.get("label") or elem.get("value") or elem.get("acc_id") or "?"
        etype  = elem.get("type", "")
        print(f"   [{idx:3d}/{total}] {status:12s} | {etype:15s} | {label[:35]}", end="", flush=True)

        try:
            if status == STATUS_UNIQUE:
                suggestion = generate_json_suggestion(elem, platform)
            else:
                suggestion = generate_id_suggestion(elem, existing_ids)
        except Exception as ex:
            suggestion = f"(hata: {ex})"

        elem["ai_suggestion"] = suggestion
        print(" ✓")

    print("✅ AI Suggestion tamamlandı.\n")
    return elements