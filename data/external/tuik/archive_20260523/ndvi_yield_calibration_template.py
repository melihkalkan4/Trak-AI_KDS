"""
═══════════════════════════════════════════════════════════════════
NDVI × YIELD KALİBRASYON ŞABLONU — TRAK-AIA / ÇP-2 Entegrasyonu
═══════════════════════════════════════════════════════════════════

AMAÇ:
ÇP-2 modelinin ürettiği NDVI tahminlerini somut "kg/dekar" hasat tahminine
çevirmek için il bazlı kalibrasyon modeli kurar.

GİRDİ:
1. tuik_trakya_yields_clean.csv  (bu paketle birlikte gelen)
2. master_feature_matrix.csv     (sizin ÇP-1 ETL çıktınız)
   Beklenen kolonlar: date, il, ndvi, evi, ndwi, t2m_max, t2m_min, tp,
                       ssr, gdd_cum, ...

ÇIKTI:
- per_il_yield_calibration.pkl   (her il × ürün için scikit-learn model)
- calibration_metrics.json       (R², MAE, RMSE)
- yield_prediction_example.csv   (2017–2024 model vs gerçek)

KULLANIM (çalıştırma):
    python ndvi_yield_calibration_template.py \
        --features /path/to/master_feature_matrix.csv \
        --yields  /path/to/tuik_trakya_yields_clean.csv \
        --crop bugday   # veya aycicegi_yaglik

═══════════════════════════════════════════════════════════════════
"""
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import pickle


# ─── ÜRÜNE GÖRE FENOLOJİK PENCERELER ────────────────────────────
# (BBCH bilgisi + Trakya iklimi referans alındı)
SEASON_WINDOWS = {
    'bugday': {  # Kışlık buğday: Ekim–Temmuz
        'name': 'Buğday (kışlık)',
        'season_start': (10, 1),    # 1 Ekim önceki yıl
        'season_end':   (7, 15),    # 15 Temmuz hasat yılı
        'flowering':    ((5, 1), (5, 31)),   # çiçeklenme penceresi
        'grain_fill':   ((6, 1), (6, 30)),   # tane dolum
        'year_offset': -1,  # season t-1 başlar
    },
    'aycicegi_yaglik': {  # Yazlık ayçiçeği: Nisan–Eylül
        'name': 'Ayçiçeği (yağlık)',
        'season_start': (4, 1),
        'season_end':   (9, 30),
        'flowering':    ((7, 1), (7, 31)),
        'grain_fill':   ((8, 1), (8, 31)),
        'year_offset': 0,
    },
}


def extract_seasonal_features(features_df, il, year, crop_window):
    """
    Bir (il, yıl) için NDVI-tabanlı sezonluk öznitelikler çıkarır.

    Üretilen özellikler (literatürdeki klasik yield-NDVI bağlayıcılar):
    - ndvi_max:        sezon boyunca peak NDVI
    - ndvi_mean:       sezon ortalama NDVI
    - ndvi_integral:   NDVI eğrisi altında alan (~ toplam fotosentez)
    - ndvi_flowering:  çiçeklenme dönemi ortalama NDVI (kritik)
    - ndvi_grain_fill: tane dolum dönemi ortalama NDVI
    - greenness_days:  NDVI > 0.6 olan gün sayısı
    - gdd_cum_season:  sezonluk kümülatif GDD
    - tp_season_sum:   sezonluk toplam yağış
    """
    yoff = crop_window['year_offset']
    sm, sd = crop_window['season_start']
    em, ed = crop_window['season_end']
    start = pd.Timestamp(year + yoff, sm, sd)
    end = pd.Timestamp(year, em, ed)

    mask = (
        (features_df['il'] == il)
        & (features_df['date'] >= start)
        & (features_df['date'] <= end)
    )
    g = features_df[mask].sort_values('date')

    if len(g) < 30:
        return None  # yetersiz veri

    ndvi = g['ndvi'].dropna().values

    # Çiçeklenme penceresi
    fm, fd_ = crop_window['flowering'][0]
    fme, fde = crop_window['flowering'][1]
    fl_start = pd.Timestamp(year, fm, fd_)
    fl_end = pd.Timestamp(year, fme, fde)
    fl_mask = (g['date'] >= fl_start) & (g['date'] <= fl_end)
    fl_ndvi = g.loc[fl_mask, 'ndvi'].mean()

    # Tane dolum
    gm, gd_ = crop_window['grain_fill'][0]
    gme, gde = crop_window['grain_fill'][1]
    gf_start = pd.Timestamp(year, gm, gd_)
    gf_end = pd.Timestamp(year, gme, gde)
    gf_mask = (g['date'] >= gf_start) & (g['date'] <= gf_end)
    gf_ndvi = g.loc[gf_mask, 'ndvi'].mean()

    return {
        'il': il,
        'year': year,
        'ndvi_max': np.nanmax(ndvi) if len(ndvi) else np.nan,
        'ndvi_mean': np.nanmean(ndvi) if len(ndvi) else np.nan,
        'ndvi_integral': np.nansum(ndvi) if len(ndvi) else np.nan,
        'ndvi_flowering': fl_ndvi,
        'ndvi_grain_fill': gf_ndvi,
        'greenness_days': int((ndvi > 0.6).sum()) if len(ndvi) else 0,
        'gdd_cum_season': g['gdd_cum'].iloc[-1] - g['gdd_cum'].iloc[0]
                          if 'gdd_cum' in g.columns and len(g) > 1 else np.nan,
        'tp_season_sum': g['tp'].sum() if 'tp' in g.columns else np.nan,
    }


