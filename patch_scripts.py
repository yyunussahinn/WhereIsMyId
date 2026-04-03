#!/usr/bin/env python3
"""
patch_scripts.py
────────────────
element_checker_ios.py ve element_checker_android.py dosyalarındaki
input() çağrılarından önce sys.stdout.flush() ekler.

GUI ile subprocess haberleşmesinde input() promptu newline içermez;
flush olmadan GUI satırı hiç alamaz → deadlock.

Kullanım:  python patch_scripts.py
Not: Zaten patch edilmiş dosyalara tekrar dokunmaz.
"""

import os
import re

SCRIPTS = [
    "element_checker_ios.py",
    "element_checker_android.py",
]

FLUSH_LINE = "sys.stdout.flush()  # GUI subprocess flush\n"

base_dir = os.path.dirname(os.path.abspath(__file__))

for fname in SCRIPTS:
    fpath = os.path.join(base_dir, fname)
    if not os.path.exists(fpath):
        print(f"⚠  Bulunamadı, atlandı: {fname}")
        continue

    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # import sys var mı?
    has_import_sys = any(re.match(r"^\s*import sys\b", l) for l in lines)

    new_lines = []
    changed   = 0

    for i, line in enumerate(lines):
        # input() çağrısını içeren satır
        if re.search(r'\binput\s*\(', line):
            indent = len(line) - len(line.lstrip())
            flush  = " " * indent + FLUSH_LINE

            # Önceki satır zaten flush mu?
            prev = new_lines[-1].strip() if new_lines else ""
            if "sys.stdout.flush" not in prev:
                new_lines.append(flush)
                changed += 1

        new_lines.append(line)

    if not has_import_sys and changed > 0:
        # import sys'i dosyanın en başına ekle.
        # Shebang (#!) veya encoding bildirimi varsa onların altına.
        insert_at = 0
        for j, ln in enumerate(new_lines[:5]):
            s = ln.strip()
            if s.startswith("#!") or "coding" in s or "-*-" in s:
                insert_at = j + 1
        new_lines.insert(insert_at, "import sys  # GUI flush icin eklendi\n")

    if changed > 0:
        with open(fpath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"✅ {fname} — {changed} adet flush eklendi.")
    else:
        print(f"ℹ  {fname} — zaten güncel, değişiklik yapılmadı.")

print("\nTamamlandı. Artık GUI ile subprocess haberleşmesi düzgün çalışmalı.")