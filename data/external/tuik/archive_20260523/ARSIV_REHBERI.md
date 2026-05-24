# Arşivleme Rehberi — TUIK v1 → v2 Geçişi

Yeni `tuik/` klasörü (ilçe bazlı, v2) eski il-bazlı dosyaların yerine geçer.
Eskileri silme — **arşivle**. İleride veri kaynağı karşılaştırması veya 
tez metni yazımı için referans değeri var.

## Önerilen klasör yapısı

```
proje_kok/
└── data/
    └── external/
        ├── tuik/                          # ✅ YENİ — aktif kullanım
        │   ├── tuik_ilce_yields_clean.csv
        │   ├── tuik_ilce_yields_full_referans.csv
        │   ├── ilce_coords.csv
        │   ├── ilce_yield_stats.csv
        │   ├── ilce_yield_trends.csv
        │   ├── ilce_anomaly_years.csv
        │   ├── ilce_pilot_baseline.csv
        │   ├── rag_chunks_ilce.json
        │   ├── ilce_yield_map.png
        │   ├── ilce_yield_heatmap.png
        │   └── MANIFEST.json
        │
        └── _archive/
            └── tuik_v1_il_bazli/           # 🗄️ ARŞİV — eski v1
                ├── tuik_trakya_yields_clean.csv      (n=132, il bazlı)
                ├── yield_stats_summary.csv
                ├── yield_trends.csv
                ├── anomaly_years.csv
                ├── pilot_basari_baseline.csv
                ├── rag_chunks_yield.json
                ├── yield_trends.png
                ├── yield_heatmap.png
                └── KULLANIM_REHBERI.md
```

## Arşive taşınacak dosyalar

| Eski dosya | Yeni karşılığı | Not |
|---|---|---|
| `tuik_trakya_yields_clean.csv` | `tuik/tuik_ilce_yields_clean.csv` | 132 satır → 1165 satır |
| `yield_stats_summary.csv` | `tuik/ilce_yield_stats.csv` | il bazlı → ilçe bazlı |
| `yield_trends.csv` | `tuik/ilce_yield_trends.csv` | 6 satır → 57 satır |
| `anomaly_years.csv` | `tuik/ilce_anomaly_years.csv` | 24 → 147 anomali |
| `pilot_basari_baseline.csv` | `tuik/ilce_pilot_baseline.csv` | 6 → 55 satır |
| `rag_chunks_yield.json` | `tuik/rag_chunks_ilce.json` | 6 → 57 chunk |
| `yield_trends.png` | `tuik/ilce_yield_heatmap.png` + `ilce_yield_map.png` | |
| `KULLANIM_REHBERI.md` | `tuik/MANIFEST.json` + bu rehber | |

## Aktif tutulacak (arşivleme dışı) dosyalar

Bu dosyalar **versiyon bağımsız** — arşivleme. Olduğu yerde kalsın:

- `ndvi_yield_calibration_template.py` — kalibrasyon scripti şablonu
- `CLAUDE_CODE_PROMPT.md` — orijinal ÇP-2.5 prompt'u (referans)
- `WHEAT_FIX_CLAUDE_CODE_PROMPT.md` — v1 model fix denemesi (referans)
- `WHEAT_FIX_v2_ILCE_PROMPT.md` — ✅ **şu an aktif olan prompt**

## Bash komutları (Linux/macOS)

Eğer proje köküne CD yaptıysan ve eski dosyalar `data/external/tuik/` altındaysa:

```bash
# 1. Arşiv klasörü oluştur
mkdir -p data/external/_archive/tuik_v1_il_bazli

# 2. Eski v1 dosyalarını taşı
cd data/external/tuik/
mv tuik_trakya_yields_clean.csv ../_archive/tuik_v1_il_bazli/
mv yield_stats_summary.csv      ../_archive/tuik_v1_il_bazli/
mv yield_trends.csv             ../_archive/tuik_v1_il_bazli/
mv anomaly_years.csv            ../_archive/tuik_v1_il_bazli/
mv pilot_basari_baseline.csv    ../_archive/tuik_v1_il_bazli/
mv rag_chunks_yield.json        ../_archive/tuik_v1_il_bazli/
mv yield_trends.png             ../_archive/tuik_v1_il_bazli/
mv yield_heatmap.png            ../_archive/tuik_v1_il_bazli/

# 3. Yeni v2 dosyalarını buraya kopyala (bu paketin içeriği)
# (claude.ai'dan indirdiğin tuik/ klasörünü buraya yerleştir)
```

## Windows PowerShell

```powershell
$arch = "data\external\_archive\tuik_v1_il_bazli"
New-Item -ItemType Directory -Force -Path $arch

Get-ChildItem data\external\tuik\ -File | 
    Where-Object { $_.Name -in @(
        "tuik_trakya_yields_clean.csv",
        "yield_stats_summary.csv",
        "yield_trends.csv",
        "anomaly_years.csv",
        "pilot_basari_baseline.csv",
        "rag_chunks_yield.json",
        "yield_trends.png",
        "yield_heatmap.png"
    )} | 
    Move-Item -Destination $arch
```

## Git workflow önerisi

```bash
git checkout -b feat/cp25-ilce-data
git add data/external/tuik/                          # Yeni v2
git add data/external/_archive/tuik_v1_il_bazli/    # Eski v1
git commit -m "feat(cp25): TÜİK ilçe bazlı verim verisine geçiş

- n=21 → n=220 (buğday 2017-2024)
- n=24 → n=216 (ayçiçeği 2017-2024)
- ERA5-only modeli için n=589 (2004-2025)
- Eski il bazlı v1 _archive/ altına taşındı"
```

## Kod tarafında güncellenmesi gerekenler

Eski il-bazlı dosya yollarını referans alan scriptler varsa:

```python
# ESKİ
yields = pd.read_csv('data/external/tuik/tuik_trakya_yields_clean.csv')

# YENİ
yields = pd.read_csv('data/external/tuik/tuik_ilce_yields_clean.csv')

# JOIN anahtarı değişiyor:
# ESKİ: merge(on=['il', 'year'])
# YENİ: merge(on=['ilce_id', 'year'])  # ya da fallback olarak ['il', 'year']
```

`inference_cp2.py`, `train_models_cp2.py` ve `ndvi_yield_calibration_template.py` 
içinde varsa bu güncelleme yapılmalı. Claude Code'a `WHEAT_FIX_v2_ILCE_PROMPT.md`'yi
verince bunu otomatik yapacak.

## Tezde referans

Tez metninde **iki sürüm de** referansta yer alabilir:

> "TÜİK Bitkisel Üretim İstatistikleri (data.tuik.gov.tr) iki granülariteyle 
> derlenmiştir: (i) il bazlı 2004–2025 dönemi (Edirne, Kırklareli, Tekirdağ; 
> n=132); (ii) ilçe bazlı 2004–2025 dönemi (29 Trakya ilçesi; n=1165). 
> Kalibrasyon modeli ilçe bazlı veriyle eğitilmiş, il bazlı veri ise 
> doğrulama ve karşılaştırma amaçlı kullanılmıştır."
