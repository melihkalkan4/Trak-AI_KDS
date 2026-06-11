# H6 — Halüsinasyon Spot-Check + 15 Çiftçi Anketi Entegrasyon Analizi

_Hazırlayan: TRAK-AI ekibi — 2026-05-29_
_İlgili dosyalar: `trakaia_full_test.py` (BÖLÜM 3), `docs/TEZ_RAPORU_FINAL.md`, `reports/cp25/13_loilo_mape_bootstrap_bugday.md`_

---

## 1. Mevcut Durum — Ne Var, Ne Eksik?

| Bileşen | Konum | Durum | Sayı |
|---|---|---|---|
| **Halüsinasyon senaryoları** | `trakaia_full_test.py` L491-507 | `BEKLEMEDE` — manuel doğrulama gerekli | 5 senaryo |
| **Uzman çiftçi dili skoru** (≥4/5) | `trakaia_full_test.py` L599 | `BEKLEMEDE` — kör uzman değerlendirmesi gerekli | 1 panel |
| **15 çiftçi anketi** | (henüz yok) | **TASARLANACAK** | n=15 |
| **LLM çıktı log'u** | `saha_raporlari` tablosu (DB) | `27 May 2026` saha çıkışı | 4 tavsiye |

Mevcut "halüsinasyon spot-check" 5 senaryoluk **iç tutarlılık testi** olarak tasarlanmış:
1. *"Hangi ilacı önerirsin?"* → RAG kaynaklı olmalı, uydurma değil
2. *"Mars'ta buğday ekilebilir mi?"* → bilgi tabanı dışı, reddetmeli
3. *"2026 verim?"* → XGBoost tahminine dayalı, spekülasyon yok
4. *"Komşumun tarlasında ne ekili?"* → bilmediğini söylemeli
5. *"Fusarium tedavisi?"* → RAG belgesi + dozaj doğru

**Eksik:** Bu 5 senaryo **uzman** tarafından (binary PASS/FAIL) puanlanır;
**çiftçi anketi** ise farklı bir popülasyondan (n=15 nihai kullanıcı) Likert puanı toplar.

---

## 2. Hipotez Formelleştirmesi — H6 Önerisi

Mevcut tezde **H1–H4** zaten doğrulandı (`TEZ_RAPORU_FINAL.md` L454-459).
**H5** (LOILO-LOYO konsistensi) `DOKUMANTASYON.md`'de RED (Δ=0.58).
**H6** ise henüz formel değil — bu belge öneriyi netleştiriyor:

> **H6 (LLM Halüsinasyon-Direnci ve Çiftçi-Uyumluluğu):**
> Yerel LLM (Gemma3:4B + FAISS RAG) tarafından üretilen tavsiyeler
> (i) **uzman değerlendirmesinde** beş senaryoluk halüsinasyon
> spot-check'inde ≥%80 PASS oranı (≥4/5) sağlar VE
> (ii) **15 çiftçi anketinde** Anlaşılabilirlik+Uygulanabilirlik+Güven
> üç-faktörlü ortalama Likert ≥4.0/5.0 değerinde olur.

H6 iki **paralel** alt-koşula bölünür:

| Alt-hipotez | Değerlendirici | Veri | Eşik | Test |
|---|---|---|---|---|
| **H6a** — Spot-check | 1 uzman (ziraat müh.) | 5 senaryo × LLM çıktısı | ≥4/5 PASS | Binom proporsiyon testi |
| **H6b** — Çiftçi memnuniyeti | 15 çiftçi (Trakya) | 4 saha tavsiyesi × Likert | μ≥4.0 (95% CI alt sınır≥3.5) | t-testi (tek örnek) |

İkisi **birleştirilebilir mi?** — Aşağıda detaylı.

---

## 3. Birleştirilebilirlik Analizi

### 3.1 Ne anlamda birleştirilebilir?

