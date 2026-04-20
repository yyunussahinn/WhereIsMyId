"""
claude_filter.py
────────────────────────────────────────────────────────────────
Annotation kutularını Appium element listesiyle eşleştirir.

Adımlar:
  1. Her kutunun içinde kalan elementleri koordinat bazlı bul
  2. Eşleşmeyen kutular varsa Claude Vision API ile doğrula
  3. Filtrelenmiş element listesini döndür

Kullanım:
    from claude_filter import filter_elements_by_boxes

    filtered = filter_elements_by_boxes(
        all_elements,   # element_checker'dan gelen liste
        boxes,          # annotator'dan gelen kutu listesi
        screenshot_path # Appium'un aldığı ekran görüntüsü
    )
"""

import base64
import json
import os
import urllib.request
import urllib.error


# ── Anthropic API ────────────────────────────────────────────────────────────
API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-opus-4-5"


def _read_api_key() -> str:
    """
    API key öncelik sırası:
      1. ANTHROPIC_API_KEY environment variable
      2. Proje klasöründeki .anthropic_key dosyası
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".anthropic_key")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            key = f.read().strip()
        if key:
            return key

    raise RuntimeError(
        "Anthropic API key bulunamadı.\n"
        "Seçenek 1: export ANTHROPIC_API_KEY='sk-ant-...'\n"
        "Seçenek 2: Proje klasörüne '.anthropic_key' dosyası oluştur ve key'i yaz."
    )


def _call_claude(messages: list, max_tokens: int = 1024) -> str:
    """Claude API'ye istek gönder, metin yanıtı döndür."""
    api_key = _read_api_key()

    payload = json.dumps({
        "model":      MODEL,
        "max_tokens": max_tokens,
        "messages":   messages,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Claude API hatası {e.code}: {body}") from e


def _img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── Koordinat eşleştirme ─────────────────────────────────────────────────────

def _elem_center(elem: dict) -> tuple[float, float] | None:
    """Element rect'inden merkez noktası hesapla."""
    rect = elem.get("rect")
    if not rect:
        return None
    try:
        cx = rect["x"] + rect["width"]  / 2
        cy = rect["y"] + rect["height"] / 2
        return cx, cy
    except (KeyError, TypeError):
        return None


def _point_in_box(cx: float, cy: float, box: dict) -> bool:
    return box["x1"] <= cx <= box["x2"] and box["y1"] <= cy <= box["y2"]


def _match_by_coordinates(elements: list, boxes: list) -> tuple[list, list]:
    """
    Koordinat bazlı eşleştirme.
    Dönüş: (matched_elements, unmatched_boxes)
      matched_elements → rect bilgisi olan ve kutu içinde kalan elementler
      unmatched_boxes  → hiç element düşmeyen kutular (Vision fallback için)
    """
    matched   = []
    box_hits  = [False] * len(boxes)

    for elem in elements:
        center = _elem_center(elem)
        if center is None:
            continue
        cx, cy = center
        for i, box in enumerate(boxes):
            if _point_in_box(cx, cy, box):
                matched.append(elem)
                box_hits[i] = True
                break   # bir element birden fazla kutuya girmesin

    unmatched_boxes = [box for i, box in enumerate(boxes) if not box_hits[i]]
    return matched, unmatched_boxes


# ── Claude Vision fallback ───────────────────────────────────────────────────

def _vision_match(elements: list, unmatched_boxes: list,
                  screenshot_path: str) -> list:
    """
    Koordinat eşleşmesi bulamadığı kutular için Claude Vision kullanır.
    Modele: screenshot + eşleşmeyen kutu koordinatları + tüm element listesi
    Model: hangi elementlerin o kutulara karşılık geldiğini JSON ile döner.
    """
    if not unmatched_boxes:
        return []

    print(f"   🔍 {len(unmatched_boxes)} kutu için Claude Vision devreye giriyor...")

    # Element listesini sadeleştir (API token tasarrufu)
    elem_summary = []
    for i, e in enumerate(elements):
        elem_summary.append({
            "index": i,
            "type":  e.get("type", ""),
            "label": e.get("label", ""),
            "value": e.get("value", ""),
            "acc_id": e.get("acc_id", ""),
        })

    img_b64 = _img_to_base64(screenshot_path)

    system_prompt = (
        "Sen bir mobile test asistanısın. "
        "Ekran görüntüsü ve koordinatlar veriliyor. "
        "Sadece JSON döndür, başka hiçbir şey yazma. "
        "Format: {\"matched_indices\": [0, 3, 7]}"
    )

    user_content = [
        {
            "type": "image",
            "source": {
                "type":       "base64",
                "media_type": "image/png",
                "data":       img_b64,
            },
        },
        {
            "type": "text",
            "text": (
                f"Ekran görüntüsünde şu koordinatlarda işaretlenmiş kutular var:\n"
                f"{json.dumps(unmatched_boxes, indent=2)}\n\n"
                f"Mevcut element listesi:\n"
                f"{json.dumps(elem_summary, indent=2, ensure_ascii=False)}\n\n"
                f"Bu kutularla eşleşen elementlerin 'index' numaralarını döndür.\n"
                f"Sadece JSON: {{\"matched_indices\": [...]}} "
            ),
        },
    ]

    try:
        raw = _call_claude([
            {"role": "user", "content": user_content}
        ], max_tokens=512)

        # JSON parse
        raw_clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data      = json.loads(raw_clean)
        indices   = data.get("matched_indices", [])

        vision_matched = [elements[i] for i in indices if 0 <= i < len(elements)]
        print(f"   ✅ Vision eşleştirdi: {len(vision_matched)} element")
        return vision_matched

    except Exception as ex:
        print(f"   ⚠️  Vision eşleştirme başarısız: {ex}")
        return []


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────

def filter_elements_by_boxes(
    all_elements:    list,
    boxes:           list,
    screenshot_path: str,
    use_vision:      bool = True,
) -> list:
    """
    Annotation kutularıyla eşleşen elementleri döndürür.

    Parametreler:
        all_elements    : element_checker'dan gelen tüm element listesi
                          Her element dict'inde opsiyonel "rect" anahtarı olmalı:
                          {"x": int, "y": int, "width": int, "height": int}
        boxes           : annotator.open_annotator() çıktısı
                          [{"x1":int,"y1":int,"x2":int,"y2":int}, ...]
        screenshot_path : Appium'un aldığı ekran görüntüsü yolu
        use_vision      : False → sadece koordinat eşleştirme (API gerekmez)

    Dönüş:
        Eşleşen elementlerin listesi (orijinal dict yapısı korunur)
    """

    if not boxes:
        print("   ⚠️  Kutu listesi boş — tüm elementler döndürülüyor.")
        return all_elements

    print(f"   📦 {len(all_elements)} element  ×  {len(boxes)} kutu eşleştiriliyor...")

    # Rect bilgisi olan ve olmayan elementleri ayır
    with_rect    = [e for e in all_elements if e.get("rect")]
    without_rect = [e for e in all_elements if not e.get("rect")]

    if without_rect:
        print(f"   ℹ️  {len(without_rect)} elementin rect bilgisi yok "
              f"— koordinat eşleştirmesi atlanıyor.")

    # Adım 1: koordinat bazlı eşleştirme
    coord_matched, unmatched_boxes = _match_by_coordinates(with_rect, boxes)
    print(f"   ✅ Koordinat eşleştirme: {len(coord_matched)} element bulundu.")

    # Adım 2: Vision fallback
    vision_matched = []
    if use_vision and unmatched_boxes and os.path.exists(screenshot_path):
        # Vision fallback için tüm listeyi ver (rect olmayanlar da dahil)
        vision_matched = _vision_match(all_elements, unmatched_boxes, screenshot_path)

    # Birleştir, duplicate'leri temizle
    seen = set()
    final = []
    for e in coord_matched + vision_matched:
        key = (e.get("acc_id", ""), e.get("label", ""), e.get("type", ""))
        if key not in seen:
            seen.add(key)
            final.append(e)

    print(f"   🎯 Toplam eşleşen: {len(final)} element")
    return final if final else all_elements   # hiç eşleşme yoksa tümünü döndür


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Test: sahte element listesi + kutular ile koordinat eşleştirmesini dene.
    Vision API testi için gerçek screenshot ve ANTHROPIC_API_KEY gerekir.
    """

    fake_elements = [
        {"type": "Button",    "label": "Login",           "acc_id": "btn_login",
         "value": "", "status": "ID Var",
         "rect": {"x": 40, "y": 260, "width": 320, "height": 50}},
        {"type": "TextField", "label": "Email",           "acc_id": "input_email",
         "value": "", "status": "ID Var",
         "rect": {"x": 40, "y": 80,  "width": 320, "height": 40}},
        {"type": "TextField", "label": "Password",        "acc_id": "",
         "value": "", "status": "ID Yok",
         "rect": {"x": 40, "y": 140, "width": 320, "height": 40}},
        {"type": "Button",    "label": "Forgot Password", "acc_id": "",
         "value": "", "status": "ID Yok",
         "rect": {"x": 80, "y": 330, "width": 200, "height": 30}},
        {"type": "Button",    "label": "Google ile Giriş","acc_id": "btn_google",
         "value": "", "status": "ID Var",
         "rect": {"x": 40, "y": 390, "width": 320, "height": 40}},
    ]

    # Annotation kutularını simüle et (email + login button)
    test_boxes = [
        {"x1": 30,  "y1": 70,  "x2": 380, "y2": 130},   # email input
        {"x1": 30,  "y1": 250, "x2": 380, "y2": 320},   # login button
        {"x1": 500, "y1": 500, "x2": 600, "y2": 550},   # hiç element yok → unmatched
    ]

    print("─" * 50)
    print("Koordinat eşleştirme testi (Vision kapalı)")
    print("─" * 50)

    result = filter_elements_by_boxes(
        fake_elements,
        test_boxes,
        screenshot_path="/tmp/nonexistent.png",
        use_vision=False,
    )

    print(f"\nSonuç ({len(result)} element):")
    for e in result:
        print(f"  [{e['status']:12s}] {e['type']:12s} | {e['label']}")