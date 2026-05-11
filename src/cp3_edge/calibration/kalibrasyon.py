import numpy as np
import matplotlib.pyplot as plt

# ─── KALİBRASYON VERİLERİ ───────────────────────────────────────
# Sensör gelince bu değerleri gerçek ölçümlerle güncelle!
# adc_degerler : ESP32'den okunan ham ADC değeri (0-4095)
# nem_gercek   : Tartarak hesaplanan gerçek nem %
#                nem% = (W_yasli - W_kuru) / W_kuru * 100

adc_degerler = np.array([
    2850,  # Kuru hava ~ 0%
    2650,  # Çok kuru toprak ~ 5%
    2400,  # Kuru toprak ~ 15%
    2150,  # Az nemli ~ 25%
    1900,  # Orta nem ~ 35%
    1650,  # Nemli ~ 50%
    1400,  # Islak ~ 65%
    1200,  # Çok ıslak ~ 80%
    1050,  # Suya yakın ~ 95%
    980,   # Suya batırılmış ~ 100%
])

nem_gercek = np.array([
    0.0, 5.0, 15.0, 25.0, 35.0,
    50.0, 65.0, 80.0, 95.0, 100.0,
])

# ─── POLİNOM REGRESYON (2. derece) ──────────────────────────────
katsayilar = np.polyfit(adc_degerler, nem_gercek, 2)
a, b, c = katsayilar

print("=" * 50)
print("KALİBRASYON SONUÇLARI")
print("=" * 50)
print(f"nem% = {a:.8f} * ADC² + {b:.6f} * ADC + {c:.4f}")
print()
print("config.h için kopyala:")
print(f"#define CAL_A   {a:.8f}f")
print(f"#define CAL_B   {b:.6f}f")
print(f"#define CAL_C   {c:.4f}f")

# ─── DOĞRULUK METRİKLERİ ────────────────────────────────────────
nem_tahmin = np.polyval(katsayilar, adc_degerler)
hatalar    = nem_gercek - nem_tahmin
rmse       = np.sqrt(np.mean(hatalar**2))
ss_res     = np.sum(hatalar**2)
ss_tot     = np.sum((nem_gercek - np.mean(nem_gercek))**2)
r2         = 1 - (ss_res / ss_tot)

print()
print("DOĞRULUK METRİKLERİ")
print("-" * 30)
print(f"RMSE : %{rmse:.3f}  (hedef: ≤ %1.02)")
print(f"R²   : {r2:.4f}    (hedef: ≥ 0.89)")
print()

if rmse <= 1.02 and r2 >= 0.89:
    print("✓ KALİBRASYON BAŞARILI!")
else:
    print("✗ Daha fazla veri noktası ekle.")

# ─── KARŞILAŞTIRMA TABLOSU ───────────────────────────────────────
print()
print(f"{'ADC':>6} | {'Gerçek%':>8} | {'Tahmin%':>8} | {'Hata':>6}")
print("-" * 40)
for i in range(len(adc_degerler)):
    print(f"{adc_degerler[i]:>6} | {nem_gercek[i]:>8.1f} | "
          f"{nem_tahmin[i]:>8.1f} | {hatalar[i]:>+6.2f}")

# ─── GRAFİK ─────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('Trak-AI SEN0193 Kalibrasyon Analizi', fontsize=14, fontweight='bold')

adc_range = np.linspace(min(adc_degerler)-50, max(adc_degerler)+50, 500)
nem_range = np.clip(np.polyval(katsayilar, adc_range), 0, 100)

ax1.scatter(adc_degerler, nem_gercek, color='red', s=80, zorder=5, label='Ölçüm noktaları')
ax1.plot(adc_range, nem_range, 'b-', linewidth=2, label=f'Polinom fit\nRMSE=%{rmse:.3f} R²={r2:.4f}')
ax1.set_xlabel('ADC Ham Değeri')
ax1.set_ylabel('Toprak Nemi (%)')
ax1.set_title('Kalibrasyon Eğrisi')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2.bar(range(len(hatalar)), hatalar,
        color=['green' if abs(h) < 1.02 else 'red' for h in hatalar])
ax2.axhline(y=1.02,  color='orange', linestyle='--', label='+Eşik')
ax2.axhline(y=-1.02, color='orange', linestyle='--', label='-Eşik')
ax2.set_xlabel('Ölçüm Noktası')
ax2.set_ylabel('Hata (%)')
ax2.set_title('Hata Dağılımı')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('kalibrasyon_grafik.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nGrafik kaydedildi: kalibrasyon_grafik.png")