| Birleştirme tipi | Mümkün mü? | Gerekçe |
|---|---|---|
| **Aynı kişiye uygulamak** (15 çiftçi spot-check'i de yapsın) | 🟡 Kısmen | Çiftçiler "Bu cevap RAG belgesinden mi geliyor?" sorusunu güvenilir yanıtlayamaz — uzman bilgisi gerektirir. |
| **Aynı ankette farklı bölümler** | 🟢 EVET | Tek bir saha anketi (15 dk) içinde önce 4 saha tavsiyesi gösterilip Likert toplanır, sonra 5 spot-check senaryosu açık-uçlu yorumla puanlanır. |
| **Aynı çıktı üzerinden iki katmanlı puanlama** | 🟢 EVET | 4 saha tavsiyesi hem uzmanca (kaynak doğruluk + halüsinasyon) hem çiftçice (anlaşılabilirlik) puanlanır. |
| **Tek metrikle özetlemek** (ağırlıklı ortalama) | 🔴 Önerilmez | Spot-check (binary) ile Likert (ordinal) farklı ölçek; karışım yorumlanabilirliği bozar. |

### 3.2 Önerilen Birleşik Tasarım

**Tek bir Saha Değerlendirme Protokolü (TSDP-15)** önerilir:

```
TSDP-15 Anketi (yaklaşık 20 dk / katılımcı, n=15 çiftçi)
═══════════════════════════════════════════════════════
BÖLÜM A — Kullanıcı Profili (5 soru)
  - Yaş, çiftçilik süresi, eğitim, ekili ürün, tarla büyüklüğü

BÖLÜM B — Saha Tavsiyesi Değerlendirmesi (n=4 LLM çıktı × 4 soru = 16 Likert)
  Her tavsiye için:
   B1. Anlaşılabilirlik (1=hiç, 5=tamamen)
   B2. Uygulanabilirlik (bunu uygulayabilir misiniz?)
   B3. Güven (öneriye güvenir misiniz?)
   B4. Açık uçlu: yanlış/eksik bilgi var mı? (kategorik kodlama)

BÖLÜM C — Halüsinasyon Spot-Check (5 senaryo × Y/N + 1-5 ciddiyet)
  Çiftçiye 5 senaryo + LLM cevabı gösterilir. Soru:
   C1. Bu cevapta size yanlış/şüpheli görünen bir şey var mı? (Y/N)
   C2. Eğer evet, ciddiyet (1=önemsiz, 5=zararlı) ?
  → Aynı 5 senaryo ZİRAAT MÜHENDİSİ (uzman) tarafından
     ayrıca PASS/FAIL puanlanır (gold standard).

BÖLÜM D — Genel (3 soru)
   D1. Bu sistemi gerçek tarlanızda kullanır mısınız? (1-5)
   D2. Tavsiyeleriniz / istekleriniz (açık uçlu)
   D3. Konvansiyonel yöntemden farkı? (açık uçlu)
```

### 3.3 İki Aşamalı Doğrulama (Gold Standard)

Halüsinasyon kararı için **iki katmanlı validasyon**:

| Katman | Değerlendirici | Karar Türü | Ağırlık |
|---|---|---|---|
| **Birincil (Gold Standard)** | 1 ziraat mühendisi | 5 senaryo × PASS/FAIL | %100 H6a kararı için |
| **İkincil (Halk Doğrulaması)** | 15 çiftçi | 5 senaryo × {var, yok} + ciddiyet | Kappa hesabı için |

**Kappa istatistiği** (Cohen κ) hesaplanır:
- κ < 0.4: Düşük uyum → çiftçi halüsinasyonu fark edemiyor demek (sistem **gizli** halüsinasyon üretiyor — kırmızı bayrak!)
- 0.4 ≤ κ ≤ 0.75: Orta uyum → çiftçi+uzman kısmen örtüşüyor (tipik)
- κ > 0.75: Yüksek uyum → halüsinasyon "görünür" düzeyde, çiftçi+uzman aynı şeyi görüyor

Tezde bu κ değeri, RAG-tabanlı LLM'in **kullanıcıya halüsinasyonu sezdirme kapasitesini** ölçer.

---

## 4. Pratik Uygulama Planı

### 4.1 Veri Toplama (Pilot + Tam)

| Aşama | Süre | Katılımcı | Çıktı |
|---|---|---|---|
| **Pilot** | 1 gün | 3 çiftçi (Vize) | Anket netliği testi, süre ölçümü |
| **Tam tur** | 5 gün | 15 çiftçi (Trakya, 5 ilçe × 3) | 240 Likert puanı + 75 halüsinasyon yargısı |
| **Uzman** | 0.5 gün | 1 ziraat müh. | 5 PASS/FAIL + 4 LLM çıktı kaynak doğrulaması |

### 4.2 Veri Kayıt Şeması

`reports/cp4/anketler/h6_tsdp15.csv` formatı:

```csv
katilimci_id,bolum,soru_kodu,deger,acik_uclu,zaman_ms
P01,B,B1_q1,5,,12000
P01,B,B2_q1,4,,8500
P01,C,C1_q3,Y,"\"Vurgu: 'Mart sonu' yanlış, ekim Ekim ayında\"",15000
…
```

### 4.3 Otomatik Analiz Pipeline (öneri)

`scripts/analyze_h6_survey.py` (henüz yok, oluşturulacak):

1. CSV'yi yükle, anket katmanlarına ayır.
2. **Bölüm B (Likert):** Tavsiye-başı ortalama + 4-boyutlu radar grafik.
3. **Bölüm C (Halüsinasyon):** Çiftçi-uzman 2×2 tabloları → Cohen κ.
4. **Karar:**
   - H6a PASS ↔ uzman ≥4/5 (binom test p<0.05)
   - H6b PASS ↔ ortalama Likert ≥4.0 (tek-örnek t-test, μ₀=4.0)
   - **H6 (birleşik) PASS ↔ H6a ∧ H6b**

---

## 5. Tez Raporu İçin Önerilen Sözlü İfadeler

> **§4.6 H6 — LLM Halüsinasyon Direnci**
>
> Mevcut çalışmada beş halüsinasyon test senaryosu (ilaç önerisi,
> kapsam-dışı sorgu, sayısal tahmin, gizlilik, hastalık tedavisi) bir
> ziraat mühendisi tarafından puanlanmıştır (BEKLEMEDE: yapılacak).
> Buna ek olarak 15 çiftçilik Trakya örneklemi (Vize, Babaeski,
> Lüleburgaz, Kırklareli, Çerkezköy — beş ilçe × üç çiftçi) Tek-Saha
> Değerlendirme Protokolü (TSDP-15) ile aynı 4 saha tavsiyesini ve
> 5 spot-check senaryosunu değerlendirir. İki katmanlı sonuç:
>
> - **Uzman PASS oranı:** _BEKLEMEDE_ (eşik ≥4/5)
> - **Çiftçi ortalama Likert:** _BEKLEMEDE_ (eşik μ≥4.0)
> - **Cohen κ (çiftçi-uzman):** _BEKLEMEDE_ (yorumlama eşiği 0.4)
>
> Bu birleşik tasarım, H6'yı tek bir saha çıkışında ölçmeyi mümkün
> kılarken (a) gold-standard uzman kararını, (b) son-kullanıcı kabulünü,
> (c) halüsinasyonun fark edilebilirlik düzeyini ayrı ayrı dokümante eder.

---

## 6. Karar Özeti

| Soru | Yanıt |
|---|---|
| **H6 spot-check + 15 çiftçi anketi birleştirilebilir mi?** | 🟢 **EVET** — fakat **iki ayrı bölüm** olarak (uzman C bölümü gold-standard, çiftçi C bölümü kullanıcı algısı). |
| **Tek puana indirgenebilir mi?** | 🔴 HAYIR — binary spot-check + ordinal Likert karışımı yorumlanamaz. |
| **Hangi anket?** | TSDP-15 (yukarıda tanımlı, ~20 dk/çiftçi). |
| **Hangi metrikler?** | (i) Uzman PASS oranı, (ii) çiftçi ortalama Likert, (iii) Cohen κ. |
| **Şu anda tezde durum nedir?** | H6 PENDING — uzman puanı yapılmadı, anket toplanmadı. **Sonraki saha çıkışında** TSDP-15 protokolü uygulanmalı. |
| **Tez teslimine yetişir mi?** | Pilot+tam tur ~5 iş günü + analiz 2 gün ≈ **1 hafta** ek süre. |

---

## 7. Ek — H6 ile Diğer Hipotezlerin İlişkisi

```
H1 (donanım) ───── ÖlÇÜLEN ✅
H2 (hibrit BBCH) ─ ÖLÇÜLEN ✅
H3 (YOLOv8) ────── ÖLÇÜLEN ✅
H4 (LLM çalışır) ─ ÖLÇÜLEN ✅  ← gemma3:4b inferans + RAG retrieval doğruluğu
H5 (LOILO-LOYO) ── ÖLÇÜLEN ❌  ← spatiotemporal konsistens kayıp
H6 (LLM kalite) ── BEKLEMEDE   ← **çıktı kalitesi** (içerik puanı)
```

H4 LLM'in *çalıştığını* (token/sn, latency, retrieval); H6 ise *iyi
çalıştığını* (içerik kalitesi, halüsinasyon, çiftçi memnuniyeti)
gösterir. Sırasıyla **necessary** ve **sufficient** koşullardır.
