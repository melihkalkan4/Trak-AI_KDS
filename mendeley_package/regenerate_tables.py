#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the headline derived tables of the TRAK-AI deposit from the shipped raw inputs, and
check them against the published invariants. No Earth Engine / no network needed — operates only on
the files in this deposit. (The Sentinel-2 extraction itself lives in the code repository.)

Usage:  python regenerate_tables.py
Outputs: regenerated/mask_validation.csv, regenerated/generalization_gap_climate_tier.csv
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "regenerated"; OUT.mkdir(exist_ok=True)
def r2(y, p):
    y = np.asarray(y, float); p = np.asarray(p, float)
    ss_res = np.sum((y - p) ** 2); ss_tot = np.sum((y - y.mean()) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
def rmse(y, p): return float(np.sqrt(np.mean((np.asarray(y,float)-np.asarray(p,float))**2)))
def check(name, got, exp, tol=0.001):
    good = abs(got - exp) <= tol
    print(f"  [{'PASS' if good else '*** FAIL ***'}] {name}: got {got:+.3f} (expected {exp:+.3f})")
    return good

print("== TABLE 1: crop-mask validation vs TÜİK planted area (Pearson) ==")
area = pd.read_csv(HERE/"02_crop_specific_layer"/"crop_classified_area_ha.csv")
t = pd.read_csv(HERE/"06_tuik_reference"/"tuik_ilce_crop_yields_2004_2025.csv")
tw = t[t.crop=="bugday"].groupby(["ilce_id","year"]).ekilen_alan_da.sum().div(10).rename("wt")
ts = t[t.crop=="aycicegi_yaglik"].groupby(["ilce_id","year"]).ekilen_alan_da.sum().div(10).rename("st")
m = area.merge(tw,on=["ilce_id","year"]).merge(ts,on=["ilce_id","year"])
wr = round(m.wheat_classified_ha.corr(m.wt),3); sr = round(m.sun_classified_ha.corr(m.st),3)
pd.DataFrame([{"crop":"wheat","pearson_r":wr,"n_district_years":len(m),"n_districts":m.ilce_id.nunique()},
              {"crop":"sunflower","pearson_r":sr,"n_district_years":len(m),"n_districts":m.ilce_id.nunique()}]
             ).to_csv(OUT/"mask_validation.csv",index=False)
ok = True
ok &= check("wheat r",   wr, 0.954); ok &= check("sunflower r", sr, 0.615)
ok &= (len(m)==216); print(f"  [{'PASS' if len(m)==216 else 'FAIL'}] n=216 district-years: got {len(m)}")

print("\n== TABLE 2: spatial-minus-temporal gap, climate tier (from per-sample predictions) ==")
pp = pd.read_csv(HERE/"04_folds_and_predictions"/"per_sample_predictions_main.csv")
FIXED = {"bugday":"gpr", "aycicegi":"xgboost"}   # fixed climate-tier model used for the paper's gap
rows=[]
for crop, mdl in FIXED.items():
    sub = pp[(pp.layer=="A") & (pp.crop==crop) & (pp.model==mdl)]
    loyo = sub[sub.cv=="LOYO"]; loilo = sub[sub.cv=="LOILO"]
    r_loyo = r2(loyo.y_true, loyo.y_pred); r_loilo = r2(loilo.y_true, loilo.y_pred)
    gap = r_loilo - r_loyo
    rows.append({"crop":crop,"model":mdl,"r2_LOYO":round(r_loyo,3),"r2_LOILO":round(r_loilo,3),
                 "gap_dR2":round(gap,3),"n_LOYO":len(loyo),"n_LOILO":len(loilo)})
gdf = pd.DataFrame(rows); gdf.to_csv(OUT/"generalization_gap_climate_tier.csv",index=False)
print(gdf.to_string(index=False))
ok &= check("wheat climate-tier gap",     gdf[gdf.crop=="bugday"].gap_dR2.iloc[0], 0.639, tol=0.005)
ok &= check("sunflower climate-tier gap", gdf[gdf.crop=="aycicegi"].gap_dR2.iloc[0], 0.580, tol=0.005)

print("\nRESULT:", "ALL CHECKS PASS — deposit reproduces the published invariants." if ok
      else "*** SOME CHECKS FAILED — inspect regenerated/ ***")
print("wrote:", OUT/"mask_validation.csv", "and", OUT/"generalization_gap_climate_tier.csv")
sys.exit(0 if ok else 1)
