"""
TRAK-AI Rover — Telnet Log → DB Importer
==========================================

Telnet üzerinden yakalanan rover log dosyasını parse edip
SQLite rover_olcumler tablosuna toplu yükler.

Log formatı (her satır):
    [17:40:50] rover/data Nem=33.81818 Temp= 27.6 Engel=  13cm BBCH=BILINMIYOR

Parse edilen alanlar:
    timestamp     ← 2026-05-27 + saat (HH:MM:SS)
    nem_1_pct     ← Nem= değeri (float)
    hava_temp_c   ← Temp= değeri (float)
    engel_on_cm   ← Engel= cm (int; 999 ise NULL)
    bbch_sinif    ← BBCH= (BILINMIYOR ise NULL — sonra classify ile doldurulur)

Ek olarak (sabit değerler):
    tarla_id  = 1                           (EVR_01)
    rover_id  = "trak-ai-rover-01"
    kaynak    = "gercek_saha_27may2026"
    nem_2_pct = NULL                        (tek sensör)
    gps_*     = NULL                        (kapalı alan, fix yoktu)

Kullanım:
    python scripts/import_rover_log.py
    python scripts/import_rover_log.py --log scripts/rover_log_27may2026.txt
    python scripts/import_rover_log.py --date 2026-05-27
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# src/ klasorunu sys.path'e ekle (database.py import icin)
THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import init_db, add_rover_olcum                # noqa: E402


# Regex pattern: [HH:MM:SS] rover/data Nem=X.X Temp= X.X Engel=  XXcm BBCH=XXX
LOG_PATTERN = re.compile(
    r"\[(?P<time>\d{2}:\d{2}:\d{2})\]\s+"
    r"rover/data\s+"
    r"Nem=\s*(?P<nem>-?\d+\.?\d*)\s+"
    r"Temp=\s*(?P<temp>-?\d+\.?\d*)\s+"
    r"Engel=\s*(?P<engel>\d+)cm\s+"
    r"BBCH=(?P<bbch>\S+)"
)

DEFAULT_LOG_PATH = THIS_DIR / "rover_log_27may2026.txt"
DEFAULT_DATE     = "2026-05-27"
TARLA_ID         = 1
ROVER_ID         = "trak-ai-rover-01"
KAYNAK           = "gercek_saha_27may2026"


def parse_line(line: str, date_str: str) -> Optional[dict]:
    """Tek satır parse et. Eşleşmezse None döner."""
    m = LOG_PATTERN.search(line)
    if not m:
        return None

    time_str = m.group("time")
    timestamp = f"{date_str} {time_str}"

    engel_raw = int(m.group("engel"))
    engel_val = None if engel_raw == 999 else engel_raw

    bbch_raw = m.group("bbch").strip()
    bbch_val = None if bbch_raw.upper() == "BILINMIYOR" else bbch_raw

    return {
        "tarla_id":     TARLA_ID,
        "rover_id":     ROVER_ID,
        "timestamp":    timestamp,
        "nem_1_pct":    float(m.group("nem")),
        "nem_2_pct":    None,
        "hava_temp_c":  float(m.group("temp")),
        "hava_nem_pct": None,         # log'da yok
        "engel_on_cm":  engel_val,
        "engel_arka_cm": None,
        "gps_lat":      None,         # kapalı alan, fix yok
        "gps_lon":      None,
        "bbch_sinif":   bbch_val,
        "bbch_guven":   None,
        "kaynak":       KAYNAK,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Rover log → SQLite importer")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG_PATH,
                    help=f"Log dosyası yolu (default: {DEFAULT_LOG_PATH})")
    ap.add_argument("--date", default=DEFAULT_DATE,
                    help=f"Log tarihi YYYY-MM-DD (default: {DEFAULT_DATE})")
    ap.add_argument("--dry-run", action="store_true",
                    help="DB'ye yazma, sadece parse ettiklerini göster")
    args = ap.parse_args()

    if not args.log.exists():
        print(f"[HATA] Log dosyası bulunamadı: {args.log}")
        print(f"       Dosyayı oluştur ve içine telnet çıktısını yapıştır.")
        sys.exit(1)

    # Tarih doğrulama
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"[HATA] Tarih formatı yanlış: {args.date} (YYYY-MM-DD bekleniyor)")
        sys.exit(1)

    print(f"[IMPORT] Log dosyası:  {args.log}")
    print(f"[IMPORT] Tarih:        {args.date}")
    print(f"[IMPORT] tarla_id={TARLA_ID} rover_id={ROVER_ID} kaynak={KAYNAK}")
    print(f"[IMPORT] " + "-" * 50)

    if not args.dry_run:
        init_db()

    # Parse + insert
    parsed_count = 0
    skipped_count = 0
    inserted_count = 0
    insert_errors = 0
    first_id = None
    last_id = None

    with args.log.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            line = line.rstrip()
            if not line:
                continue
            record = parse_line(line, args.date)
            if record is None:
                skipped_count += 1
                continue
            parsed_count += 1

            if args.dry_run:
                if parsed_count <= 5:
                    print(f"  Satir {line_no}: {record}")
                continue

            try:
                # add_rover_olcum tarla_id'yi ayrı parametre alır
                tarla = record.pop("tarla_id")
                row_id = add_rover_olcum(tarla, record)
                inserted_count += 1
                if first_id is None:
                    first_id = row_id
                last_id = row_id
            except Exception as e:
                insert_errors += 1
                if insert_errors <= 3:
                    print(f"  [HATA satir {line_no}] {e}")

    # Özet
    print(f"[IMPORT] " + "-" * 50)
    print(f"[IMPORT] Toplam parse edilen:   {parsed_count}")
    print(f"[IMPORT] Atlanan (parse fail):  {skipped_count}")
    if args.dry_run:
        print(f"[IMPORT] DRY-RUN — DB'ye yazılmadı")
    else:
        print(f"[IMPORT] DB'ye eklendi:         {inserted_count}")
        print(f"[IMPORT] INSERT hatası:         {insert_errors}")
        if first_id is not None:
            print(f"[IMPORT] ID aralığı:            {first_id} ... {last_id}")
        print()
        print(f"[OK] {inserted_count} kayıt rover_olcumler tablosuna yazıldı.")
        print(f"     Sorgu: SELECT * FROM rover_olcumler WHERE kaynak='{KAYNAK}';")


if __name__ == "__main__":
    main()
