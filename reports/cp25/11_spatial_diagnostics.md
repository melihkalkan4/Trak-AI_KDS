# ÇP-2.5 — Görev 11: Mekânsal Tanılama (Moran's I)

## Yöntem

1. Layer A şampiyon model LOYO residuals (her ilçe için ortalama).
2. KNN(k=4) komşuluk grafiği lat/lon centroid'lerden.
3. ``esda.Moran`` ile global Moran's I + permutation test (999 iter).

## Sonuçlar

| Ürün | Moran's I | E[I] | z-norm | p_norm | p_sim | n_ilçe |
|---|---|---|---|---|---|---|
| bugday | +0.257 | -0.036 | +2.64 | 0.0082 | 0.0110 | 29 |
| aycicegi | +0.117 | -0.037 | +1.38 | 0.1679 | 0.0790 | 28 |

## H5 Yorum

- **bugday**: 🟡 Pozitif spatial autocorrelation tespit edildi (p<0.05). Komşu ilçelerde benzer hata kalıbı → geographic feature (lat/lon, soil, micro-climate) modele eklenmeli.
- **aycicegi**: 🟢 Residuals mekânsal bağımsız — model spatial bilgiyi yakalamış.

## Görsel
`reports/cp25/fig_morans_i.png`