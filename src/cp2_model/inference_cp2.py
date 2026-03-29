"""
predict_cp2.py
──────────────
TRAK-AIA Karar Destek Sistemi — Tahmin Modülü

Görev   : Eğitilmiş Conv-LSTM modellerinden NDVI tahmini üretir ve
          RAG-LLM aşaması için zenginleştirilmiş bağlam metni hazırlar.
Yazar   : TRAK-AIA Ekibi
Python  : 3.9+
"""

from __future__ import annotations  # Python 3.9'da "X | None" sözdizimi için

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import tensorflow as tf

# ── Ortam & Loglama ────────────────────────────────────────────────────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # TF C++ uyarılarını gizle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("trak-aia.predict")

# ── Dizin yapısı ───────────────────────────────────────────────────────────────
# Bu dosya: <proje_koku>/src/cp2/predict_cp2.py
BASE_DIR: Path = Path(__file__).resolve().parent          # src/cp2/
PROJECT_ROOT: Path = BASE_DIR.parents[1]                  # proje kökü (2 seviye yukarı)
DATA_PATH: Path = PROJECT_ROOT / "data" / "processed" / "master_feature_matrix_2017_2024.csv"

# ── Sabitler ───────────────────────────────────────────────────────────────────
BEKLENEN_GIRDI_SEKLI = (1, 30, 7)   # (batch, zaman_adimi, ozellik_sayisi)
SON_GUN_PENCERESI = 15              # Saha özeti için kaç gün geriye bakılacak

# Zorunlu CSV sütunları — eksikse erken hata ver
ZORUNLU_SUTUNLAR = ["tp_sum", "t2m_max", "t2m_min", "e_sum", "ssr_sum"]

# ── Ürün konfigürasyonu ────────────────────────────────────────────────────────
# Yeni ürün eklemek için yalnızca bu sözlüğe satır ekle.
URUN_KONFIG: dict[str, dict[str, str]] = {
    "Bugday": {
        "model":  "model_wheat.keras",
        "veri":   "X_wheat.npy",
        "scaler": "scaler_wheat.pkl",
        "etiket": "Buğday",
    },
    "Aycicegi": {
        "model":  "model_sunflower.keras",
        "veri":   "X_sunflower.npy",
        "scaler": "scaler_sunflower.pkl",
        "etiket": "Ayçiçeği",
    },
}


# ── Yardımcı Fonksiyonlar ──────────────────────────────────────────────────────

def ndvi_yorumla(deger: float) -> str:
    """NDVI değerini literatür eşiklerine göre metinsel olarak yorumlar."""
    if deger < 0.2:
        return "KRİTİK — Bitki örtüsü çok zayıf veya hasarlı"
    if deger < 0.4:
        return "DÜŞÜK — Stres belirtileri mevcut, müdahale önerilir"
    if deger < 0.6:
        return "ORTA — Makul bitki sağlığı, takip edilmeli"
    if deger < 0.8:
        return "İYİ — Sağlıklı bitki örtüsü"
    return "MÜKEMMEL — Yoğun ve güçlü bitki örtüsü"


