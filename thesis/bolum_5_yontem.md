# Bölüm 5 — Yöntem

## 5.1 Baseline Modeller (Akademik Karşılaştırma Standardı)

Hiçbir gelişmiş model bu baseline'ları **anlamlı bir farkla** geçemediği
sürece deploy edilemez.  Bu, Kern et al. 2018'in iklim-VI çalışmalarında
ve genel agro-modelleme literatüründe yerleşmiş bir disiplindir.

### 5.1.1 4 Baseline Tanımı

| Kod | Yaklaşım | Açıklama |
|---|---|---|
| **B0** | Naive Climatology | `(ilçe, ürün)` 22-yıl ortalaması.  Skill-score referansı (RMSE_B0). |
| **B1** | Yıl Trendi | Per `(ilçe, ürün)` lineer regresyon `yield ~ year`. |
| **B2** | Persistence | `yield(t) = yield(t-1)`.  t-1 yoksa B0 fallback. |
| **B3** | Climate-Mean | Vekil regresyon: ekilen alan + yıl üzerinden (gerçek climate B3, Bölüm 6.1 Layer A'da test edildi). |

Tüm baseline'lar **LOYO (Leave-One-Year-Out)** ile in-place tahminlerini
ürettiler.  Random k-fold **kullanılmadı** çünkü gelecek yıl verisini
eğitimde görmek temporal leakage oluştururdu — Tao et al. 2023 standardına
göre random k-fold yasaktır.

### 5.1.2 Baseline LOYO Sonuçları

| Ürün | Model | R² | RMSE (kg/da) | MAE | Skill Score |
|---|---|---|---|---|---|
| Ayçiçeği | B0 | +0.033 | 50.0 | 40.4 | 0.000 |
| Ayçiçeği | B1 | +0.001 | 50.8 | 39.5 | -0.017 |
| Ayçiçeği | **B2 (kazanan)** | **+0.210** | 45.2 | 33.4 | **+0.096** |
| Ayçiçeği | B3 | +0.087 | 48.6 | 37.4 | +0.028 |
| Buğday | **B0 (kazanan)** | **+0.213** | 61.7 | 48.7 | 0.000 |
| Buğday | B1 | +0.208 | 61.9 | 49.0 | -0.003 |
| Buğday | B2 | -0.269 | 78.4 | 62.6 | -0.270 |
| Buğday | B3 | +0.126 | 65.1 | 50.0 | -0.054 |

**Akademik gözlemler:**

* **Buğday için B2 (persistence) -0.27 ile kötü** çünkü buğday verimi yıldan
  yıla yüksek varyans gösteriyor (kuraklık yıllarında ±150 kg/da swing).
  Climatology bu durumda daha güvenilir.
* **Ayçiçeği için B2 (persistence) +0.21 ile en iyi** — bu da iki yıl arası
  iklim sürekliliği + bölgesel adaptasyon sinyalinin güçlü olduğunu gösteriyor.

Bu farklılık, **ürün-spesifik kalibrasyon mimarisi** kullanılmasını destekler;
tek bir genel model her iki ürünü de iyi açıklayamaz.

## 5.2 3-Katmanlı Karşılaştırmalı Tasarım

Tao et al. 2023 LSTMatt çalışmasında transfer eden yerel modelin (R²=0.73)
genel DSSAT'tan (R²=0.16) anlamlı şekilde üstün olduğunu göstermişti.  Bu
çalışma, **bilgi türünün** (climate vs. NDVI vs. soil) marjinal katkısını
sırayla test eden 3 katmanlı mimari kullanır:

```
Katman A — Climate-only  (n_ilçe-yıl=1165, hedef R²≥0.35-0.40)
   ↓ +NDVI
Katman B — Climate + NDVI (n=eldeki NDVI satırı, hedef R²≥0.45-0.55)
   ↓ +Soil
Katman C — Multimodal Full (Katman B + statik toprak, hedef R²≥0.50-0.60)
```

Her katman **aynı 5 model yarışını** ve **3 CV şemasını** alır → kontrol grubu
mantıksal.

## 5.3 Model Seti

Küçük örneklem (Layer A n ≈ 589/crop, Layer B/C n ≈ 213/crop) +
nonlinearite + interpretasyon dengesi için 5 ana model + 1 ensemble
paralel yarıştırıldı.  Derin öğrenme **dışlandı**: Alsaber et al. 2025
n<1000 örneklemde DNN'nin overfitting'e açık olduğunu gösterir.

| Model | Hyperparam | Gerekçe | Layer C Şampiyon |
|---|---|---|---|
| PLS | n_components=3 | Düşük örneklem korelasyonlu features klasik | — |
| ElasticNet | α=1.0, l1_ratio=0.5 | L1+L2 düzenlileştirme dengesi | — |
| Random Forest | n=300, max_depth=5 | Nonlinearite + Pantazi 2016 ref. | — |
| XGBoost | n=200, max_depth=4, lr=0.05 | Gradient boosting standart | **Buğday LOYO** |
| **GPR** | Matern(ν=2.5) + WhiteKernel, normalize_y | **Belirsizlik kantifikasyonu** + small-n robust | **Ayçiçeği LOYO** |
| Stacking | RF+XGBoost+GPR → Ridge(α=1.0) meta | Ensemble (sadece LOYO) | — (overfit) |

Tree-based modeller (RF, XGBoost) ölçeklemeden bağımsız; PLS/ElasticNet/GPR
için `StandardScaler` LOYO içinde her fold için yeniden fit edildi (data
leakage'ı önler).

**Şampiyon model seçim kriteri**: En düşük LOYO RMSE.  Bu, operasyonel
"forecast" senaryosunu (gelecek yıl tahmin) yansıtan en gerçekçi metrik.

### 5.3.1 Stacking Ensemble Önemli Akademik Bulgu

Stacking ensemble her iki üründe de LOYO için tek-model GPR/XGBoost
şampiyonundan kötü performans verdi (Ayçiçeği: GPR R²=0.386 vs Stacking
R²=0.343).  Bu **küçük örneklem stacking riskinin** kanonik örneğidir:
meta-learner (Ridge) ~190 train fold ile overfit'ten kaçınamadı.  Akademik
sonuç: **n<300 için stacking önerilmez; tek-model + uygun düzenlileştirme
daha güvenli**.

## 5.4 Üç Paralel CV Şeması

Akademik altın standart için aynı veri üzerinde üç bağımsız CV:

### 5.4.1 Leave-One-Year-Out (LOYO)

`LeaveOneGroupOut(groups=year)` → 22 fold.  Cevapladığı soru: **"Modelim
gelecek yılı tahmin edebiliyor mu?"**  Operasyonel kullanım: sezon sonu
verim öngörüsü.

### 5.4.2 Leave-One-İlçe-Out (LOILO)

`LeaveOneGroupOut(groups=ilce_id)` → 29 fold.  Cevapladığı soru: **"Modelim
yeni bir ilçeye genelleyebiliyor mu?"**  Kullanım: Trakya dışı genişleme
(Türk-AIA vizyonu).

### 5.4.3 Spatiotemporal Block CV

5 yıl bloğu × 5 mekânsal cluster = **25 blok**.  Yıllar `np.linspace`
ile 5 bina; ilçeler lat/lon centroid'lerden KMeans(n_clusters=5) ile.
Tao et al. 2023 standardı.  Cevapladığı soru: **"Hem yeni yıl hem yeni
ilçe için ne kadar güvenilir?"**

Üç CV paralel raporlanır.  LOILO ≈ LOYO ise spatial generalization güçlü;
uzaksa spatial autocorrelation'a bağımlı (Bölüm 6.7 Moran's I ile teyit
edilir).

## 5.5 Performans Metrikleri

| Metrik | Formül | Yorum |
|---|---|---|
| R² | 1 − SS_res/SS_tot | Açıklanan varyans |
| RMSE | √mean((y − ŷ)²) | Mutlak hata, kg/da |
| MAE | mean(|y − ŷ|) | Outlier-robust hata |
| MAPE | mean(|y − ŷ|/y) × 100 | Göreceli %hata |
| **Skill Score** | 1 − RMSE_model / RMSE_B0 | Climatology baseline'a göre kazanım — pozitif zorunlu |
| Bias | mean(ŷ − y) | Sistematik sapma |

## 5.6 Hipotez Test Plana

| Hipotez | Test Yöntemi | Kabul Kriteri |
|---|---|---|
| **H1**: İlçe-bazlı (n=1165) il-bazlıyı (n=132) outperform eder | A/B karşılaştırma | ΔR² ≥ 0.15 |
| **H2**: NDVI eklenmesi climate-only baseline'ı outperform eder | Katman A vs B | ΔR² ≥ 0.10 |
| **H3**: Multimodal füzyon (Katman C) Katman B'yi outperform eder | LOYO karşılaştırma | ΔR² ≥ 0.05 |
| **H4**: Anomali yıllarda (2023, 2025) climate-mean'i geçer | Skill Score | SS > 0.30 |
| **H5**: Spatial CV (LOILO) ≈ LOYO | LOILO − LOYO | \|ΔR²\| < 0.15 |

## 5.7 Belirsizlik Kantifikasyonu

İki paralel yaklaşım (Bölüm 6.6'da raporlanır):

1. **GPR analitik posterior**: `mean ± 1.96 σ` (Bayesian inferansla doğal
   belirsizlik).
2. **Bootstrap (1000 resample)**: RF/XGBoost için empirical CI.

**PICP (Prediction Interval Coverage Probability)** = `mean(y_test ∈ [PI_l, PI_u])`.
Hedef: PICP ≈ 0.95.  PICP < 0.90 ise belirsizlik underestimated → temperature
scaling uygulanır.

## 5.8 Yorumlanabilirlik (XAI)

Lischeid et al. 2022 "ML alone is not enough" eleştirisine cevap olarak,
her şampiyon model için:

* **SHAP** global summary + per-instance waterfall (anomali vakaları için)
* **Permutation importance** — feature dropout etkisi
* **Partial Dependence Plots (PDP)** — top-5 özelliğin yield ile non-lineer
  ilişkisi
* **Local explanation** — 2023 Tekirdağ kuraklık vakası özelinde

## 5.9 Reproducibility

| Bileşen | Değer |
|---|---|
| Numpy seed | 42 |
| Sklearn random_state | 42 |
| LOYO/LOILO | sklearn.model_selection.LeaveOneGroupOut |
| Final model fit | All-data, train_date_utc + git_sha bundle metadata |
| Çevre snapshot | `requirements_freeze.txt` (haftalık) |
