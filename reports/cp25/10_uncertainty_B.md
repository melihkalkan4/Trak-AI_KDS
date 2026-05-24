# ÇP-2.5 — Görev 10: Belirsizlik Kalibrasyonu (Layer B)

## Yöntem

- **GPR**: Matern(ν=2.5) + WhiteKernel, LOYO her fold için yeniden fit
- **Bootstrap**: XGBoost 100 resample, LOYO
- **PICP** = mean(y ∈ [PI_2.5, PI_97.5]), hedef ≈ 0.95
- **Sharpness** = mean(PI_upper - PI_lower)

## aycicegi_yaglik (n=209)

| Yöntem | PICP | Sharpness (kg/da) |
|---|---|---|
| XGBoost Bootstrap (n=100) | **0.502** | 72.2 |

## bugday (n=213)

| Yöntem | PICP | Sharpness (kg/da) |
|---|---|---|
| XGBoost Bootstrap (n=100) | **0.441** | 97.8 |
