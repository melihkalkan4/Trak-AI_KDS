"""
TRAK-AI Rover — Image Classifier + DB Updater
==============================================

Saha çıkışında çekilen bitki/tarla fotoğraflarını YOLOv8 sınıflandırma
modelinden geçirir ve rover_olcumler tablosundaki ilgili kayıtların
bbch_sinif / goruntu_yolu / goruntu_guven alanlarını günceller.

Akış:
  1. data/rover_images/27may2026/  dizinindeki .jpg dosyalarını listele
  2. rover_olcumler'den kaynak='gercek_saha_27may2026' kayıtların ID'lerini al
  3. Fotoğraf sayısı != kayıt sayısı ise → numpy.linspace ile eşit aralıklı sample
  4. Her fotoğraf için YOLOv8 classify (src/cp2_model/crop_health_best.pt)
  5. BBCH_MAP ile class index → string label
  6. UPDATE rover_olcumler SET bbch_sinif, goruntu_yolu, goruntu_guven WHERE id
  7. Foto'yu classified/{id}_{bbch}_{guven:.2f}.jpg adıyla kopyala
  8. Özet rapor (sınıf dağılımı, ortalama güven)

Bağımlılıklar:
    pip install ultralytics numpy

Kullanım:
    python scripts/classify_rover_images.py
    python scripts/classify_rover_images.py --kaynak gercek_saha_27may2026
    python scripts/classify_rover_images.py --src-dir data/rover_images/27may2026
    python scripts/classify_rover_images.py --dry-run        # sadece rapor üret
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Numpy isteğe bağlı — eğer yoksa eşit aralıklı seçim manuel yapılır
try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    _NUMPY_OK = False

# Ultralytics ana bağımlılık
try:
    from ultralytics import YOLO
    _ULTRA_OK = True
    _ULTRA_ERR = ""
except ImportError as e:
    _ULTRA_OK = False
    _ULTRA_ERR = str(e)

# Project paths
THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import init_db, get_connection                # noqa: E402


# YOLOv8 model sınıf index → label haritası (FALLBACK)
# Not: Script önce model.names dict'ini kullanır (gerçek eğitim sınıfları).
# BBCH_MAP sadece model.names mevcut değilse fallback olarak kullanılır.
# Mevcut models/crop_health_best.pt sınıfları:
#   0: hastalik_mildiyo
#   1: hastalik_pas
#   2: saglikli_aycicegi
#   3: saglikli_bugday
#   4: stres_besin
#   5: stres_kuraklik
BBCH_MAP = {
    0: "hastalik_mildiyo",
    1: "hastalik_pas",
    2: "saglikli_aycicegi",
    3: "saglikli_bugday",
    4: "stres_besin",
    5: "stres_kuraklik",
}

# Varsayılan dizin ve değerler
DEFAULT_KAYNAK    = "gercek_saha_27may2026"
DEFAULT_SRC_DIR   = PROJECT_DIR / "data" / "rover_images" / "27may2026"
DEFAULT_DST_DIR   = PROJECT_DIR / "data" / "rover_images" / "classified"
DEFAULT_MODEL_PT  = PROJECT_DIR / "models" / "crop_health_best.pt"


def linspace_select(items: list, count: int) -> list:
    """N öğeyi count adet eşit aralıklı index ile sample et."""
    if count >= len(items):
        return items
    if count <= 0:
        return []
    if _NUMPY_OK:
        idxs = np.linspace(0, len(items) - 1, count, dtype=int).tolist()
    else:
        # Manuel lineer interpolasyon
        step = (len(items) - 1) / (count - 1) if count > 1 else 0
        idxs = [int(round(i * step)) for i in range(count)]
    seen = set()
    out = []
    for i in idxs:
        if i not in seen:
            out.append(items[i])
            seen.add(i)
    return out


def fetch_record_ids(kaynak: str) -> list[int]:
    """rover_olcumler'den kaynak filtresine uygun ID'leri sıralı al."""
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM rover_olcumler WHERE kaynak = ? ORDER BY timestamp ASC",
            (kaynak,)
        ).fetchall()
    return [int(r["id"]) for r in rows]


def update_record(record_id: int, sinif: str, goruntu_yolu: str, guven: float) -> None:
    """Tek kayıt için goruntu_sinif (YOLO çıktısı), goruntu_yolu, goruntu_guven update.

    NOT: Önceden bbch_sinif kolonuna yazıyordu (yanlış semantik — BBCH fenolojik
    evredir, YOLO çıktısı görüntü sınıfıdır). Hibrit BBCH motoru artık bbch_sinif'i
    yönetiyor. Bu fonksiyon YOLO çıktısını goruntu_sinif'e yazar.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE rover_olcumler "
            "SET goruntu_sinif = ?, goruntu_yolu = ?, goruntu_guven = ? "
            "WHERE id = ?",
            (sinif, goruntu_yolu, float(guven), record_id)
        )
        conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description="YOLOv8 image classifier + DB updater")
    ap.add_argument("--src-dir", type=Path, default=DEFAULT_SRC_DIR,
                    help=f"Kaynak fotoğraf dizini (default: {DEFAULT_SRC_DIR})")
    ap.add_argument("--dst-dir", type=Path, default=DEFAULT_DST_DIR,
                    help=f"Sınıflandırılmış fotoğraf hedef dizini (default: {DEFAULT_DST_DIR})")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL_PT,
                    help=f"YOLOv8 .pt model (default: {DEFAULT_MODEL_PT})")
    ap.add_argument("--kaynak", default=DEFAULT_KAYNAK,
                    help=f"Filtre: rover_olcumler.kaynak değeri (default: {DEFAULT_KAYNAK})")
    ap.add_argument("--dry-run", action="store_true",
                    help="DB güncelleme + kopyalama yapma, sadece classify et")
    args = ap.parse_args()

    # 1) Pre-check
    if not _ULTRA_OK:
        print(f"[HATA] ultralytics kütüphanesi eksik: {_ULTRA_ERR}")
        print("       Yüklemek için:  pip install ultralytics")
        sys.exit(1)

    if not args.model.exists():
        print(f"[HATA] Model dosyası bulunamadı: {args.model}")
        sys.exit(1)

    if not args.src_dir.exists():
        print(f"[HATA] Kaynak dizini yok: {args.src_dir}")
        print(f"       Fotoğrafları bu klasöre at, sonra scripti tekrar çalıştır.")
        sys.exit(1)

    # 2) Foto listesi
    photos = sorted([p for p in args.src_dir.iterdir()
                     if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if not photos:
        print(f"[HATA] {args.src_dir} içinde JPG/PNG bulunamadı.")
        sys.exit(1)

    # 3) DB kayıt ID'leri
    record_ids = fetch_record_ids(args.kaynak)
    if not record_ids:
        print(f"[HATA] rover_olcumler'de kaynak='{args.kaynak}' kayıt yok.")
        print(f"       Önce: python scripts/import_rover_log.py")
        sys.exit(1)

    print(f"[CLASSIFY] Kaynak dizini:    {args.src_dir}")
    print(f"[CLASSIFY] Hedef dizini:     {args.dst_dir}")
    print(f"[CLASSIFY] Model:            {args.model}")
    print(f"[CLASSIFY] DB filtre kaynak: {args.kaynak}")
    print(f"[CLASSIFY] Fotoğraf sayısı:  {len(photos)}")
    print(f"[CLASSIFY] DB kayıt sayısı:  {len(record_ids)}")

    # 4) Eşleştirme (sayılar farklıysa numpy.linspace)
    if len(photos) == len(record_ids):
        pairs = list(zip(record_ids, photos))
        print(f"[CLASSIFY] 1:1 eşleşme.")
    elif len(photos) > len(record_ids):
        # Fotograflari kayit sayisina göre örnekle
        selected = linspace_select(photos, len(record_ids))
        pairs = list(zip(record_ids, selected))
        print(f"[CLASSIFY] {len(photos)} foto → {len(record_ids)} kayıt'a sample edildi "
              f"(linspace).")
    else:
        # Kayıt sayisindan az foto → ID'leri sample et
        selected_ids = linspace_select(record_ids, len(photos))
        pairs = list(zip(selected_ids, photos))
        print(f"[CLASSIFY] {len(record_ids)} kayıt'tan {len(photos)} foto'ya sample "
              f"(linspace). {len(record_ids) - len(photos)} kayıt BBCH=NULL kalır.")

    print(f"[CLASSIFY] " + "-" * 50)

    # 5) Hedef dizinini hazırla
    if not args.dry_run:
        args.dst_dir.mkdir(parents=True, exist_ok=True)

    # 6) Model yükle + sınıf isimlerini al
    print(f"[CLASSIFY] Model yükleniyor: {args.model.name}")
    model = YOLO(str(args.model))
    # Modelin kendi sınıf isimlerini kullan (eğitimle birebir uyumlu)
    # model.names → {0: 'hastalik_mildiyo', 1: 'hastalik_pas', ...}
    class_map = dict(model.names) if hasattr(model, "names") and model.names else BBCH_MAP
    print(f"[CLASSIFY] Model sınıfları ({len(class_map)}):")
    for idx, name in sorted(class_map.items()):
        print(f"    {idx}: {name}")
    print()

    # 7) Classify + update döngüsü
    results_log = []     # (record_id, photo, sinif, guven)
    sinif_counter = Counter()
    confidences = []
    errors = 0

    for idx, (record_id, photo_path) in enumerate(pairs, 1):
        try:
            result = model(str(photo_path), verbose=False)
            # Classification result objesi:
            #   result[0].probs.top1     → sınıf indeksi (int)
            #   result[0].probs.top1conf → güven (tensor)
            probs = result[0].probs
            if probs is None:
                # Sınıflandırma değil, detection olabilir — atla
                print(f"[CLASSIFY] [{idx}/{len(pairs)}] probs yok: {photo_path.name} (atlandı)")
                errors += 1
                continue
            sinif_idx = int(probs.top1)
            guven_val = float(probs.top1conf)
            sinif_lbl = class_map.get(sinif_idx, f"unknown_{sinif_idx}")
        except Exception as e:
            print(f"[CLASSIFY] [{idx}/{len(pairs)}] HATA: {photo_path.name} → {e}")
            errors += 1
            continue

        # Hedef dosya yolu: classified/{id}_{bbch}_{guven:.2f}.jpg
        dst_name = f"{record_id:04d}_{sinif_lbl}_{guven_val:.2f}.jpg"
        dst_path = args.dst_dir / dst_name

        sinif_counter[sinif_lbl] += 1
        confidences.append(guven_val)
        results_log.append((record_id, photo_path.name, sinif_lbl, guven_val, dst_name))

        marker = "✓" if not args.dry_run else "[DRY]"
        print(f"[CLASSIFY] [{idx}/{len(pairs)}] {marker} id={record_id} "
              f"{photo_path.name} → {sinif_lbl} @ {guven_val*100:.0f}%")

        if args.dry_run:
            continue

        # DB update
        try:
            update_record(record_id, sinif_lbl, str(dst_path), guven_val)
        except Exception as e:
            print(f"[CLASSIFY] [{idx}/{len(pairs)}] DB UPDATE HATA id={record_id}: {e}")
            errors += 1
            continue

        # Fotoğrafı kopyala
        try:
            shutil.copy2(photo_path, dst_path)
        except Exception as e:
            print(f"[CLASSIFY] [{idx}/{len(pairs)}] COPY HATA: {e}")
            errors += 1

    # 8) Özet rapor
    print(f"[CLASSIFY] " + "=" * 50)
    print(f"[CLASSIFY] ÖZET RAPOR")
    print(f"[CLASSIFY] " + "=" * 50)
    print(f"  Toplam işlenen:      {len(results_log)} fotoğraf")
    print(f"  Hata sayısı:         {errors}")
    print()
    print(f"  Sınıf dağılımı:")
    for sinif, count in sinif_counter.most_common():
        pct = count / len(results_log) * 100 if results_log else 0
        print(f"    {count:3d}x  {sinif:<20s}  ({pct:.1f}%)")
    print()
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        print(f"  Güven istatistik:")
        print(f"    Ortalama:  {avg_conf*100:.1f}%")
        print(f"    Min:       {min_conf*100:.1f}%")
        print(f"    Max:       {max_conf*100:.1f}%")

    if not args.dry_run:
        print()
        print(f"  Sınıflandırılmış fotoğraflar: {args.dst_dir}")
        print(f"  Sorgu örneği:")
        print(f"    SELECT id, timestamp, bbch_sinif, goruntu_guven, goruntu_yolu")
        print(f"    FROM rover_olcumler WHERE kaynak='{args.kaynak}' ORDER BY id;")


if __name__ == "__main__":
    main()
