# TRAK-AI KDS — Kapsamlı Test Raporu

**Tarih:** 2026-05-21 20:55

**Toplam Test:** 22

| Durum | Sayı | Oran |
|---|---|---|
| ✅ Başarılı | 18 | %82 |
| ⏳ Beklemede | 2 | %9 |
| ⚠️ Kısmi/Uyarı | 2 | %9 |
| ❌ Başarısız | 0 | %0 |

## Detaylı Sonuçlar

| Modül | Test | Durum | Detay |
|---|---|---|---|
| ÇP-2 | Buğday R² hedefi (>0.75) | ✅ BAŞARILI | LSTM: R²=0.7520 |
| ÇP-2 | Ayçiçeği R² hedefi (>0.75) | ✅ BAŞARILI | LSTM: R²=0.7957 |
| ÇP-2 | Buğday Verim MAPE (<10%) | ✅ BAŞARILI | MAPE=5.1% |
| ÇP-2 | Ayçiçeği Verim MAPE (<10%) | ✅ BAŞARILI | MAPE=7.3% |
| YOLOv8 | Genel Top-1 doğruluk (≥%90) | ✅ BAŞARILI | %94.9 |
| YOLOv8 | sağlıklı_buğday doğruluk | ✅ BAŞARILI | %98.0 |
| YOLOv8 | sağlıklı_ayçiçeği doğruluk | ✅ BAŞARILI | %100.0 |
| YOLOv8 | hastalık_pas doğruluk | ✅ BAŞARILI | %91.0 |
| YOLOv8 | hastalık_mildiyö doğruluk | ✅ BAŞARILI | %99.1 |
| YOLOv8 | stres_kuraklık overfit kontrolü | ⚠️ UYARI | %100.0 — 360 görüntü, veri artırma gerekli |
| YOLOv8 | stres_besin doğruluk | ✅ BAŞARILI | %85.2 |
| ÇP-4 RAG | Bilgi tabanı boyutu | ✅ BAŞARILI | 17,059 chunk / 64 belge |
| ÇP-4 RAG | Uçtan uca gecikme (<120sn) | ✅ BAŞARILI | 27.1 sn (Gemma-3-4B, CPU) |
| ÇP-4 RAG | Retrieval doğruluğu (10/10) | ✅ BAŞARILI | %100 |
| ÇP-4 RAG | Halüsinasyon testi (5 senaryo) | ⏳ BEKLEMEDE | Manuel doğrulama gerekli |
| ÇP-4 RAG | Çiftçi dili uyumu (uzman ≥4/5) | ⏳ BEKLEMEDE | Kör uzman değerlendirmesi gerekli |
| Agro | Ekim penceresi doğruluğu (5/6) | ⚠️ KISMI | 5/6 test geçti |
| Agro | Sulama karar doğruluğu (4/4) | ✅ BAŞARILI | 4/4 |
| Agro | Anomali tespit doğruluğu (6/6) | ✅ BAŞARILI | 6/6 |
| Mimari | Edge-Fog-Cloud diyagramı | ✅ BAŞARILI | PNG oluşturuldu |
| Mimari | TVC diyagramı | ✅ BAŞARILI | PNG oluşturuldu |
| Donanım | Hazırlık durumu (7/12 hazır) | ✅ BAŞARILI | 7 hazır, 5 beklemede/eksik |

## Üretilen Görseller

- `charts\agro_fenolojik_takvim.png` — Agro Fenolojik Takvim
- `charts\cp2_model_karsilastirma_r2.png` — Cp2 Model Karsilastirma R2
- `charts\cp2_model_mae_rmse.png` — Cp2 Model Mae Rmse
- `charts\cp2_ndvi_tahmin_vs_gercek.png` — Cp2 Ndvi Tahmin Vs Gercek
- `charts\cp2_sampiyon_radar.png` — Cp2 Sampiyon Radar
- `charts\cp2_verim_shap.png` — Cp2 Verim Shap
- `charts\donanim_hazirlik_durumu.png` — Donanim Hazirlik Durumu
- `charts\final_test_ozet.png` — Final Test Ozet
- `charts\rag_bilgi_tabani_istatistik.png` — Rag Bilgi Tabani Istatistik
- `charts\rag_performans_gauge.png` — Rag Performans Gauge
- `charts\yolo_confusion_matrix.png` — Yolo Confusion Matrix
- `charts\yolo_sinif_dogruluk.png` — Yolo Sinif Dogruluk
- `charts\yolo_veri_seti_dagilim.png` — Yolo Veri Seti Dagilim
- `diagrams\mimari_edge_fog_cloud.png` — Mimari Edge Fog Cloud
- `diagrams\tvc_deger_zinciri.png` — Tvc Deger Zinciri

## Bekleyen İşler (Manuel)

1. **Halüsinasyon testi:** 5 senaryo hazır, Ollama çalıştırılarak test edilmeli
2. **Agronomik uzman değerlendirmesi:** Kör uzman testi (hedef ≥4/5)
3. **Dashboard UI testi:** 6 test sorusu Streamlit'te denenecek
4. **config.h WiFi bilgisi:** Telefon hotspot adı/şifre yazılacak
5. **HC-SR04 sipariş iptali:** Çift siparişten biri iptal edilecek
6. **stres_kuraklık overfit:** Veri artırma ile yeniden eğitim düşünülmeli