def build_training_set(features_df, yields_df, crop):
    """(yıl × il) seviyesinde X, y eğitim seti üretir."""
    window = SEASON_WINDOWS[crop]
    y_sub = yields_df[yields_df['crop'] == crop].copy()
    rows = []
    for _, r in y_sub.iterrows():
        feats = extract_seasonal_features(features_df, r['il'], int(r['year']), window)
        if feats is None:
            continue
        feats['yield_kg_da'] = r['verim_kg_da']
        rows.append(feats)
    return pd.DataFrame(rows)


def fit_and_eval(train_df, model_kind='gbr'):
    """LOOCV (Leave-One-Out CV) ile bölgesel kalibrasyon modeli kurar."""
    feature_cols = ['ndvi_max', 'ndvi_mean', 'ndvi_integral',
                    'ndvi_flowering', 'ndvi_grain_fill', 'greenness_days',
                    'gdd_cum_season', 'tp_season_sum']
    X = train_df[feature_cols].fillna(train_df[feature_cols].median())
    y = train_df['yield_kg_da'].values

    loo = LeaveOneOut()
    preds = np.zeros_like(y, dtype=float)
    for tr, te in loo.split(X):
        if model_kind == 'ridge':
            m = Ridge(alpha=1.0)
        else:
            m = GradientBoostingRegressor(
                n_estimators=200, max_depth=3, learning_rate=0.05,
                random_state=42
            )
        m.fit(X.iloc[tr], y[tr])
        preds[te] = m.predict(X.iloc[te])

    metrics = {
        'r2': float(r2_score(y, preds)),
        'mae_kg_da': float(mean_absolute_error(y, preds)),
        'rmse_kg_da': float(np.sqrt(mean_squared_error(y, preds))),
        'n_samples': int(len(y)),
        'mean_yield_kg_da': float(np.mean(y)),
    }

    # Final model on all data
    if model_kind == 'ridge':
        final = Ridge(alpha=1.0)
    else:
        final = GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            random_state=42
        )
    final.fit(X, y)

    out_df = train_df.copy()
    out_df['yield_pred_loocv'] = preds
    out_df['abs_error'] = np.abs(out_df['yield_kg_da'] - out_df['yield_pred_loocv'])

    return final, metrics, out_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--features', required=True,
                    help='ÇP-1 master_feature_matrix.csv yolu')
    ap.add_argument('--yields', required=True,
                    help='tuik_trakya_yields_clean.csv yolu')
    ap.add_argument('--crop', default='bugday',
                    choices=list(SEASON_WINDOWS.keys()))
    ap.add_argument('--model', default='gbr', choices=['gbr', 'ridge'])
    ap.add_argument('--out', default='./calibration_out')
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True, parents=True)

    print(f"\n📂 Veri yükleniyor: features={args.features}, yields={args.yields}")
    feats = pd.read_csv(args.features, parse_dates=['date'])
    yields = pd.read_csv(args.yields)

    print(f"\n🔧 Özellik çıkarımı: ürün={args.crop}")
    train = build_training_set(feats, yields, args.crop)
    if len(train) < 8:
        raise RuntimeError(f"Yetersiz örneklem: {len(train)} (min 8)")
    print(f"   {len(train)} (il × yıl) örneği oluşturuldu")

    print(f"\n🤖 LOOCV ile eğitim: model={args.model}")
    model, metrics, pred_df = fit_and_eval(train, model_kind=args.model)
    print(f"\n📊 PERFORMANS METRİKLERİ:")
    for k, v in metrics.items():
        print(f"   {k}: {v:.4f}" if isinstance(v, float) else f"   {k}: {v}")

    # Kaydet
    with open(out / f'model_{args.crop}_{args.model}.pkl', 'wb') as f:
        pickle.dump({'model': model, 'metrics': metrics,
                     'crop': args.crop,
                     'feature_cols': [c for c in train.columns
                                      if c not in ('il', 'year', 'yield_kg_da')]}, f)
    with open(out / f'metrics_{args.crop}_{args.model}.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    pred_df.to_csv(out / f'predictions_{args.crop}_{args.model}.csv', index=False)
    print(f"\n✅ Çıktılar: {out}/")


if __name__ == '__main__':
    main()
