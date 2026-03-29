"""
=====================================================================================
TRAK-AI KDS: GELİŞMİŞ ÇOK-MODALLI KEŞİFSEL VERİ ANALİZİ (EDA)
=====================================================================================
Oluşturulan nihai öznitelik matrisini (Feature Matrix) okuyarak; 
İklim, Su Stresi ve Bitki Gelişimi dinamiklerini tek bir görselde birleştirir.
=====================================================================================
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

print("="*60)
print("📊 TRAK-AI KDS: Gelişmiş EDA Grafiği Çiziliyor...")
print("="*60)

# =====================================================================================
# 1. AYARLAR VE VERİ YÜKLEME
# =====================================================================================
START_YEAR = 2023
END_YEAR = 2023

# main_etl_pipeline.py'nin ürettiği dosyayı bul (İsmi formata göre ayarlıyoruz)
file_path = f'data/processed/master_feature_matrix_{START_YEAR}_{END_YEAR}.csv'

# Eğer o isimde yoksa eski test dosyasını ara
if not os.path.exists(file_path):
    file_path = 'data/processed/master_feature_matrix_2017_2024.csv'
    
if not os.path.exists(file_path):
    # Eğer doğrudan ana dizine atıldıysa oradan al
    file_path = 'master_feature_matrix_2023.csv'

try:
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    print(f"✅ Veri başarıyla yüklendi: {file_path}")
except Exception as e:
    print(f"❌ Veri yükleme hatası: {e}\nLütfen önce main_etl_pipeline.py'yi çalıştırın.")
    exit()

# Çıktı klasörünü hazırla
plots_dir = 'docs/plots'
os.makedirs(plots_dir, exist_ok=True)

# =====================================================================================
# 2. GRAFİK OLUŞTURMA (2 ALT GRAFİK: ÜSTTE İNDEKSLER+SICAKLIK, ALTTA YAĞIŞ)
# =====================================================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)

# --- ÜST GRAFİK: NDVI, NDWI ve Sıcaklık İlişkisi ---
color_ndvi = 'tab:green'
color_ndwi = 'tab:cyan'

ax1.set_ylabel('Spektral İndeksler', color='black', fontsize=12, fontweight='bold')

# NDVI Çizgisi ve Noktaları
line_ndvi = ax1.plot(df['date'], df['NDVI_int'], color=color_ndvi, linewidth=2.5, label='NDVI (Bitki Gelişimi)')
scatter_ndvi = ax1.scatter(df.dropna(subset=['NDVI'])['date'], df.dropna(subset=['NDVI'])['NDVI'], 
                           color='darkgreen', s=50, zorder=5, label='Gerçek NDVI Ölçümü')

# NDWI Çizgisi ve Noktaları
line_ndwi = ax1.plot(df['date'], df['NDWI_int'], color=color_ndwi, linewidth=2.5, linestyle='--', label='NDWI (Su Stresi)')
scatter_ndwi = ax1.scatter(df.dropna(subset=['NDWI'])['date'], df.dropna(subset=['NDWI'])['NDWI'], 
                           color='darkblue', s=50, marker='x', zorder=5, label='Gerçek NDWI Ölçümü')

ax1.set_title(f'Trak-AI KDS: {START_YEAR} Yılı Çok-Modallı Veri Füzyonu (İklim, Bitki, Su)', fontsize=16, fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.5)

# İkinci Y Ekseni (Sıcaklık)
ax1b = ax1.twinx()
color_temp = 'tab:red'
ax1b.set_ylabel('Sıcaklık (°C)', color=color_temp, fontsize=12, fontweight='bold')

# Min/Max sıcaklık aralığını gölgeleme (Çok profesyonel bir veri bilimi dokunuşu)
ax1b.fill_between(df['date'], df['t2m_min'], df['t2m_max'], color=color_temp, alpha=0.15, label='Günlük Sıcaklık Aralığı (Min-Max)')
line_temp = ax1b.plot(df['date'], df['t2m_mean'], color=color_temp, linewidth=1.5, alpha=0.8, label='Ortalama Sıcaklık')

ax1b.tick_params(axis='y', labelcolor=color_temp)

# Üst Grafiğin Lejantlarını Birleştirme
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax1b.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', framealpha=0.9, fontsize=10)

# --- ALT GRAFİK: Yağış Rejimi ---
color_precip = 'tab:blue'
ax2.set_ylabel('Yağış (mm)', color=color_precip, fontsize=12, fontweight='bold')
ax2.bar(df['date'], df['tp_sum'], color=color_precip, alpha=0.7, label='Günlük Toplam Yağış')
ax2.tick_params(axis='y', labelcolor=color_precip)
ax2.set_xlabel('Tarih (Aylar)', fontsize=12, fontweight='bold')
ax2.grid(True, linestyle='--', alpha=0.5)

# X ekseni formatı (Ayları düzgün göstermek için)
ax2.xaxis.set_major_locator(mdates.MonthLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
plt.xticks(rotation=45)

plt.tight_layout()

# =====================================================================================
# 3. GRAFİĞİ KAYDETME
# =====================================================================================
output_image_path = os.path.join(plots_dir, f'advanced_eda_plot_{START_YEAR}_{END_YEAR}.png')
plt.savefig(output_image_path, dpi=300, bbox_inches='tight')

print(f"✅ Çizim tamamlandı! Grafik kaydedildi:")
print(f"   📂 {output_image_path}")
print("="*60)