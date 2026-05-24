# ÇP-2.5 — Anomali Yıl Validasyonu

**Yöntem:** Anomali yılı (|z|>1.5) train set'ten çıkarıldı, şampiyon model kalanla eğitildi, anomali yıllarında tahmin yapıldı.

## BUGDAY
- Şampiyon model: `Ridge(alpha=100.0)`
- Test edilen anomali satırı: **4**
- Anomali yıllarında MAE: **113.7 kg/da**
- Anomali yıllarında MAPE: **22.3%**

| İl | Yıl | Yön | z | Gerçek (kg/da) | Tahmin (kg/da) | Mutlak Hata |
|---|---|---|---|---|---|---|
| Edirne | 2021 | YÜKSEK | +1.64 | 474 | 387 | 87.1 |
| Kırklareli | 2021 | YÜKSEK | +1.98 | 460 | 390 | 70.0 |
| Tekirdağ | 2021 | YÜKSEK | +2.33 | 534 | 391 | 143.0 |
| Edirne | 2023 | YÜKSEK | +2.76 | 536 | 381 | 154.8 |

## AYCICEGI
- Şampiyon model: `Ridge(alpha=1.0)`
- Test edilen anomali satırı: **6**
- Anomali yıllarında MAE: **33.2 kg/da**
- Anomali yıllarında MAPE: **21.3%**

| İl | Yıl | Yön | z | Gerçek (kg/da) | Tahmin (kg/da) | Mutlak Hata |
|---|---|---|---|---|---|---|
| Kırklareli | 2019 | YÜKSEK | +1.58 | 285 | 261 | 24.1 |
| Tekirdağ | 2019 | YÜKSEK | +1.40 | 251 | 242 | 9.5 |
| Kırklareli | 2020 | YÜKSEK | +1.71 | 291 | 260 | 31.2 |
| Tekirdağ | 2020 | YÜKSEK | +1.32 | 248 | 240 | 7.6 |
| Tekirdağ | 2023 | DÜŞÜK | -2.12 | 115 | 180 | 64.9 |
| Edirne | 2024 | DÜŞÜK | -1.72 | 137 | 199 | 62.1 |

## Yorum

- **H3 (yanlış pozitif düşürme) için kanıt:** Anomali MAE'si calibration LOOCV MAE'sine yakın ise, model kuraklık/uç yıllarda da bozulmuyor — alert sisteminin yanlış pozitif oranını düşürmek için kullanılabilir.
- **Sınırlama:** Anomali test seti üç il × birkaç yıl ile küçüktür; tek bir uç yılın MAE'yi ciddi bozması mümkün.