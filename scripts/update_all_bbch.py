"""
Tüm tarlalar için hibrit BBCH motoru çalıştır + rover_olcumler güncelle.

Bugün yapılan ölçümlere BBCH hesaplanır:
  rover_olcumler SET bbch_sinif, bbch_kaynak, bbch_guven
  WHERE DATE(timestamp) = DATE('now') AND bbch_sinif IS NULL

Eski tarihli kayıtlar için: ölçüm tarihini referans alarak BBCH hesapla.

Kullanım:
    python scripts/update_all_bbch.py
    python scripts/update_all_bbch.py --all     # tüm kayıtları update
    python scripts/update_all_bbch.py --tarla 1
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")        # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")        # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass

THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import get_connection, init_db                # noqa: E402
from bbch_engine import hesapla_bbch                         # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="Tüm rover_olcumler kayıtlarını güncelle (default: sadece bugün)")
    ap.add_argument("--tarla", type=int, default=None,
                    help="Sadece bu tarla için")
    args = ap.parse_args()

    init_db()
    today = date.today()

    # Aktif tarlalar
    with get_connection() as c:
        if args.tarla:
            tarlalar = c.execute(
                "SELECT id, name, evrenli_id, crop_type FROM tarla WHERE id = ?",
                (args.tarla,)
            ).fetchall()
        else:
            tarlalar = c.execute(
                "SELECT id, name, evrenli_id, crop_type FROM tarla "
                "WHERE crop_type IS NOT NULL"
            ).fetchall()

    if not tarlalar:
        print("[HATA] Tarla bulunamadı")
        sys.exit(1)

    print(f"[BBCH] {len(tarlalar)} tarla için hesaplama")
    print("-" * 60)

    total_updated = 0
    for t in tarlalar:
        tarla_id = t["id"]
        crop = t["crop_type"]
        print(f"\n[BBCH] Tarla {tarla_id} ({t['evrenli_id']}, {crop}):")

        # Bugün için hesapla
        result = hesapla_bbch(tarla_id, today)
        if not result.get("bbch"):
            print(f"  HESAP YAPILAMADI: {result.get('uyari', '?')}")
            continue

        bbch = result["bbch"]
        kaynak = result["kaynak"]
        guven = result["guven"]
        uyari = result.get("uyari", "")

        print(f"  BBCH:    {bbch}")
        print(f"  Kaynak:  {kaynak}")
        print(f"  Güven:   {guven:.0%}")
        if uyari:
            print(f"  Uyarı:   {uyari}")
        if result.get("detay"):
            print(f"  Detay:   {json.dumps(result['detay'], ensure_ascii=False, default=str)}")

        # rover_olcumler güncelle
        if args.all:
            # TÜM kayıtları güncelle (tarih bağımsız)
            where = "tarla_id = ?"
            params = (tarla_id,)
        else:
            # Sadece bugünün kayıtlarını veya bbch_sinif boş olanları
            where = ("tarla_id = ? AND (bbch_sinif IS NULL "
                     "OR DATE(timestamp) = DATE('now'))")
            params = (tarla_id,)

        with get_connection() as conn:
            cur = conn.execute(
                f"UPDATE rover_olcumler "
                f"SET bbch_sinif = ?, bbch_kaynak = ?, bbch_guven = ? "
                f"WHERE {where}",
                (bbch, kaynak, guven) + params
            )
            n = cur.rowcount
            conn.commit()
        print(f"  → {n} rover_olcumler satırı güncellendi")
        total_updated += n

    print()
    print("=" * 60)
    print(f"TAMAMLANDI: Toplam {total_updated} satır güncellendi")
    print("=" * 60)


if __name__ == "__main__":
    main()