def guncel_durum_ozeti_cikar(csv_yolu: Path = DATA_PATH) -> str:
    """
    İşlenmiş CSV'nin son `SON_GUN_PENCERESI` gününe bakarak tarlanın
    mevcut iklim ve toprak durumunu özetler.

    Döndürür
    --------
    str : LLM bağlamına eklenmeye hazır Türkçe özet cümlesi.
          Dosya okunamazsa veya sütun eksikse açıklayıcı bir hata dizesi döner.
    """
    if not csv_yolu.exists():
        logger.warning("Saha CSV dosyası bulunamadı: %s", csv_yolu)
        return f"Saha verisi okunamadı (dosya yok: {csv_yolu})."

    try:
        df = pd.read_csv(csv_yolu)
    except Exception as exc:
        logger.error("CSV okuma hatası: %s", exc)
        return f"Saha verisi okunamadı (okuma hatası: {exc})."

    # Zorunlu sütun kontrolü — sessiz NaN yerine açık hata
    eksik = [s for s in ZORUNLU_SUTUNLAR if s not in df.columns]
    if eksik:
        logger.error("CSV'de eksik sütunlar: %s", eksik)
        return f"Saha verisi eksik sütunlar içeriyor: {eksik}."

    son_n = df.tail(SON_GUN_PENCERESI)

    toplam_yagis      = son_n["tp_sum"].sum()
    ort_max_sicaklik  = son_n["t2m_max"].mean()
    ort_min_sicaklik  = son_n["t2m_min"].mean()
    toplam_buharlasma = son_n["e_sum"].sum()
    ort_radyasyon     = son_n["ssr_sum"].mean()

    return (
        f"Son {SON_GUN_PENCERESI} Günün Saha Verileri: "
        f"Toplam Yağış: {toplam_yagis:.2f} mm, "
        f"Ort. Gündüz Sıcaklığı: {ort_max_sicaklik:.2f}°C, "
        f"Ort. Gece Sıcaklığı: {ort_min_sicaklik:.2f}°C, "
        f"Net Buharlaşma/Nem Kaybı (e_sum): {toplam_buharlasma:.4f}, "
        f"Ortalama Yüzey Radyasyonu: {ort_radyasyon:.0f} J/m²."
    )


def _model_yukle(model_yolu: Path) -> tf.keras.Model:
    """Modeli yükler; bulunamazsa anlamlı hata fırlatır."""
    if not model_yolu.exists():
        raise FileNotFoundError(
            f"Model bulunamadı: {model_yolu}\n"
            "Lütfen önce train_cp2.py ile modeli eğitin."
        )
    logger.info("Model yükleniyor: %s", model_yolu.name)
    return tf.keras.models.load_model(str(model_yolu))


def _girdi_hazirla(
    konfig: dict[str, str],
    canli_veri: Optional[np.ndarray],
) -> tuple[np.ndarray, str]:
    """
    Tahmin için girdi dizisini ve kaynağını döndürür.

    Üretim   → canli_veri parametresiyle dışarıdan (1, 30, 7) dizisi verilir.
    Test/Dev → canli_veri=None ise X_*.npy'nin son dilimi kullanılır.
    """
    if canli_veri is not None:
        if canli_veri.shape != BEKLENEN_GIRDI_SEKLI:
            raise ValueError(
                f"Beklenen girdi şekli: {BEKLENEN_GIRDI_SEKLI}, "
                f"gelen: {canli_veri.shape}"
            )
        return canli_veri, "canli_sensor_verisi"

    # Test yolu
    veri_yolu = BASE_DIR / konfig["veri"]
    if not veri_yolu.exists():
        raise FileNotFoundError(
            f"Veri bulunamadı: {veri_yolu}\n"
            "Lütfen önce preprocessing_cp2.py'yi çalıştırın."
        )
    X = np.load(str(veri_yolu))
    logger.warning(
        "Canlı veri yok — '%s' eğitim setinin son dilimi kullanılıyor (test modu).",
        konfig["etiket"],
    )
    return X[-1:], "test_verisi_son_dilim"


# ── Ana Tahmin Fonksiyonu ──────────────────────────────────────────────────────

