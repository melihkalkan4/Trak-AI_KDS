"""
TRAK-AI YOLOv8 Saha Tahmin Log Üretici
========================================

logs/visual_field_yolov8.jsonl dosyasını rover_olcumler tablosundaki
classified fotoğraflardan üretir. Cross-Modal dashboard sekmesi ve
audit pipeline tarafından okunur.

Şema (her satır JSON):
    {
      "timestamp": "2026-05-27T17:41:17",
      "site_id": "EVR_01",
      "evrenli_id": "EVR_01",
      "image": "data/rover_images/classified/0004_saglikli_bugday_0.58.jpg",
      "predicted_class": "saglikli_bugday",
      "confidence": 0.58,
      "n_detections": 1,
      "rover_id": "trak-ai-rover-01",
      "kaynak": "gercek_saha_27may2026"
    }

Kullanım:
    python scripts/generate_yolov8_field_log.py
    python scripts/generate_yolov8_field_log.py --append    # mevcut log'a ekle
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import init_db, get_connection             # noqa: E402

LOGS_DIR  = PROJECT_DIR / "logs"
LOG_FILE  = LOGS_DIR / "visual_field_yolov8.jsonl"

# Tarla ID → site_id mapping (config)
TARLA_TO_SITE = {
    1: "EVR_01",
    2: "EVR_02",
    3: "EVR_03",
    4: "EVR_04",
    5: "EVR_05",
}


def main() -> None:
    ap = argparse.ArgumentParser(description="YOLOv8 saha log üretici")
    ap.add_argument("--append", action="store_true",
                    help="Mevcut log'a ekle (default: üzerine yaz)")
    args = ap.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    with get_connection() as c:
        rows = c.execute("""
            SELECT id, timestamp, tarla_id, rover_id, goruntu_sinif,
                   goruntu_guven, goruntu_yolu, kaynak
            FROM rover_olcumler
            WHERE goruntu_sinif IS NOT NULL
              AND goruntu_yolu IS NOT NULL
            ORDER BY timestamp ASC
        """).fetchall()

    if not rows:
        print(f"[HATA] DB'de classified foto kaydı bulunamadı.")
        print(f"       Önce: python scripts/classify_rover_images.py")
        sys.exit(1)

    print(f"[YOLOv8] {len(rows)} classified kayıt bulundu")
    print(f"[YOLOv8] Çıkış: {LOG_FILE}")

    mode = "a" if args.append else "w"
    written = 0
    skipped = 0

    with LOG_FILE.open(mode, encoding="utf-8") as f:
        for r in rows:
            rd = dict(r)
            site_id = TARLA_TO_SITE.get(rd.get("tarla_id"), "EVR_01")
            entry = {
                "timestamp":       rd["timestamp"],
                "site_id":         site_id,
                "evrenli_id":      site_id,
                "image":           rd.get("goruntu_yolu", ""),
                "predicted_class": rd.get("goruntu_sinif", "UNKNOWN"),
                "confidence":      float(rd.get("goruntu_guven") or 0.0),
                "n_detections":    1,
                "rover_id":        rd.get("rover_id", "trak-ai-rover-01"),
                "kaynak":          rd.get("kaynak", "unknown"),
                "rover_record_id": rd["id"],
            }
            try:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                written += 1
            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"[YOLOv8] Satır yazma hatası id={rd['id']}: {e}")

    print(f"[YOLOv8] Yazıldı: {written} satır, atlanan: {skipped}")
    print(f"[YOLOv8] Dosya boyutu: {LOG_FILE.stat().st_size / 1024:.1f} KB")

    # Sınıf dağılım istatistiği
    classes: dict[str, int] = {}
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                c = d.get("predicted_class", "?")
                classes[c] = classes.get(c, 0) + 1
            except Exception:
                pass
    if classes:
        print(f"[YOLOv8] Sınıf dağılımı:")
        for cls, n in sorted(classes.items(), key=lambda x: -x[1]):
            print(f"           {n:4d}x  {cls}")


if __name__ == "__main__":
    main()
