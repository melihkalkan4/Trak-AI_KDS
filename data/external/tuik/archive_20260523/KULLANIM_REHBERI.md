# TÜİK Verim Verisi — TRAK-AIA Entegrasyon Rehberi

> **Veri kaynağı:** TÜİK Bitkisel Üretim İstatistikleri (data.tuik.gov.tr)
> **Kapsam:** Edirne, Kırklareli, Tekirdağ — 2004–2025 (22 yıl)
> **Ürünler:** Buğday + Ayçiçeği (Yağlık)

---

## 📦 Paket içeriği

| Dosya | Açıklama |
|---|---|
| `tuik_trakya_yields_clean.csv` | Long-format, JOIN'e hazır tidy veri (132 satır) |
| `yield_stats_summary.csv` | Her (il, ürün) için 22-yıl istatistikleri |
| `yield_trends.csv` | Linear regression trend analizi + anlamlılık |
| `anomaly_years.csv` | Z-skor tabanlı anomali yılları (\|z\| > 1.3) |
| `pilot_basari_baseline.csv` | TÜBİTAK %20-30 hedefi için baseline tablosu |
| `rag_chunks_yield.json` | RAG sistemine yüklenmeye hazır Türkçe metin chunk'ları |
| `yield_trends.png` | 22-yıl çizgi grafiği + anomali işaretlemeleri |
| `yield_heatmap.png` | Yıl × İl ısı haritası |
| `ndvi_yield_calibration_template.py` | NDVI → kg/dekar kalibrasyon scripti |

---

## 🎯 5 katmanlı kullanım stratejisi

### Katman 1: NDVI → Yield Kalibrasyonu (en kritik)

**Sorun:** ÇP-2 modeliniz NDVI tahmin ediyor; çiftçi "kg/dekar" istiyor.

**Çözüm:** 22 yıllık (il × yıl) verim verisi ile sezonluk NDVI özellikleri arasında regresyon kur.

```bash
# Kendi master_feature_matrix.csv'inizle:
python ndvi_yield_calibration_template.py \
    --features data/master_feature_matrix.csv \
    --yields tuik_trakya_yields_clean.csv \
    --crop bugday
```

