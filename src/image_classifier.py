"""
TRAK-AI KDS — Görüntü Sınıflandırıcı
========================================
YOLOv8s-cls tabanlı bitki sağlık sınıflandırması.
Model dosyası yoksa otomatik mock modda çalışır.

Mimari: Hybrid Edge-Fog — ESP32-CAM JPEG gönderir, burada YOLOv8 çalışır.

Model sınıf sırası (YOLOv8 model.names — alfabetik):
  0: hastalik_mildiyo  (%99.1)
  1: hastalik_pas      (%91.0)
  2: saglikli_aycicegi (%100.0)
  3: saglikli_bugday   (%98.0)
  4: stres_besin       (%85.2)
  5: stres_kuraklik    (%100.0 — overfit riski)
"""
import os
import base64
import io
import random
import logging

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))  # src/
PROJECT_ROOT = os.path.dirname(_SRC_DIR)
DEFAULT_MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "crop_health_best.pt")

logger = logging.getLogger("trak-ai.image-clf")

try:
    from ultralytics import YOLO as _YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    _ULTRALYTICS_AVAILABLE = False
    logger.info("ultralytics yuklu degil — mock mod aktif")

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# Gerçek model sınıf sırası: YOLOv8 model.names (alfabetik sıralı)
SINIF_LABELS = {
    0: {
        "sinif": "hastalik_mildiyo",
        "hastalik": "Mildiyo (Plasmopara)",
        "bbch_aralik": None,
        "aciklama": "Aycicegi mildiyo tespit edildi",
    },
    1: {
        "sinif": "hastalik_pas",
        "hastalik": "Pas (Puccinia)",
        "bbch_aralik": None,
        "aciklama": "Bugday yaprak pasi tespit edildi",
    },
    2: {
        "sinif": "saglikli_aycicegi",
        "hastalik": None,
        "bbch_aralik": "10-89",
        "aciklama": "Saglikli aycicegi bitkisi",
    },
    3: {
        "sinif": "saglikli_bugday",
        "hastalik": None,
        "bbch_aralik": "50-89",
        "aciklama": "Saglikli bugday bitkisi",
    },
    4: {
        "sinif": "stres_besin",
        "hastalik": None,
        "bbch_aralik": None,
        "aciklama": "Besin eksikligi belirtileri",
    },
    5: {
        "sinif": "stres_kuraklik",
        "hastalik": None,
        "bbch_aralik": None,
        "aciklama": "Kuraklik stresi belirtileri",
    },
}

# KDS aksiyon tablosu: her sınıf için ne yapılmalı
KDS_AKSIYONLAR = {
    "hastalik_pas":       {"aksiyon": "ILACLAMA", "aciliyet": "YUKSEK", "tavsiye": "Fungisit uygulamasi gerekli — Tebukkonazol veya Propikonazol"},
    "hastalik_mildiyo":   {"aksiyon": "ILACLAMA", "aciliyet": "YUKSEK", "tavsiye": "Mildiyo ilaci uygulanmali — Metalaksil + Mankozeb"},
    "stres_kuraklik":     {"aksiyon": "SULAMA",   "aciliyet": "ACIL",   "tavsiye": "Acil sulama gerekli — 30-40 mm/da"},
    "stres_besin":        {"aksiyon": "GUBRE",    "aciliyet": "ORTA",   "tavsiye": "Azot takviyesi onerilir — Ure veya CAN"},
    "saglikli_bugday":    {"aksiyon": "YOK",      "aciliyet": "NORMAL", "tavsiye": "Bitki saglikli, rutin izleme yeterli"},
    "saglikli_aycicegi":  {"aksiyon": "YOK",      "aciliyet": "NORMAL", "tavsiye": "Bitki saglikli, rutin izleme yeterli"},
}


