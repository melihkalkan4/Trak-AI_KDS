"""
EVR_01 tarlasının ürün tipini 'sunflower' -> 'bugday' (wheat) düzelt.

NOT: tarlalar bir VIEW (tarla TABLE üstünde). UPDATE doğrudan tarla
tablosuna yapılır. crop_type kolonu kullanılır.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from database import get_connection, init_db  # noqa: E402


def main() -> None:
    init_db()
    with get_connection() as conn:
        # Önce mevcut durumu göster
        before = conn.execute(
            "SELECT id, name, evrenli_id, crop_type FROM tarla "
            "WHERE evrenli_id='EVR_01'"
        ).fetchone()
        if before is None:
            print("[HATA] EVR_01 bulunamadı")
            sys.exit(1)
        print(f"[ONCE] id={before['id']} name={before['name']} crop_type={before['crop_type']}")

        cur = conn.execute(
            "UPDATE tarla SET crop_type='wheat' WHERE evrenli_id='EVR_01'"
        )
        conn.commit()
        n = cur.rowcount

        after = conn.execute(
            "SELECT id, name, evrenli_id, crop_type FROM tarla "
            "WHERE evrenli_id='EVR_01'"
        ).fetchone()
        print(f"[SONRA] crop_type={after['crop_type']}")
        print(f"[OK] Güncellenen: {n} kayıt")


if __name__ == "__main__":
    main()
