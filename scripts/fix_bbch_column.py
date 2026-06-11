"""
BBCH sütunu temizliği — YOLO görüntü sınıfını goruntu_sinif'e taşı.

Sorun: classify_rover_images.py YOLO sınıf adını (saglikli_bugday vb.)
bbch_sinif kolonuna yazdı. Doğru BBCH evresi "00-09", "70-79" gibi
fenolojik kod olmalı. Bu script:

1. goruntu_sinif kolonunu ekler (yoksa)
2. bbch_sinif'teki YOLO çıktısını (saglikli_*, hastalik_*, stres_*,
   hasat_*) goruntu_sinif'e kopyalar
3. Yanlış kullanılmış bbch_sinif değerlerini NULL'a çevirir
4. Gerçek BBCH formatında olan (BBCH_50_59 gibi) değerleri korur

Kullanım:
    python scripts/fix_bbch_column.py
    python scripts/fix_bbch_column.py --dry-run    # sadece raporla
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from database import get_connection, init_db  # noqa: E402


# YOLO çıktı desenleri — bunlar BBCH değil, görüntü sınıfı
YOLO_PATTERNS = [
    r"^saglikli_",   # saglikli_bugday, saglikli_aycicegi
    r"^hastalik_",   # hastalik_pas, hastalik_mildiyo
    r"^stres_",      # stres_kuraklik, stres_besin
    r"^hasat_",      # hasat_olgun
]

YOLO_REGEX = re.compile("|".join(YOLO_PATTERNS))

# Gerçek BBCH desenleri (korunacak)
BBCH_REGEX = re.compile(r"^(BBCH_\d+_\d+|\d{2}-\d{2})$")


def is_yolo_class(value: str) -> bool:
    return bool(YOLO_REGEX.match(value or ""))


def is_real_bbch(value: str) -> bool:
    return bool(BBCH_REGEX.match(value or ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="DB değiştirme, sadece raporla")
    args = ap.parse_args()

    init_db()

    with get_connection() as conn:
        # 1. goruntu_sinif kolonu ekle (yoksa)
        cols = [r["name"] for r in conn.execute(
            "PRAGMA table_info(rover_olcumler)").fetchall()]
        added_cols = []
        if "goruntu_sinif" not in cols:
            if not args.dry_run:
                conn.execute("ALTER TABLE rover_olcumler ADD COLUMN goruntu_sinif TEXT")
            added_cols.append("goruntu_sinif")
        if "bbch_kaynak" not in cols:
            # BBCH hesap kaynağı (GDD/NDVI/DATE)
            if not args.dry_run:
                conn.execute("ALTER TABLE rover_olcumler ADD COLUMN bbch_kaynak TEXT")
            added_cols.append("bbch_kaynak")
        if added_cols:
            if not args.dry_run:
                conn.commit()
            print(f"[FIX] Yeni kolonlar: {', '.join(added_cols)}")

        # 2. Mevcut bbch_sinif değerlerini incele
        rows = conn.execute(
            "SELECT id, bbch_sinif, goruntu_guven FROM rover_olcumler "
            "WHERE bbch_sinif IS NOT NULL"
        ).fetchall()

        yolo_count = 0
        bbch_count = 0
        other_count = 0
        examples_yolo = []
        examples_other = []

        for r in rows:
            val = r["bbch_sinif"]
            if is_yolo_class(val):
                yolo_count += 1
                if len(examples_yolo) < 3:
                    examples_yolo.append((r["id"], val))
            elif is_real_bbch(val):
                bbch_count += 1
            else:
                other_count += 1
                if len(examples_other) < 3:
                    examples_other.append((r["id"], val))

        total = len(rows)
        print(f"[ANALYSIS] bbch_sinif IS NOT NULL toplamı: {total}")
        print(f"  - YOLO görüntü sınıfı:  {yolo_count}  ({yolo_count/total*100:.1f}%)")
        if examples_yolo:
            for i, v in examples_yolo:
                print(f"      Örnek: id={i} bbch_sinif={v!r}")
        print(f"  - Gerçek BBCH formatı: {bbch_count}  ({bbch_count/total*100:.1f}%)")
        print(f"  - Diğer/bilinmeyen:     {other_count}  ({other_count/total*100:.1f}%)")
        if examples_other:
            for i, v in examples_other:
                print(f"      Örnek: id={i} bbch_sinif={v!r}")

        if args.dry_run:
            print()
            print("[DRY RUN] DB değiştirilmedi.")
            return

        # 3. YOLO çıktılarını goruntu_sinif'e taşı, bbch_sinif NULL yap
        moved = 0
        with get_connection() as conn2:
            for r in rows:
                val = r["bbch_sinif"]
                if not is_yolo_class(val):
                    continue
                # Taşı: bbch_sinif -> goruntu_sinif
                conn2.execute(
                    "UPDATE rover_olcumler "
                    "SET goruntu_sinif = ?, bbch_sinif = NULL "
                    "WHERE id = ?",
                    (val, r["id"])
                )
                moved += 1
            conn2.commit()

        print()
        print(f"[FIX] Taşınan kayıt: {moved}")
        print(f"      bbch_sinif (YOLO değerleri) -> goruntu_sinif")
        print(f"      bbch_sinif -> NULL (BBCH hibrit motor yeniden hesaplayacak)")

        # 4. Final durum
        final = conn2.execute(
            "SELECT COUNT(*) FILTER (WHERE bbch_sinif IS NOT NULL) AS bbch_dolu, "
            "       COUNT(*) FILTER (WHERE goruntu_sinif IS NOT NULL) AS gor_dolu "
            "FROM rover_olcumler"
        ).fetchone()
        print()
        print(f"[FINAL] bbch_sinif dolu:    {final['bbch_dolu']}")
        print(f"        goruntu_sinif dolu: {final['gor_dolu']}")


if __name__ == "__main__":
    main()
