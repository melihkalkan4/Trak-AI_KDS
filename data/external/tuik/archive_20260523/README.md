# TÜİK Arşivi — 2026-05-23

Bu klasör, ÇP-2.5 NDVI→Verim Kalibrasyon katmanının **ilk versiyon** TÜİK
verilerini içerir. Daha kaliteli/yeni veri geldiğinde üst klasöre yenisi
yerleştirilecektir.

## İçerik

| Dosya | Boyut | Açıklama |
|---|---|---|
| `tuik_trakya_yields_clean.csv` | 10 KB | 132 satır = 3 il × 2 ürün × 22 yıl (2004-2025), kg/dekar |
| `yield_stats_summary.csv` | 0.5 KB | 6 satır = (il, crop) için mean/std/cv/min/max |
| `yield_trends.csv` | 0.5 KB | Lineer trend slope + p-value |
| `anomaly_years.csv` | 1.4 KB | 24 satır = \|z\|>1.5 anomali yılları |
| `pilot_basari_baseline.csv` | 0.3 KB | TÜBİTAK %20/%30 hedef baseline |
| `rag_chunks_yield.json` | 5.1 KB | 6 RAG chunk (il × ürün) |
| `ndvi_yield_calibration_template.py` | 9 KB | Referans iskelet kod |
| `KULLANIM_REHBERI.md` | 7 KB | Veri seti dokümantasyonu |
| `yield_heatmap.png` | 167 KB | Görsel — yıl × il verim heatmap |
| `yield_trends.png` | 309 KB | Görsel — trend grafikleri |

## ÇP-2.5'i etkileyen artefaktlar

Bu veriler üzerinde eğitilmiş artefaktlar **olduğu gibi durur**:

- `models/cp25_calibration_{bugday,aycicegi}.pkl` — Ridge bundle'lar
- `reports/cp25_calibration_metrics.json` — LOOCV metrikleri (ayçiçeği R²=+0.646, buğday R²=-0.085)
- `reports/cp25_loocv_predictions_*.csv`
- `reports/cp25_anomaly_validation.md`
- `data/processed/calibration_{train_set,holdout}_*.csv` — sezonluk feature'lar
- `src/cp4_rag/faiss_index/` — +6 TÜİK chunk (idempotent ingestor varsa atlar)

## Yeni veri geldiğinde yapılacaklar

1. Yeni dosyaları `data/external/tuik/` köküne koyun (bu arşive **dokunmayın**)
2. Yeniden eğitim zinciri:
   ```bash
   python src/cp25_calibration/build_calibration_set.py
   python src/cp25_calibration/train_calibration.py
   python src/cp25_calibration/anomaly_validation.py
   python src/cp25_calibration/rag_ingest.py
   python tests/test_cp25_end_to_end.py
   ```
3. Eski FAISS chunk'larını temizlemek istenirse: `rag_ingest.py` idempotent
   olduğu için duplicate eklemez; eski chunk'ları silmek isterseniz
   `chunks_meta.json`'da `chunk_id_external` başlangıçlı `tuik_*` kayıtları
   manuel temizlenip FAISS yeniden build edilmeli.

## Akademik notlar

- Eski TÜİK verisi manuel tablo extraction'ından geldiği için citation
  zayıftı (kaynak: "TÜİK Bitkisel Üretim İstatistikleri" — sayfa/tablo
  referansı yok).
- Yeni veride **her satıra rapor URL + sayfa numarası** eklenirse
  reproducibility kuvvetlenir.
- Önceki veride 2025 değerleri "geçici" olarak işaretlenmişti — yeni
  veride finalize edildiyse 2025 hold-out test setine alınabilir.

---

*Arşiv tarihi: 2026-05-23. Sebep: kullanıcı daha kaliteli veri sağlayacak.*
