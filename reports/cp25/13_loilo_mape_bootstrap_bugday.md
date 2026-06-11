# ÇP-2.5 — Görev 13: LOILO MAPE Bootstrap %95 Güven Aralığı (bugday)

_Üretildi: 2026-05-29T12:39:05.282679+00:00_  |  Layer C  |  Model: **XGBoost**  |  CV: **LOILO**

## Yöntem

- Veri: `data/processed/calibration_features_layerC.csv` → bugday alt-kümesi (n=213, 28 ilçe).
- `LeaveOneGroupOut(groups=ilce_id)` ile her ilçe için dışarıda bırakılarak XGBoost eğitildi.
- Hiperparametreler: `n_estimators=200, max_depth=4, lr=0.05, seed=42` (07_layer_c_full.py birebir).
- Bootstrap: 1000 yeniden örnekleme (with replacement), tohum=42.
- MAPE eşik (literatür/saha kriteri): **≤%10**.

## Sonuçlar

| Metrik | Değer |
|---|---|
| Nokta MAPE | **%10.561** |
| Bootstrap ortalaması | %10.572 |
| Bootstrap medyanı | %10.561 |
| %95 GA alt sınır (2.5p) | **%9.138** |
| %95 GA üst sınır (97.5p) | **%12.099** |
| Bootstrap std | %0.783 |
| %10 eşiğin altındaki resample oranı | %24.3 |
| n_obs | 213 |
| n_bootstraps | 1000 |

## Yorum — "≤%10 Hedefe Yakınlık" İddiası

- **Nokta tahmin** (10.561%) hedefin üstünde.
- **%95 GA üst sınırı** %12.099 → hedef **dışarıda** (üst sınır > %10).
- Nokta tahmin ile %10 hedefi arasındaki mesafe: **-0.561 puan** (negatif değer hedefin üstünde demek).
- Bootstrap resample'larının **%24.3**'i hedefi tutturuyor.

### Hipotez İfadesi

> **H_LOILO≤10:** Layer C XGBoost LOILO MAPE bugday için ≤%10.
> **Karar:** KORUMA ALTINDA (yakın)

## Şampiyon Modelin (Pre-bootstrap) Layer C LOILO Tablosu

Karşılaştırma için 07_layer_c_results.csv'deki bugday LOILO satırları (n=213) — bu
tablo Layer C orijinal raporundan birebir alınmıştır:

| Model | R² | RMSE | MAPE % |
|---|---|---|---|
| pls | +0.210 | 62.6 | 12.415 |
| elastic_net | +0.180 | 63.8 | 12.941 |
| random_forest | +0.392 | 54.9 | 11.458 |
| **xgboost** | **+0.427** | **53.3** | **10.561** |
| gpr | +0.342 | 57.2 | 11.753 |

Bootstrap analizi yalnızca **xgboost** üzerinde yapıldı; çünkü 07_layer_c_results.csv'de
şampiyon (en düşük RMSE/MAPE) olarak listelenen LOILO modeli odur.
