# ÇP-2.5 — Görev 10: Belirsizlik Kalibrasyonu (Layer A)

## Yöntem

- **GPR**: Matern(ν=2.5) + WhiteKernel, LOYO her fold için yeniden fit
- **Bootstrap**: XGBoost 50 resample, LOYO
- **PICP** = mean(y ∈ [PI_2.5, PI_97.5]), hedef ≈ 0.95
- **Sharpness** = mean(PI_upper - PI_lower)

## aycicegi_yaglik (n=576)

| Yöntem | PICP | Sharpness (kg/da) |
|---|---|---|
| XGBoost Bootstrap (n=50) | **0.384** | 51.8 |

## bugday (n=589)

| Yöntem | PICP | Sharpness (kg/da) |
|---|---|---|
| XGBoost Bootstrap (n=50) | **0.374** | 79.6 |