**Üretilen özellikler:**
- `ndvi_max` — sezon peak NDVI
- `ndvi_integral` — eğri altında alan (toplam fotosentez proxy'si)
- `ndvi_flowering` — çiçeklenme dönemi ortalaması (en kritik!)
- `ndvi_grain_fill` — tane dolum dönemi
- `greenness_days` — NDVI > 0.6 olan gün sayısı
- `gdd_cum_season` — sezonluk kümülatif GDD
- `tp_season_sum` — sezonluk yağış

**Validasyon yöntemi:** LOOCV (Leave-One-Out CV) — küçük örneklemde (n=66 max) en doğru yaklaşım.

**Beklenen performans:** Literatürde benzer çalışmalarda R² ~ 0.55–0.75 (Kern et al. 2018; Bhatia et al. 2022 — Trakya literatür kaynaklarınızda mevcut).

**Entegrasyon noktası:** ÇP-2 → `inference_cp2.py`. NDVI tahmininden sonra bu modeli çağır:

```python
# inference_cp2.py içine eklenecek
import pickle
cal = pickle.load(open('calibration_out/model_bugday_gbr.pkl', 'rb'))
seasonal_feats = extract_seasonal_features(predicted_ndvi_series, il, year)
yield_kg_da = cal['model'].predict([seasonal_feats])[0]
# LLM bağlamına gönder:
context['tahmini_verim_kg_da'] = round(yield_kg_da, 1)
context['lokal_22yil_ortalama'] = stats[(il, crop)]['mean_kg_da']
context['sapma_pct'] = 100 * (yield_kg_da - context['lokal_22yil_ortalama']) / context['lokal_22yil_ortalama']
```

---

### Katman 2: Anomali Yıl Validasyonu (H3 hipotezi)

`anomaly_years.csv` 24 anomali yıl içeriyor. Öne çıkanlar:

| Yıl | İl | Ürün | Verim | Sapma |
|---|---|---|---|---|
| **2023** | Tekirdağ | Ayçiçeği | 115 kg/da | **-2.12 σ** (kuraklık) |
| **2025** | Kırklareli | Ayçiçeği | 113 kg/da | **-2.18 σ** |
| **2007** | Tekirdağ | Ayçiçeği | 121 kg/da | -1.97 σ |
| 2024 | Edirne | Ayçiçeği | 137 kg/da | -1.72 σ |
| 2010 | Kırklareli | Buğday | 283 kg/da | -1.86 σ |

**Kullanım:**
1. Modelinizi bu yıllar için çalıştırın → kritik uyarı üretiyor mu?
2. Üretmiyorsa: ÇP-2 mimarisi kuraklık sinyalini kaçırıyor; ERA5 + NDVI özellik mühendisliğinde eksik var.
3. Üretiyorsa: H3 hipoteziniz (FP düşürme) için **kanıt verisi** elinizde — tez bölüm 5'e koyabilirsiniz.

---

### Katman 3: TÜBİTAK %20-30 Verim Hedefi Baseline

`pilot_basari_baseline.csv` her (il × ürün) için son 5 yıl ortalamasını + %20/%30 hedef değerlerini içeriyor.

**Örnek:**
```
il          urun_tr              baseline   +20%    +30%
Edirne      Ayçiçeği (Yağlık)    201.0      241.2   261.3
Tekirdağ    Buğday               426.6      511.9   554.6
```

Pilot çiftliğinizde mevsim sonu hasat ölçümleri → bu tabloyla karşılaştır → sistemin gerçek katkı miktarı dokümante edilir. **Tez Sonuç bölümü için ana metrik bu.**

---

### Katman 4: RAG Bilgi Tabanı

`rag_chunks_yield.json` 6 hazır Türkçe paragraf chunk içerir. Direkt FAISS'e yükleyebilirsiniz:

```python
from langchain.schema import Document
import json

chunks = json.load(open('rag_chunks_yield.json'))
docs = [Document(
    page_content=c['text'],
    metadata={'il': c['il'], 'urun': c['urun'], 'kaynak': c['kaynak']}
) for c in chunks]
vectorstore.add_documents(docs)
```

**Örnek soru/yanıt:**
- Soru: "Edirne'de buğday verimi son yıllarda nasıl?"
- Chunk: "Edirne ilinde buğday verimi 2004–2025 döneminde yıllık ortalama 384 kg/dekar... 22 yıllık seride en yüksek verim 2023 yılında 536 kg/dekar..."

---

### Katman 5: Sezon Başı Prior (Bayesyen Tahmin)

`yield_stats_summary.csv`'deki `mean_kg_da` ve `std_kg_da` değerleri, model çıktınız belirsiz olduğunda **öncel bilgi** olarak kullanılır:

```python
# Model güveni düşük (örn. veri eksik bir parsel)
if model_confidence < 0.5:
    # Prior dağılım: N(mean_il_crop, std_il_crop)
    prior_yield = stats[(il, crop)]['mean_kg_da']
    final_estimate = 0.5 * model_pred + 0.5 * prior_yield
```

---

## 📊 Trend bulgularının yorumu

```
Tekirdağ Buğday: +0.4 kg/da/yıl  (düz)        — istikrarlı bölge
Tekirdağ Ayçiçek: +0.2 kg/da/yıl  (düz)       — istikrarlı
Kırklareli Buğday: +3.1 kg/da/yıl (ANLAMLI ↑) — agronomik iyileşme var
Kırklareli Ayçiçek: +2.4 kg/da/yıl (düz)       — sınırda anlamlı
Edirne Buğday: +2.8 kg/da/yıl    (düz)        — sınırda
Edirne Ayçiçek: +1.3 kg/da/yıl    (düz)       — istikrarlı
```

**Yorum:** Genel olarak Trakya'da ayçiçeği verimi istatistiksel olarak yatay seyrediyor; buğdayda hafif artış var ama sadece Kırklareli'de istatistiksel olarak anlamlı (p < 0.05). Bu, son yıllarda **iklim stresinin verim artışı potansiyelini bastırdığını** gösteriyor — projenizin "kuraklık adaptasyonu" iddiasını güçlendirir.

---

## ⚠️ Sınırlamalar (tezde açıkça yazılmalı)

1. **Çözünürlük:** Veri il düzeyinde, parsel düzeyinde değil. Pilot parselinizin gerçek verimi il ortalamasından sapacaktır.
2. **Yıllık tek nokta:** Sezon içi dinamik yok — bu yüzden NDVI zaman serisinden öznitelik çıkarımı zorunlu.
3. **2025 verisi:** Sezon henüz bitmediği için bazı değerler geçici/tahmini olabilir; modellemede dikkat.
4. **Pilot ölçek farkı:** TÜİK il ortalaması = küçük çiftçi + büyük işletme + her tipi karışık. Sizin pilot çiftliğiniz "iyi yönetilen" işletme tipi olduğundan baseline'ın üstünde olması beklenir.

---

## 🔗 Sonraki adımlar

1. ✅ Bu paketi `data/external/tuik/` altına koyun
2. ⏭️ `ndvi_yield_calibration_template.py`'yi kendi `master_feature_matrix.csv`'inizle çalıştırın
3. ⏭️ Üretilen `.pkl` kalibrasyon modelini `inference_cp2.py`'ye bağlayın
4. ⏭️ `rag_chunks_yield.json`'u mevcut FAISS index'inize ekleyin
5. ⏭️ Pilot sezon sonunda gerçek hasatı `pilot_basari_baseline.csv` ile karşılaştırın
