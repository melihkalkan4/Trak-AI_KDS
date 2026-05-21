# YOLOv8 Model Dosyaları

Colab'dan eğitim sonrası buraya kopyala:
- `crop_health_best.pt` — Ana model (PyTorch)
- `crop_health_best.onnx` — ONNX formatı (opsiyonel, hızlı inference)

Model yoksa sistem otomatik olarak mock modda çalışır.

## Sınıflar (6)

| ID | Sınıf | Açıklama |
|---|---|---|
| 0 | saglikli_bugday | Sağlıklı buğday |
| 1 | saglikli_aycicegi | Sağlıklı ayçiçeği |
| 2 | hastalik_pas | Buğday yaprak pası (Puccinia) |
| 3 | hastalik_mildiyo | Ayçiçeği mildiyö (Plasmopara) |
| 4 | stres_kuraklik | Kuraklık stresi |
| 5 | stres_besin | Besin eksikliği |

## Eğitim (Google Colab)

```python
from ultralytics import YOLO
model = YOLO("yolov8n-cls.pt")
model.train(data="dataset/", epochs=50, imgsz=224, batch=32)
# best.pt → models/crop_health_best.pt
```