def tahmin_al(
    urun_tipi: str,
    canli_veri: Optional[np.ndarray] = None,
    saha_ozeti: Optional[str] = None,
) -> dict:
    """
    Belirtilen ürün için NDVI tahmini üretir.

    Parametreler
    ------------
    urun_tipi   : 'Bugday' veya 'Aycicegi'
    canli_veri  : (1, 30, 7) şeklinde numpy dizisi.
                  None → X_*.npy'nin son dilimi (yalnızca test).
    saha_ozeti  : Önceden hesaplanmış saha özeti metni.
                  None → otomatik olarak CSV'den okunur.
                  Birden fazla ürün tahmini alınıyorsa dışarıdan
                  tek seferlik hesaplanıp buraya verilmesi önerilir.

    Döndürür
    --------
    dict anahtarları:
        urun          – Ürün etiketi (Türkçe)
        tahmin_degeri – Kırpılmış NDVI (float, 4 ondalık)
        yorum         – Metinsel NDVI yorumu
        veri_kaynagi  – 'canli_sensor_verisi' | 'test_verisi_son_dilim'
        saha_ozeti    – Son N günün iklim özeti
        llm_baglami   – RAG-LLM'e doğrudan aktarılabilecek bağlam metni
    """
    if urun_tipi not in URUN_KONFIG:
        gecerli = ", ".join(f"'{k}'" for k in URUN_KONFIG)
        raise ValueError(
            f"Geçersiz ürün tipi: '{urun_tipi}'. Geçerli seçenekler: {gecerli}"
        )

    konfig = URUN_KONFIG[urun_tipi]

    model        = _model_yukle(BASE_DIR / konfig["model"])
    girdi, kaynak = _girdi_hazirla(konfig, canli_veri)

    # Scaler entegrasyonu (eğitimde kullanıldıysa yorumu kaldır)
    # scaler_yolu = BASE_DIR / konfig["scaler"]
    # if scaler_yolu.exists():
    #     import joblib
    #     scaler = joblib.load(str(scaler_yolu))
    #     girdi = scaler.transform(girdi.reshape(-1, 7)).reshape(BEKLENEN_GIRDI_SEKLI)

    tahmin_ham  = float(model.predict(girdi, verbose=0)[0][0])
    tahmin_klip = float(np.clip(tahmin_ham, -1.0, 1.0))
    yorum       = ndvi_yorumla(tahmin_klip)

    # Saha özeti: dışarıdan verilmediyse hesapla (tekrar I/O'yu önler)
    if saha_ozeti is None:
        saha_ozeti = guncel_durum_ozeti_cikar()

    llm_baglami = (
        f"{konfig['etiket']} tarlası için tahmin edilen NDVI değeri "
        f"{tahmin_klip:.4f} olup bitki gelişimi '{yorum}' "
        f"olarak değerlendirilmektedir.\n"
        f"{saha_ozeti}"
    )

    return {
        "urun":          konfig["etiket"],
        "tahmin_degeri": round(tahmin_klip, 4),
        "yorum":         yorum,
        "veri_kaynagi":  kaynak,
        "saha_ozeti":    saha_ozeti,
        "llm_baglami":   llm_baglami,   # düzeltildi: Kiril "и" → Latin "i"
    }


# ── CLI Girişi ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  TRAK-AIA KARAR DESTEK SİSTEMİ — TAHMİN MODÜLÜ")
    print("=" * 60)

    # CSV tek seferlik okunur, tüm ürünlerde paylaşılır
    paylasilan_saha_ozeti = guncel_durum_ozeti_cikar()
    logger.info("Saha özeti hazırlandı.")

    for urun_kodu in URUN_KONFIG:
        print()
        try:
            sonuc = tahmin_al(urun_kodu, saha_ozeti=paylasilan_saha_ozeti)

            print(f"  Ürün         : {sonuc['urun']}")
            print(f"  NDVI         : {sonuc['tahmin_degeri']:.4f}")
            print(f"  Yorum        : {sonuc['yorum']}")
            print(f"  Veri kaynağı : {sonuc['veri_kaynagi']}")
            print(f"  LLM Bağlamı  :\n    {sonuc['llm_baglami']}")

        except (FileNotFoundError, ValueError) as hata:
            logger.error("[%s] %s", urun_kodu, hata)

    print()
    print("─" * 60)
    print("Tahmin modülü tamamlandı. Veriler RAG-LLM'e aktarılmaya hazır.")