class CropHealthClassifier:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        if not _ULTRALYTICS_AVAILABLE:
            logger.info("ultralytics yok — mock mod")
            return
        if not os.path.exists(self.model_path):
            logger.info("Model bulunamadi: %s — mock mod aktif", self.model_path)
            return
        try:
            self.model = _YOLO(self.model_path)
            logger.info(
                "YOLOv8 modeli yuklendi: %s | Siniflar: %s",
                self.model_path,
                list(self.model.names.values()),
            )
        except Exception as e:
            logger.warning("Model yukleme hatasi: %s — mock mod", e)

    def classify_base64(self, base64_string: str) -> dict:
        try:
            img_bytes = base64.b64decode(base64_string)
            if not _PIL_AVAILABLE:
                return self._mock_result()
            img = _PILImage.open(io.BytesIO(img_bytes))
            return self.classify_image(img)
        except Exception as e:
            return self._error_result(str(e))

    def classify_image(self, image) -> dict:
        if self.model is None:
            return self._mock_result()
        try:
            result = self.model.predict(image, verbose=False)[0]
            top1_idx = int(result.probs.top1)
            top1_conf = float(result.probs.top1conf.item())

            sinif_info = SINIF_LABELS.get(top1_idx, {
                "sinif": "bilinmiyor",
                "hastalik": None,
                "bbch_aralik": None,
                "aciklama": "Sinif tanimsiz",
            })
            sinif_key = sinif_info["sinif"]

            return {
                "sinif": sinif_key,
                "guven": round(top1_conf, 3),
                "hastalik": sinif_info.get("hastalik"),
                "bbch_aralik": sinif_info.get("bbch_aralik"),
                "aciklama": sinif_info.get("aciklama", ""),
                "aksiyon": KDS_AKSIYONLAR.get(sinif_key, {}),
                "tum_olasiliklar": {
                    SINIF_LABELS[i]["sinif"]: round(float(result.probs.data[i].item()), 3)
                    for i in range(len(result.probs.data))
                    if i in SINIF_LABELS
                },
            }
        except Exception as e:
            return self._error_result(str(e))

    def classify_file(self, image_path: str) -> dict:
        if not _PIL_AVAILABLE:
            return self._mock_result()
        try:
            img = _PILImage.open(image_path)
            return self.classify_image(img)
        except Exception as e:
            return self._error_result(str(e))

    def classify(self, *args, **kwargs) -> dict:
        return self.classify_file(*args, **kwargs)

    def _mock_result(self) -> dict:
        # Ağırlıklı: sağlıklı %70, hastalık %20, stres %10
        weights = [10, 10, 35, 35, 5, 5]  # model sınıf sırası: mildiyo, pas, s_ayci, s_bugday, besin, kuraklik
        idx = random.choices(list(SINIF_LABELS.keys()), weights=weights, k=1)[0]
        info = SINIF_LABELS[idx]
        sinif_key = info["sinif"]
        return {
            "sinif": sinif_key,
            "guven": round(random.uniform(0.65, 0.95), 3),
            "hastalik": info.get("hastalik"),
            "bbch_aralik": info.get("bbch_aralik"),
            "aciklama": info.get("aciklama", ""),
            "aksiyon": KDS_AKSIYONLAR.get(sinif_key, {}),
            "mock": True,
        }

    def _error_result(self, error: str) -> dict:
        return {
            "sinif": "hata",
            "guven": 0.0,
            "hastalik": None,
            "bbch_aralik": None,
            "aciklama": f"Siniflandirma hatasi: {error}",
            "aksiyon": {},
            "error": error,
        }


# Global instance — import edildiğinde bir kez yüklenir
classifier = CropHealthClassifier()


def classify_rover_image(base64_or_path: str) -> dict:
    """
    Rover'dan gelen görüntüyü sınıflandır.
    base64_or_path: base64 string (>500 karakter) veya dosya yolu
    """
    if isinstance(base64_or_path, str) and len(base64_or_path) > 500:
        return classifier.classify_base64(base64_or_path)
    elif isinstance(base64_or_path, str) and os.path.exists(base64_or_path):
        return classifier.classify_file(base64_or_path)
    else:
        return classifier._mock_result()
