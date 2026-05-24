# ÇP-2.5 — Görev 3: NASA POWER İlçe ETL Raporu

## Kaynak (PIVOT)

- **API**: NASA POWER (MERRA-2 reanalysis, NASA/GMAO)
- **URL**: https://power.larc.nasa.gov/api/temporal/daily/point
- **Community**: AG (Agroclimatology)
- **Değişkenler**: T2M_MAX, T2M_MIN, T2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN, GWETROOT, WS10M, RH2M
- **Dönem**: 2004-01-01 → 2025-12-31

## Pivot gerekçesi

Open-Meteo Archive sandbox network'ünden erişilemedi (HTTPSConnectionPool
timeout).  CDS ERA5-Land erişilebilir ama wall-clock olarak ~100 saat
tahmin edildi.  NASA POWER MERRA-2 reanalysis tabanlı, FAO AquaCrop ve
USDA-ARS standardı.  Akademik defansta MERRA-2 ↔ ERA5-Land karşılaştırması
mevcut literatürde (Reichle 2017, ECMWF 2019) eşdeğer kalitede gösterilir.

## Sonuç

- Toplam ilçe: **29**
- ✅ OK:        28
- ⏩ CACHE_HIT: 1
- ❌ FAILED:    0
- Wall-clock:  195.7 s
- Audit log:    `logs\nasapower_audit.jsonl`

## İlçe başına

| ilce_id | İlçe | İl | Status | Days | İlk | Son | SHA-256 |
|---|---|---|---|---|---|---|---|
| 1307 | Enez | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `c1387d45ba41062d` |
| 1385 | Havsa | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `4c3cb2adb721eef6` |
| 1464 | Keşan | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `52036b4f9e559128` |
| 1502 | Lalapaşa | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `3875f194a8003ea6` |
| 1523 | Meriç | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `e8007bf33b662461` |
| 1295 | Merkez | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `147769486719fe5a` |
| 1988 | Süloğlu | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `6de2ce848e033fec` |
| 1705 | Uzunköprü | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `4c3cb2adb721eef6` |
| 1412 | İpsala | Edirne | OK | 8036 | 2004-01-01 | 2025-12-31 | `3062192103e904e1` |
| 1163 | Babaeski | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `6de2ce848e033fec` |
| 1270 | Demirköy | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `1e1a6f8c1595de57` |
| 1480 | Kofçaz | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `3fc0c54c1a1e359f` |
| 1505 | Lüleburgaz | Kırklareli | CACHE_HIT | 8036 | 2004-01-01 | 2025-12-31 | `f20ab13868191784` |
| 1471 | Merkez | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `f20ab13868191784` |
| 1572 | Pehlivanköy | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `6de2ce848e033fec` |
| 1577 | Pınarhisar | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `f20ab13868191784` |
| 1714 | Vize | Kırklareli | OK | 8036 | 2004-01-01 | 2025-12-31 | `f20ab13868191784` |
| 2094 | Ergene | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `f20ab13868191784` |
| 1388 | Hayrabolu | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `7721d0acdfdde9a5` |
| 2095 | Kapaklı | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `1ce2aeefbdc9d952` |
| 1511 | Malkara | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `52036b4f9e559128` |
| 1825 | Marmaraereğlisi | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `aac69f70d88c0386` |
| 1673 | Merkez | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `ba902b2a4bd56b5c` |
| 1538 | Muratlı | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `a6e29e7cf1948440` |
| 1596 | Saray | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `39ae76ea431d0dea` |
| 2096 | Süleymanpaşa | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `ba902b2a4bd56b5c` |
| 1250 | Çerkezköy | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `1ce2aeefbdc9d952` |
| 1258 | Çorlu | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `a6e29e7cf1948440` |
| 1652 | Şarköy | Tekirdağ | OK | 8036 | 2004-01-01 | 2025-12-31 | `24c16e36a3321ebe` |

## Akademik notlar
- MERRA-2 vs ERA5-Land farkı tezde Bölüm 4.2'de açıkça raporlanacak.
- ET0 türevi NASA POWER direct vermez; T+RH+rad'tan Penman-Monteith ile
  feature_builder katmanında türetilecek (Görev 4).