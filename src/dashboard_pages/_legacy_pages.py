"""Legacy page renderers preserved verbatim from the original src/dashboard.py.

The new router (`src/dashboard.py`) imports `page_tarla`, `page_rover`,
`page_chat`, and the `KDS_AKSIYONLAR` registry from this module so the
unified master dashboard can keep using the original 3 farmer-facing pages
without rewriting their logic.

Differences from the original `src/dashboard.py`:
    * `st.set_page_config` removed — only the router may call it.
    * `PROJECT_ROOT` recomputed for the new location (`src/dashboard_pages/`).
    * `init_db()` removed — the router seeds the DB once at startup.
    * No `main()` / `if __name__ == "__main__":` guard.

All other page-rendering logic is intentionally identical to preserve
behaviour while the master dashboard migration is in progress.
"""
from __future__ import annotations

import sys
import os
import json
import logging
from datetime import datetime, timedelta, date

# ── Path Kurulumu (one level deeper than original dashboard.py) ──────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SRC_DIR = os.path.join(PROJECT_ROOT, "src")
_CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
_CP4_DIR = os.path.join(PROJECT_ROOT, "src", "cp4_rag")
for _p in [_SRC_DIR, _CP2_DIR, _CP4_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Veritabani ────────────────────────────────────────────────────────────────
from database import (
    init_db, get_tarlalar, get_tarla, add_rover_olcum,
    get_rover_olcumler, get_rover_olcumler_asc,
    get_son_tahmin, get_tarla_ozet,
    get_weather_history, get_weather_stats,
    _wheat_season, _sunflower_season,
)

# ── Opsiyonel moduller ────────────────────────────────────────────────────────
try:
    from weather_service import (
        get_current_weather, get_7day_forecast, get_weather_alerts,
    )
    _WEATHER_OK = True
except ImportError:
    _WEATHER_OK = False

try:
    from agro_calendar import (
        get_current_phenology, evaluate_planting_window,
        get_irrigation_advice, get_fertilization_advice,
    )
    _AGRO_OK = True
except ImportError:
    _AGRO_OK = False

try:
    from llm_engine import (
        build_rich_context, classify_query,
        generate_chat_response, check_ollama_connection,
    )
    _LLM_OK = True
except ImportError:
    _LLM_OK = False

try:
    from build_index import load_faiss_index
    _FAISS_DATA = load_faiss_index()
    _vectorstore = _FAISS_DATA[0] if _FAISS_DATA else None
    _chunks = _FAISS_DATA[1] if _FAISS_DATA and len(_FAISS_DATA) > 1 else []
    _FAISS_OK = _vectorstore is not None
except Exception:
    _vectorstore = None
    _chunks = []
    _FAISS_OK = False

try:
    from image_classifier import classifier as _img_clf, KDS_AKSIYONLAR
    _YOLO_OK = _img_clf.model is not None
except ImportError:
    _img_clf = None
    _YOLO_OK = False
    KDS_AKSIYONLAR = {}


# ── Yardimci Fonksiyonlar ─────────────────────────────────────────────────────

def _ndvi_renk(ndvi: float) -> str:
    if ndvi is None:
        return "gray"
    if ndvi >= 0.55:
        return "green"
    if ndvi >= 0.40:
        return "orange"
    return "red"


def _saglik_badge(ndvi: float) -> str:
    if ndvi is None:
        return "Bilinmiyor"
    if ndvi >= 0.60:
        return "Mukemmel"
    if ndvi >= 0.50:
        return "Iyi"
    if ndvi >= 0.40:
        return "Orta"
    if ndvi >= 0.30:
        return "Zayif"
    return "Kritik"


def _crop_key(tarla: dict) -> str:
    """Normalise the active crop label to the CP2 model key.

    Accepts Turkish or English variants written to `tarla.crop_type` /
    `tarlalar.aktif_urun` (e.g. 'sunflower', 'ayçiçeği', 'wheat',
    'buğday'). Defaults to 'Wheat'.
    """
    urun = (tarla.get("aktif_urun") or "wheat").lower()
    if any(t in urun for t in ("sunflower", "aycicegi", "ayci",
                                "ayçiçeği", "ayçiçek")):
        return "Sunflower"
    return "Wheat"


def _crop_badge(tarla: dict) -> str:
    """One-line emoji + TR label for the active crop."""
    return ("🌻 Ayçiçeği" if _crop_key(tarla) == "Sunflower"
            else "🌾 Buğday")


@st.cache_data(show_spinner=False)
def _load_yield_meta(crop_key: str) -> dict:
    """Read cp2_model/yield_meta_{crop}.json once per session.

    Returns {} on missing/invalid file so callers can fall back gracefully.
    """
    fname = "yield_meta_sunflower.json" if crop_key == "Sunflower" else "yield_meta_wheat.json"
    path = os.path.join(_CP2_DIR, fname)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _trakya_median(crop_key: str) -> float:
    """Trakya regional median yield (kg/da) from yield_meta_*.json.

    Falls back to literature averages if metadata is unavailable.
    """
    meta = _load_yield_meta(crop_key)
    val = meta.get("trakya_median_yield")
    if val:
        return float(val)
    return 324.0 if crop_key == "Wheat" else 180.0


def _model_nem(tarla: dict, scan_date: date) -> float:
    crop_key = _crop_key(tarla)
    clay = tarla.get("toprak_kil") or 31.0
    if crop_key == "Wheat":
        prof = _wheat_season(scan_date, clay)
    else:
        ekim_str = tarla.get("ekim_tarihi") or "2026-04-20"
        try:
            ekim_date = datetime.strptime(ekim_str, "%Y-%m-%d").date()
        except Exception:
            ekim_date = date(2026, 4, 20)
        days = max(0, (scan_date - ekim_date).days)
        prof = _sunflower_season(days, scan_date)
    return round(prof["nem_c"], 1)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("# 🌾 TRAK-AIA KDS")
        st.caption("TUBiTAK 2209-A • Trakya Universitesi • 2026")
        st.divider()

        # Tarla secici
        tarlalar = get_tarlalar()
        tarla_labels = {t["id"]: f"{t['isim']} ({t['aktif_urun']})" for t in tarlalar}
        tarla_ids = list(tarla_labels.keys())
        selected_id = st.selectbox(
            "Tarla Sec",
            options=tarla_ids,
            format_func=lambda x: tarla_labels[x],
            key="tarla_id",
        )
        tarla = get_tarla(selected_id)

        # Mini tayla karti
        if tarla:
            with st.container(border=True):
                st.markdown(f"**{tarla['isim']}**")
                c1, c2 = st.columns(2)
                c1.caption(f"Il: {tarla['il']}")
                c2.caption(f"Urun: {tarla['aktif_urun']}")
                c1.caption(f"Alan: {tarla.get('alan_dekar', '?')} da")
                _ekim = tarla.get("ekim_tarihi") or "?"
                c2.caption(f"Ekim: {_ekim[:7]}")

        st.divider()

        # Sistem durumu
        st.markdown("**Sistem Durumu**")
        ollama_ok = _LLM_OK and check_ollama_connection() if _LLM_OK else False
        st.markdown(
            f"Ollama {'🟢' if ollama_ok else '🔴'}  |  "
            f"FAISS {'✅' if _FAISS_OK else '❌'}  |  "
            f"DB ✅  |  "
            f"YOLOv8 {'✅' if _YOLO_OK else '⚠️ MOCK'}"
        )

        st.divider()

        # Sayfa navigasyonu
        page = st.radio(
            "Sayfa",
            ["🌿 Tarla Durumu", "📡 Rover Izleme", "💬 Tarim Asistani"],
            label_visibility="collapsed",
        )

    return selected_id, tarla, page


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA 1: Tarla Durumu ve Oneriler
# ═══════════════════════════════════════════════════════════════════════════════

def page_tarla(tarla_id: int, tarla: dict):
    crop_key = _crop_key(tarla)
    urun_label = tarla.get("aktif_urun", "Bugday")
    st.header(f"🌿 Tarla Durumu — {tarla['isim']}")
    st.caption(
        f"**Ürün:** {_crop_badge(tarla)}  |  "
        f"**Konum:** ({tarla.get('konum_lat', '?')}, "
        f"{tarla.get('konum_lon', '?')})  |  "
        f"**Alan:** {tarla.get('alan_dekar', '?')} da  |  "
        f"**Toprak:** {tarla.get('toprak_tipi') or '—'}  |  "
        f"**Ekim:** {tarla.get('ekim_tarihi') or '—'}"
    )

    # Son tahmin ve rover verisi
    son_tahmin = get_son_tahmin(tarla_id) or {}
    son_rover_list = get_rover_olcumler(tarla_id, limit=1)
    son_rover = son_rover_list[0] if son_rover_list else {}

    # Hava (tarla koordinatiyla)
    weather = {}
    forecast = []
    alerts = []
    if _WEATHER_OK:
        try:
            weather = get_current_weather(tarla["konum_lat"], tarla["konum_lon"]) or {}
            forecast = get_7day_forecast(tarla["konum_lat"], tarla["konum_lon"]) or []
            alerts = get_weather_alerts(weather, forecast) if weather else []
        except Exception:
            pass

    # Fenoloji & Sulama
    fenoloji = {}
    sulama = {}
    gubre = {}
    ekim_degerlendirme = {}
    if _AGRO_OK:
        try:
            now_month = datetime.now().month
            fenoloji = get_current_phenology(crop_key, now_month) or {}
            # Prefer rover observation; fall back to ERA5 soil_moisture from
            # weather_service. soil_moisture may arrive as fraction (0..1) or
            # percent (>1.5) depending on the upstream client — rescale only
            # in the fraction case. If neither source has a real value we pass
            # None to get_irrigation_advice so it can flag missing input
            # instead of silently treating dry soil as 25%.
            _rover_h = son_rover.get("humidity") if son_rover else None
            _sm_raw = weather.get("soil_moisture") if weather else None
            if _rover_h is not None:
                nem_degeri = _rover_h
            elif _sm_raw is None:
                nem_degeri = None
            elif _sm_raw > 1.5:
                nem_degeri = _sm_raw            # already percent
            else:
                nem_degeri = _sm_raw * 100.0    # 0..1 fraction → percent
            sulama = (get_irrigation_advice(crop_key, now_month, nem_degeri, forecast)
                      if nem_degeri is not None else {}) or {}
            gubre_sonuc = get_fertilization_advice(crop_key, now_month)
            if isinstance(gubre_sonuc, dict):
                gubre = gubre_sonuc
            elif isinstance(gubre_sonuc, list) and gubre_sonuc:
                gubre = gubre_sonuc[0]
        except Exception:
            pass
        try:
            ekim_degerlendirme = evaluate_planting_window(crop_key, weather, forecast) or {}
        except Exception:
            pass

    # ── Uyari Banner ──────────────────────────────────────────────────────────
    if alerts:
        for al in alerts:
            st.error(f"⚠️ {al}")

    # Son kamera tespiti varsa ust banner
    son_kamera_bulgu = None
    tum_rover = get_rover_olcumler(tarla_id, limit=10)
    for r in tum_rover:
        if r.get("camera_sinif") and r["camera_sinif"] not in ("saglikli_bugday", "saglikli_aycicegi"):
            son_kamera_bulgu = r
            break

    if son_kamera_bulgu:
        aksiyon = KDS_AKSIYONLAR.get(son_kamera_bulgu["camera_sinif"], {})
        st.error(
            f"📷 Kamera Tespiti: **{son_kamera_bulgu['camera_sinif']}** "
            f"(%{(son_kamera_bulgu.get('camera_guven') or 0)*100:.0f} guven) — "
            f"{aksiyon.get('tavsiye', '')}"
        )

    # ── 1A: Bitki Sagligi Karti ───────────────────────────────────────────────
    st.subheader("🌱 Bitki Sagligi")
    ndvi_mevcut = son_tahmin.get("ndvi_mevcut")
    ndvi_tahmin = son_tahmin.get("ndvi_tahmin_7gun")
    ndvi_delta  = son_tahmin.get("ndvi_delta", 0) or 0

    col_a, col_b, col_c = st.columns(3)
    ndvi_display = f"{ndvi_mevcut:.3f}" if ndvi_mevcut is not None else "—"
    delta_display = f"{ndvi_delta:+.3f}" if ndvi_delta != 0 else None
    col_a.metric("NDVI (Mevcut)", ndvi_display, delta=delta_display)
    col_b.metric("7 Gun Tahmini", f"{ndvi_tahmin:.3f}" if ndvi_tahmin else "—")
    saglik = _saglik_badge(ndvi_mevcut)
    col_c.metric("Saglik Durumu", saglik)

    # ── 1A-bis: On-demand frozen LSTM tahmin butonu ──────────────────────────
    if st.button("🔮 Tahmin Yap (Frozen LSTM, 7 gun)",
                 key=f"predict_now_{tarla_id}", use_container_width=True):
        try:
            from data_integration.live_predictor import predict_for_tarla
            with st.spinner("Frozen LSTM calistiriliyor..."):
                res = predict_for_tarla(tarla_id, persist=True)
            if not res["ok"]:
                st.error(f"Tahmin yapilamadi: {res.get('error')}")
            else:
                lr = res["last_row"]
                pa, pb, pc = st.columns(3)
                pa.metric("Tahmin (t+7)",
                          f"{lr['predicted_ndvi']:.3f}",
                          delta=f"{lr['residual_delta']:+.3f}")
                pb.metric("Son gozlem",
                          f"{lr['last_observed_ndvi']:.3f}")
                anom = lr.get("anomaly_vs_climatology")
                pc.metric("Klimatoloji farki",
                          f"{anom:+.3f}" if anom is not None else "—")
                st.caption(
                    f"Hedef tarih: {lr['target_date']} · "
                    f"Toplam {res['n_predictions']} satir · "
                    f"Kaynak: {res['features_path']}"
                )
        except Exception as exc:                                       # noqa: BLE001
            st.error(f"Frozen LSTM yuklenemedi: {exc}")

    # NDVI trend grafigi (DB'den son 30 olcum)
    tum_asc = get_rover_olcumler_asc(tarla_id, limit=5000)
    tahmin_rows = [r for r in tum_asc if r.get("ndvi") is not None]
    if len(tahmin_rows) >= 3:
        recent = tahmin_rows[-30:]
        df_ndvi = pd.DataFrame(recent)
        df_ndvi["ts"] = pd.to_datetime(df_ndvi["timestamp"])
        fig_ndvi = go.Figure()
        fig_ndvi.add_trace(go.Scatter(
            x=df_ndvi["ts"], y=df_ndvi["ndvi"],
            mode="lines+markers", name="NDVI",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=5),
        ))
        fig_ndvi.update_layout(
            height=200, margin=dict(t=10, b=20, l=40, r=20),
            yaxis=dict(range=[0, 1], title="NDVI"),
            xaxis_title="Tarih",
            showlegend=False,
        )
        st.plotly_chart(fig_ndvi, use_container_width=True)

    # ── 1B: Verim Projeksiyonu ────────────────────────────────────────────────
    st.subheader("📊 Verim Projeksiyonu")
    verim_kg = son_tahmin.get("verim_tahmini_kg_dekar")
    verim_alt = son_tahmin.get("verim_guven_alt")
    verim_ust = son_tahmin.get("verim_guven_ust")
    verim_risk = son_tahmin.get("verim_risk", "Bilinmiyor")
    trakya_ort = _trakya_median(crop_key)

    col1, col2, col3 = st.columns(3)
    if verim_kg:
        col1.metric("Tahmini Verim", f"{verim_kg:.0f} kg/da")
        col2.metric("Guvenlı Aralik", f"{verim_alt:.0f}–{verim_ust:.0f}" if verim_alt and verim_ust else "—")
        col3.metric("Risk", verim_risk or "Bilinmiyor")

        oran = min(1.0, verim_kg / (trakya_ort * 1.5))
        st.caption(f"Trakya ortalamasina kiyasla: {verim_kg/trakya_ort*100:.0f}%")
        st.progress(oran, text=f"{verim_kg:.0f} / {trakya_ort:.0f} kg/da (Trakya ort.)")
    else:
        col1.info("Verim tahmini hesaplanmadi")

    # ── 1C: Hava Durumu ───────────────────────────────────────────────────────
    st.subheader("🌤️ Hava Durumu")
    if weather:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sicaklik", f"{weather.get('temp_c', '?'):.1f}°C")
        c2.metric("Nem", f"%{weather.get('humidity', '?'):.0f}")
        c3.metric("Ruzgar", f"{weather.get('wind_kmh', 0):.0f} km/s")
        # weather_service.get_current_weather already returns soil_moisture
        # as percentage (m³/m³ × 100). Render as-is to avoid %3530 bug.
        sm = weather.get('soil_moisture')
        if sm is None:
            c4.metric("Toprak Nemi", "—")
        else:
            sm_pct = sm if sm > 1.5 else sm * 100   # accept both shapes defensively
            sm_pct = min(sm_pct, 99.9)
            c4.metric("Toprak Nemi", f"%{sm_pct:.1f}")

        if forecast and len(forecast) >= 3:
            df_fc = pd.DataFrame(forecast[:7])
            fig_hava = go.Figure()
            if "date" in df_fc.columns:
                fig_hava.add_trace(go.Bar(x=df_fc["date"], y=df_fc.get("precip_mm", [0]*7),
                                          name="Yagis (mm)", marker_color="#aec7e8", yaxis="y2"))
                fig_hava.add_trace(go.Scatter(x=df_fc["date"], y=df_fc.get("temp_max_c", [20]*7),
                                              mode="lines+markers", name="Max Sicaklik",
                                              line=dict(color="#d62728")))
                fig_hava.add_trace(go.Scatter(x=df_fc["date"], y=df_fc.get("temp_min_c", [10]*7),
                                              mode="lines+markers", name="Min Sicaklik",
                                              line=dict(color="#1f77b4")))
                fig_hava.update_layout(
                    height=260, margin=dict(t=10, b=20, l=40, r=40),
                    yaxis=dict(title="Sicaklik (°C)"),
                    yaxis2=dict(title="Yagis (mm)", overlaying="y", side="right"),
                    legend=dict(orientation="h", y=1.12),
                )
                st.plotly_chart(fig_hava, use_container_width=True)
    else:
        st.info("Hava verisi alinemiyor (internet baglantisini kontrol edin).")

    # ── 1C-bis: Hava Durumu Gecmisi ───────────────────────────────────────────
    hava_gecmis = get_weather_history(tarla_id, days=30)
    if hava_gecmis:
        hava_stats = get_weather_stats(tarla_id, days=30)
        # get_weather_stats can return None values (not just missing keys),
        # so coerce numeric stats with `or 0` before formatting.
        _avg_t   = hava_stats.get("avg_temp")
        _max_t   = hava_stats.get("max_temp")
        _min_t   = hava_stats.get("min_temp")
        _toplam_y = hava_stats.get("toplam_yagis") or 0
        _gdd     = hava_stats.get("son_gdd_kum") or 0
        _yag_gun = hava_stats.get("yagisli_gun") or 0
        with st.expander(
            f"📊 Hava Durumu Gecmisi (Son 30 Gun) — "
            f"Ort. {_avg_t if _avg_t is not None else '?'}°C | "
            f"Toplam Yagis: {_toplam_y:.0f}mm | "
            f"GDD: {_gdd:.0f}",
            expanded=False,
        ):
            cols_stat = st.columns(5)
            cols_stat[0].metric("Ort. Sicaklik",
                                f"{_avg_t if _avg_t is not None else '?'}°C")
            cols_stat[1].metric("Max Sicaklik",
                                f"{_max_t if _max_t is not None else '?'}°C")
            cols_stat[2].metric("Min Sicaklik",
                                f"{_min_t if _min_t is not None else '?'}°C")
            cols_stat[3].metric("Yagisli Gun", _yag_gun)
            cols_stat[4].metric("GDD Kumulatif", f"{_gdd:.0f}")

            df_hv = pd.DataFrame(hava_gecmis)
            df_hv["tarih_dt"] = pd.to_datetime(df_hv["timestamp"])

            # ERA5 tp_sum on disk uses the legacy sum-of-accumulated-hourlies
            # scale (~12.5x daily total). Display in realistic mm.
            df_hv["yagis_disp"] = (
                df_hv["precipitation"].fillna(0) / 12.5
            ).clip(lower=0, upper=80)

            fig_h = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                row_heights=[0.45, 0.30, 0.25],
                vertical_spacing=0.06,
                subplot_titles=["Sicaklik (°C)", "Gunluk Yagis (mm)", "Kumulatif GDD"],
            )
            # sensor_reading has a single daily mean temperature column; we no
            # longer fabricate ±5°C bands. A 7-day rolling min/max envelope
            # over that mean gives a real, honest band of recent variability.
            t_rolling_max = df_hv["temperature"].rolling(7, min_periods=1).max()
            t_rolling_min = df_hv["temperature"].rolling(7, min_periods=1).min()
            fig_h.add_trace(go.Scatter(
                x=df_hv["tarih_dt"], y=t_rolling_max,
                mode="lines", name="7g Max", line=dict(color="#d62728", width=1.2),
            ), row=1, col=1)
            fig_h.add_trace(go.Scatter(
                x=df_hv["tarih_dt"], y=t_rolling_min,
                mode="lines", name="7g Min", line=dict(color="#1f77b4", width=1.2),
                fill="tonexty", fillcolor="rgba(31,119,180,0.10)",
            ), row=1, col=1)
            fig_h.add_trace(go.Scatter(
                x=df_hv["tarih_dt"], y=df_hv["temperature"],
                mode="lines", name="Gunluk Ort.",
                line=dict(color="#2ca02c", width=1.6),
            ), row=1, col=1)
            fig_h.add_trace(go.Bar(
                x=df_hv["tarih_dt"], y=df_hv["yagis_disp"],
                name="Yagis", marker_color="#aec7e8",
            ), row=2, col=1)
            fig_h.add_trace(go.Scatter(
                x=df_hv["tarih_dt"], y=df_hv["gdd"].cumsum(),
                mode="lines", name="GDD Kum.", line=dict(color="#9467bd", width=2),
            ), row=3, col=1)

            # Real don / sicak-stres markers driven by actual temperature value.
            don_rows = df_hv[df_hv["temperature"] < 0]
            if not don_rows.empty:
                fig_h.add_trace(go.Scatter(
                    x=don_rows["tarih_dt"], y=don_rows["temperature"],
                    mode="markers", name="Don Riski (T<0°C)",
                    marker=dict(color="blue", symbol="triangle-down", size=9),
                ), row=1, col=1)
            sicak_rows = df_hv[df_hv["temperature"] > 32]
            if not sicak_rows.empty:
                fig_h.add_trace(go.Scatter(
                    x=sicak_rows["tarih_dt"], y=sicak_rows["temperature"],
                    mode="markers", name="Sicak Stres (T>32°C)",
                    marker=dict(color="orange", symbol="triangle-up", size=9),
                ), row=1, col=1)

            fig_h.update_layout(
                height=500, margin=dict(t=30, b=20, l=55, r=20),
                legend=dict(orientation="h", y=1.05),
                hovermode="x unified",
            )
            st.plotly_chart(fig_h, use_container_width=True)

            if hava_stats.get("don_gun", 0) > 0:
                st.warning(f"❄️ {hava_stats['don_gun']} don gunu tespit edildi (grafikteki mavi ucgenler)")
            if hava_stats.get("sicak_gun", 0) > 0:
                st.warning(f"🌡️ {hava_stats['sicak_gun']} sicak stres gunu tespit edildi (turuncu ucgenler)")

    # ── 1D: Fenoloji ──────────────────────────────────────────────────────────
    st.subheader("🌾 Fenoloji ve Takvim")
    col1, col2 = st.columns(2)

    with col1:
        if fenoloji:
            kritik = "🔴 KRiTiK DONEM" if fenoloji.get("kritik_mi") else "🟢 Normal Donem"
            st.info(
                f"**Evre:** {fenoloji.get('evre', '?')}\n\n"
                f"**BBCH:** {fenoloji.get('bbch_aralik', '?')}\n\n"
                f"**Aciklama:** {fenoloji.get('aciklama', '?')}\n\n"
                f"{kritik}"
            )

    with col2:
        if ekim_degerlendirme:
            skor = ekim_degerlendirme.get("skor", 0)
            kategori = ekim_degerlendirme.get("kategori", "Bilinmiyor")
            st.metric("Ekim Penceresi Skoru", f"{skor}/100", delta=kategori)

    if sulama:
        if sulama.get("sulama_gerekli"):
            aciliyet = sulama.get("aciliyet", "ORTA")
            ikon = "🔴" if aciliyet == "ACIL" else "🟡"
            st.warning(
                f"{ikon} **Sulama:** {aciliyet} | "
                f"{sulama.get('miktar_ton_dekar', '?')} ton/da | "
                f"{sulama.get('zamanlama', '?')}\n\n"
                f"{sulama.get('gerekce', '')}"
            )
        else:
            st.success(f"💧 Sulama gerekmiyor: {sulama.get('gerekce', 'Nem seviyesi yeterli.')}")

    if gubre and gubre.get("gubre_zamani"):
        st.info(f"🌱 Gubreleme: {gubre.get('tip', '?')} — {gubre.get('doz', '?')}")

    # ── 1E: Oneriler ─────────────────────────────────────────────────────────
    st.subheader("💡 Aksiyon Onerileri")
    oneriler = []

    if son_kamera_bulgu:
        aksiyon = KDS_AKSIYONLAR.get(son_kamera_bulgu["camera_sinif"], {})
        oneriler.append({
            "renk": "error",
            "baslik": f"📷 Kamera: {son_kamera_bulgu['camera_sinif']}",
            "detay": aksiyon.get("tavsiye", "Uzman ile gorusun"),
            "aciliyet": aksiyon.get("aciliyet", "YUKSEK"),
        })

    if sulama and sulama.get("sulama_gerekli"):
        oneriler.append({
            "renk": "error" if sulama.get("aciliyet") == "ACIL" else "warning",
            "baslik": f"💧 Sulama Gerekiyor ({sulama.get('aciliyet','?')})",
            "detay": f"{sulama.get('miktar_ton_dekar','?')} ton/da — {sulama.get('zamanlama','')}",
            "aciliyet": sulama.get("aciliyet", "ORTA"),
        })

    if alerts:
        for al in alerts:
            oneriler.append({"renk": "warning", "baslik": "⚠️ Hava Uyarisi", "detay": al, "aciliyet": "ORTA"})

    if gubre and gubre.get("gubre_zamani"):
        oneriler.append({
            "renk": "info",
            "baslik": "🌱 Gubreleme Plani",
            "detay": f"{gubre.get('tip','')} — {gubre.get('doz','')}",
            "aciliyet": "PLANLI",
        })

    if ndvi_mevcut and ndvi_mevcut < 0.35:
        oneriler.append({
            "renk": "error",
            "baslik": "📉 Dusuk NDVI",
            "detay": f"NDVI {ndvi_mevcut:.3f} — Bitki sagligi kritik. Gozlem ve mudahale gerekebilir.",
            "aciliyet": "YUKSEK",
        })

    if not oneriler:
        st.success("✅ Kritik bir sorun tespit edilmedi. Rutin izleme yeterli.")
    else:
        for o in oneriler:
            fn = getattr(st, o["renk"])
            fn(f"**{o['baslik']}**\n\n{o['detay']}")

    # ── 1F: SHAP (varsa) ──────────────────────────────────────────────────────
    shap_data = son_tahmin.get("shap_ozet") if son_tahmin else None
    if shap_data:
        try:
            shap_dict = json.loads(shap_data) if isinstance(shap_data, str) else shap_data
            if shap_dict:
                st.subheader("🔬 Verim Faktoru Analizi (SHAP Top-5)")
                items = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
                df_shap = pd.DataFrame(items, columns=["Faktor", "SHAP Degeri"])
                colors = ["red" if v < 0 else "green" for _, v in items]
                fig_shap = go.Figure(go.Bar(
                    x=df_shap["SHAP Degeri"], y=df_shap["Faktor"],
                    orientation="h", marker_color=colors,
                ))
                fig_shap.update_layout(height=200, margin=dict(t=10, b=20, l=10, r=20))
                st.plotly_chart(fig_shap, use_container_width=True)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA 2: Rover Izleme
# ═══════════════════════════════════════════════════════════════════════════════

def page_rover(tarla_id: int, tarla: dict):
    st.header(f"📡 Rover Izleme — {tarla['isim']}")
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    crop_key = _crop_key(tarla)

    # ── 2A: Rover veri kaynagi (offline-first) ────────────────────────────────
    # Rover telemetrisi gercekte MQTT/CSV uzerinden DB'ye yazilir.
    # Mock simulation butonlari kaldirildi (v3 refactor).
    tum_asc = get_rover_olcumler_asc(tarla_id, limit=5000)
    if not tum_asc:
        st.info(
            "Bu tarla icin henuz rover olcumu yok. "
            "Olcumler MQTT/CSV ingestion ile veritabanina yazilir."
        )

    # Demo-mode visibility: if recent rows come from retrospective/feature-derived
    # ingest (no live rover + no real YOLO model), be transparent about it.
    if tum_asc:
        recent_sources = {str(r.get("kaynak", "")).lower()
                          for r in tum_asc[-20:] if r.get("kaynak")}
        is_demo = any(("feature_derived" in s) or ("backfill" in s)
                      or ("mock" in s) for s in recent_sources)
        if is_demo:
            try:
                from .shared.components import demo_mode_badge
                demo_mode_badge(
                    "Geriye dönük (ERA5 + Sentinel-2) — "
                    "canlı rover/YOLO yerine özellik türevli görüntü etiketi"
                )
            except Exception:                                   # noqa: BLE001
                pass

    # ── 2B: Son Rover Verileri ────────────────────────────────────────────────
    st.subheader("📋 Son Rover Verileri")
    olcumler_desc = list(reversed(tum_asc))[:20] if tum_asc else []

    if olcumler_desc:
        df_son = pd.DataFrame(olcumler_desc)
        df_son["Tarih"] = pd.to_datetime(df_son["timestamp"]).dt.strftime("%d %b %H:%M")
        df_son["Waypoint"] = df_son.get("waypoint_label", "—")
        df_son["Nem-1"] = df_son["humidity"].apply(lambda x: f"%{x:.1f}" if x else "—")
        df_son["Nem-2"] = df_son["soil_moisture"].apply(lambda x: f"%{x:.1f}" if x else "—")
        df_son["Sicaklik"] = df_son["temperature"].apply(lambda x: f"{x:.1f}°C" if x else "—")
        df_son["BBCH"] = df_son.get("bbch_sinif", "—")
        df_son["Kamera"] = df_son.apply(
            lambda r: f"📷 {r['camera_sinif']}" if r.get("camera_sinif") else "—", axis=1
        )
        df_son["Anomali"] = df_son["anomali_sayisi"].apply(
            lambda x: f"🔴 {int(x)}" if x and int(x) > 0 else "🟢 0"
        )
        display_cols = ["Tarih", "Waypoint", "Nem-1", "Nem-2", "Sicaklik", "BBCH", "Kamera", "Anomali"]
        st.dataframe(df_son[display_cols], use_container_width=True)
    else:
        st.info("Henuz rover olcumu yok.")

    # ── 2B-bis: Son Rover Goruntuleri ─────────────────────────────────────────
    goruntulu = [r for r in (list(reversed(tum_asc))[:50]) if r.get("image_path")]
    if goruntulu:
        st.subheader("📸 Son Rover Goruntuleri")
        cols_g = st.columns(4)
        for idx, olc in enumerate(goruntulu[:8]):
            img_path = olc["image_path"]
            col = cols_g[idx % 4]
            sinif = olc.get("camera_sinif", "")
            guven = (olc.get("camera_guven") or 0) * 100
            saglikli = sinif in ("saglikli_bugday", "saglikli_aycicegi")
            badge_color = "🟢" if saglikli else "🔴"
            label = f"{badge_color} {sinif} (%{guven:.0f})" if sinif else "—"
            if os.path.exists(img_path):
                col.image(img_path, caption=label, use_container_width=True)
            else:
                col.caption(f"📷 {label}\n_{str(olc.get('timestamp',''))[:16]}_")
    else:
        with st.expander("📸 Son Rover Goruntuleri", expanded=False):
            st.info("Goruntu iceren rover olcumu bulunamadi. Kamera modulu aktiflesince goruntuler burada listelenir.")

    # ── 2C: Frozen LSTM NDVI Tahmini vs Sentinel-2 Gercek NDVI ───────────────
    # Rationale: Frozen LSTM produces NDVI forecasts, not soil moisture; the
    # database has zero rover/ESP32 soil-moisture rows (all sensor_reading
    # entries are api_retrospective Sentinel-2/ERA5). The only legitimate
    # per-site model-vs-observation pairing we currently have is FLOV's
    # 7-day NDVI prediction vs Sentinel-2 ground truth from
    # reports/prospective/{site}_{year}_{validation.csv | predictions.parquet}.
    st.subheader("📈 Frozen LSTM NDVI Tahmini vs Sentinel-2 Gercek NDVI")
    research_id = (tarla.get("research_code") or tarla.get("evrenli_id")
                   or "EVR_01")
    year = int(st.session_state.get("research_year",
                                    datetime.now().year))

    try:
        from dashboard_pages.shared.data_loaders import (
            load_flov_predictions, load_flov_validation,
        )
    except Exception:                                                   # noqa: BLE001
        load_flov_predictions = None
        load_flov_validation = None

    val_df = pd.DataFrame()
    pred_df = pd.DataFrame()
    summary = None
    if load_flov_validation is not None:
        try:
            val_df, summary, _ = load_flov_validation(research_id, year)
        except Exception:                                               # noqa: BLE001
            val_df = pd.DataFrame()
    if val_df.empty and load_flov_predictions is not None:
        try:
            pred_df = load_flov_predictions(research_id, year)
        except Exception:                                               # noqa: BLE001
            pred_df = pd.DataFrame()

    df_src = val_df if not val_df.empty else pred_df
    has_actual = (not val_df.empty) and ("actual_ndvi" in val_df.columns)

    if df_src.empty:
        st.info(
            f"FLOV tahminleri bulunamadi ({research_id} / {year}). "
            f"Komut: `python scripts/predict_evr01.py --site {research_id} "
            f"--year {year}`"
        )
    else:
        # Build the chart (target_date axis so it lines up with observations)
        df_chart = df_src.copy()
        if "target_date" in df_chart.columns:
            df_chart["target_date"] = pd.to_datetime(df_chart["target_date"])
            df_chart = df_chart.sort_values("target_date")
            x_axis = df_chart["target_date"]
        else:
            x_axis = pd.to_datetime(df_chart["prediction_date"])

        fig_ndvi_cmp = go.Figure()
        fig_ndvi_cmp.add_trace(go.Scatter(
            x=x_axis, y=df_chart["predicted_ndvi"],
            mode="lines", name="Frozen LSTM Tahmini",
            line=dict(color="#1f77b4", width=2),
        ))
        if "climatology_ndvi" in df_chart.columns:
            fig_ndvi_cmp.add_trace(go.Scatter(
                x=x_axis, y=df_chart["climatology_ndvi"],
                mode="lines", name="Iklim ortalamasi (DOY)",
                line=dict(color="#7f7f7f", width=1, dash="dot"),
            ))
        if has_actual:
            fig_ndvi_cmp.add_trace(go.Scatter(
                x=df_chart["target_date"], y=df_chart["actual_ndvi"],
                mode="markers", name="Sentinel-2 Gercek NDVI",
                marker=dict(color="#2ca02c", size=6, symbol="circle"),
            ))
        fig_ndvi_cmp.update_layout(
            height=320, margin=dict(t=10, b=30, l=55, r=30),
            yaxis=dict(title="NDVI", range=[0, 1]),
            xaxis_title="Hedef Tarih",
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
        )
        st.plotly_chart(fig_ndvi_cmp, use_container_width=True)

        # Status thresholds — per-stage MAE in FLOV pipeline is ~0.07 NDVI,
        # so |delta| > 0.10 (~1.4 sigma) is a real deviation, > 0.20 (~3 sigma)
        # is critical.
        def _status(delta: float) -> str:
            if delta is None or pd.isna(delta):
                return "—"
            ad = abs(delta)
            if ad > 0.20:
                return "🔴 KRITIK"
            if ad > 0.10:
                return "🟡 SAPMA"
            return "🟢 NORMAL"

        # Provenance caption — show what the user is actually looking at.
        try:
            from prospective_validation.model_loader import load_frozen_champion
            _sha_short = (load_frozen_champion().sha256[:16])
        except Exception:                                               # noqa: BLE001
            _sha_short = "n/a"
        src_label = ("validation.csv" if has_actual else "predictions.parquet")
        st.caption(
            f"Veri kaynaklari: **Frozen LSTM** (sha256 `{_sha_short}`) · "
            f"**Sentinel-2 NDVI** (GEE) · `reports/prospective/{research_id}_{year}_{src_label}` · "
            f"Per-stage R²=0.76–0.79, MAE≈0.07"
        )

        if summary:
            mae = summary.get("mae") or summary.get("MAE")
            r2 = summary.get("r2") or summary.get("R2")
            bias = summary.get("bias")
            n_pts = summary.get("n") or summary.get("n_samples")
            cols_m = st.columns(4)
            if n_pts is not None:
                cols_m[0].metric("Eslesen gozlem", int(n_pts))
            if mae is not None:
                cols_m[1].metric("MAE", f"{float(mae):.3f}")
            if r2 is not None:
                cols_m[2].metric("R²", f"{float(r2):.3f}")
            if bias is not None:
                cols_m[3].metric("Bias", f"{float(bias):+.3f}")

        # Last 10 — pick most recent rows in target_date order
        if has_actual:
            son10 = df_chart.tail(10).copy()
            son10["delta"] = son10["actual_ndvi"] - son10["predicted_ndvi"]
            son10["Tarih"] = son10["target_date"].dt.strftime("%d %b %Y")
            son10["Tahmin NDVI"] = son10["predicted_ndvi"].apply(lambda x: f"{x:.3f}")
            son10["Gercek NDVI"] = son10["actual_ndvi"].apply(
                lambda x: f"{x:.3f}" if pd.notna(x) else "—"
            )
            son10["Fark"] = son10["delta"].apply(
                lambda x: f"{x:+.3f}" if pd.notna(x) else "—"
            )
            son10["Durum"] = son10["delta"].apply(_status)
            st.dataframe(
                son10[["Tarih", "Tahmin NDVI", "Gercek NDVI", "Fark", "Durum"]],
                use_container_width=True, hide_index=True,
            )
        else:
            # Forward-only predictions parquet: no actuals yet for this year.
            son10 = df_chart.tail(10).copy()
            son10["Tarih"] = pd.to_datetime(son10["target_date"]).dt.strftime("%d %b %Y") \
                if "target_date" in son10.columns else ""
            son10["Tahmin NDVI"] = son10["predicted_ndvi"].apply(lambda x: f"{x:.3f}")
            if "anomaly_vs_climatology" in son10.columns:
                son10["Iklim Anomalisi"] = son10["anomaly_vs_climatology"].apply(
                    lambda x: f"{x:+.3f}" if pd.notna(x) else "—"
                )
                son10["Durum"] = son10["anomaly_vs_climatology"].apply(_status)
                cols_show = ["Tarih", "Tahmin NDVI", "Iklim Anomalisi", "Durum"]
            else:
                cols_show = ["Tarih", "Tahmin NDVI"]
            st.dataframe(son10[cols_show], use_container_width=True,
                         hide_index=True)
            st.caption(
                f"Not: {year} icin Sentinel-2 gercek NDVI henuz birikmedi; "
                f"yalnizca tahmin + iklim baseline gosteriliyor. "
                f"Yil sonunda `validate_evr01.py` ile actual eslestirilecek."
            )

    # ── 2D: Anomali Gecmisi ───────────────────────────────────────────────────
    st.subheader("⚠️ Anomali Gecmisi")
    anomalili = [r for r in reversed(tum_asc) if r.get("anomali_sayisi", 0) > 0]
    if anomalili:
        for ano in anomalili:
            with st.expander(
                f"🔴 {ano['timestamp']} — {ano.get('waypoint_label','?')} "
                f"({ano['anomali_sayisi']} anomali)"
            ):
                if ano.get("anomaliler"):
                    try:
                        for a in json.loads(ano["anomaliler"]):
                            st.warning(a)
                    except Exception:
                        st.warning(ano["anomaliler"])

                if ano.get("kds_tavsiye"):
                    st.info(f"💡 KDS Tavsiyesi: {ano['kds_tavsiye']}")

                # Kamera tespiti
                cam_sinif = ano.get("camera_sinif") or ano.get("hastalik")
                cam_guven = ano.get("camera_guven") or ano.get("hastalik_guven") or 0.0
                if cam_sinif:
                    aksiyon = KDS_AKSIYONLAR.get(cam_sinif, {})
                    st.error(
                        f"📷 Kamera Tespiti: **{cam_sinif}** (%{cam_guven*100:.0f} guven) — "
                        f"{aksiyon.get('tavsiye', '')}"
                    )

                img_path = ano.get("image_path")
                if img_path and os.path.exists(img_path):
                    st.image(img_path, caption=f"Rover goruntusu — {ano.get('waypoint_label','?')}", width=320)
    else:
        st.success("Bu tarla icin kayitli anomali yok.")

    # ── 2E: GPS Haritasi ──────────────────────────────────────────────────────
    st.subheader("🗺️ Waypoint Haritasi")
    try:
        import folium
        from streamlit_folium import st_folium
        center = [tarla["konum_lat"], tarla["konum_lon"]]
        m = folium.Map(location=center, zoom_start=14)
        folium.Marker(center, popup=tarla["isim"],
                      icon=folium.Icon(color="blue", icon="home")).add_to(m)
        for olc in list(reversed(tum_asc)):
            lat = olc.get("gps_lat") or tarla["konum_lat"]
            lon = olc.get("gps_lon") or tarla["konum_lon"]
            color = "red" if olc.get("anomali_sayisi", 0) > 0 else "green"
            popup_txt = (
                f"{olc.get('waypoint_label','?')} | {str(olc.get('timestamp','?'))[:10]}<br>"
                f"Nem: %{olc.get('humidity','?')} | Sic: {olc.get('temperature','?')}°C"
            )
            if olc.get("camera_sinif"):
                popup_txt += f"<br>Kamera: {olc['camera_sinif']}"
            elif olc.get("hastalik"):
                popup_txt += f"<br>Hastalik: {olc['hastalik']}"
            folium.CircleMarker(
                [lat, lon], radius=8, color=color, fill=True, fill_opacity=0.8,
                popup=folium.Popup(popup_txt, max_width=200),
            ).add_to(m)
        st_folium(m, height=420, use_container_width=True)
    except ImportError:
        st.info("Harita icin: `pip install folium streamlit-folium`")

    # ── 2F: istatistikler ─────────────────────────────────────────────────────
    st.subheader("📈 Rover istatistikleri")
    tum_desc = list(reversed(tum_asc))
    if tum_desc:
        toplam = len(tum_desc)
        anomali_n = sum(1 for r in tum_desc if r.get("anomali_sayisi", 0) > 0)
        nem_values = [r.get("humidity") or 0 for r in tum_desc]
        ort_nem = sum(nem_values) / toplam if toplam > 0 else 0
        son_ts = tum_desc[0].get("timestamp", "?")[:16]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Tarama", toplam)
        c2.metric("Anomali Orani", f"%{anomali_n/toplam*100:.0f}")
        c3.metric("Ort. Nem", f"%{ort_nem:.1f}")
        c4.metric("Son Tarama", son_ts)
    else:
        st.info("Istatistik icin veri yok.")


# ═══════════════════════════════════════════════════════════════════════════════
# SAYFA 3: Tarim Asistani (Chat)
# ═══════════════════════════════════════════════════════════════════════════════

def page_chat(tarla_id: int, tarla: dict):
    st.header("💬 Tarim Asistani")

    if not _LLM_OK:
        st.error("LLM modulu yuklenemedi. `src/cp4_rag/llm_engine.py` kontrol edin.")
        return

    # Demo-mode visibility — if RAG index is missing, answers are plain LLM
    if not _FAISS_OK:
        try:
            from .shared.components import demo_mode_badge
            demo_mode_badge("RAG indeksi yok — yanıtlar düz LLM (kaynak gösterimi devre dışı)")
        except Exception:                                       # noqa: BLE001
            pass

    # Session state baslat
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "rag_sources" not in st.session_state:
        st.session_state["rag_sources"] = {}

    # ── Sidebar: Ornek Sorular ────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("**Ornek Sorular**")
        ornek_sorular = [
            "Tarlam nasil?",
            "Detayli tarla raporu yaz",
            "Bugday verimim ne olur?",
            "Su vermem lazim mi?",
            "Mildiyo tedavisi nedir?",
            "Ekim zamani mi?",
        ]
        for soru in ornek_sorular:
            if st.button(soru, key=f"ornek_{soru}", use_container_width=True):
                st.session_state["pending_question"] = soru

    # ── Gecmis mesajlari goster ───────────────────────────────────────────────
    for i, msg in enumerate(st.session_state["chat_history"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and i in st.session_state.get("rag_sources", {}):
                meta = st.session_state["rag_sources"][i]
                badge_map = {"VERI": "📊 VERi", "BILGI": "📚 BiLGi", "GENEL": "💬 GENEL"}
                qtype = meta.get("query_type", "GENEL")
                st.caption(
                    f"{badge_map.get(qtype, qtype)} | "
                    f"Sure: {meta.get('elapsed', 0):.1f}s"
                )
                if meta.get("sources"):
                    with st.expander(f"📚 Kaynak Belgeler ({len(meta['sources'])} chunk)"):
                        for s in meta["sources"]:
                            src = s.get("source", "?")
                            txt = s.get("text", "")[:200]
                            score = s.get("score", 0)
                            st.markdown(f"**{src}** (skor: {score:.3f})\n\n{txt}…")

    # ── Kullanici girisi ──────────────────────────────────────────────────────
    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input("Tarlaniz hakkinda bir soru sorun…") or pending

    if user_input:
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Dusunuyor…"):
                t0 = datetime.now()
                try:
                    result = generate_chat_response(
                        user_question=user_input,
                        vectorstore=_vectorstore if _FAISS_OK else None,
                        chunks=_chunks if _FAISS_OK else [],
                    )
                    answer = result.get("answer") or result.get("response") or result.get("text") or "Yanit uretilmedi."
                    elapsed = (datetime.now() - t0).total_seconds()
                    query_type = result.get("query_type", "GENEL")
                    sources = result.get("sources", [])
                except Exception as e:
                    answer = f"Hata olustu: {e}"
                    elapsed = 0
                    query_type = "GENEL"
                    sources = []

                st.markdown(answer)
                badge_map = {"VERI": "📊 VERi", "BILGI": "📚 BiLGi", "GENEL": "💬 GENEL"}
                st.caption(
                    f"{badge_map.get(query_type, query_type)} | "
                    f"Sure: {elapsed:.1f}s"
                )
                if sources:
                    with st.expander(f"📚 Kaynak Belgeler ({len(sources)} chunk)"):
                        for s in sources:
                            src = s.get("source", "?")
                            txt = s.get("text", "")[:200]
                            score = s.get("score", 0)
                            st.markdown(f"**{src}** (skor: {score:.3f})\n\n{txt}…")

        msg_idx = len(st.session_state["chat_history"])
        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
        st.session_state["rag_sources"][msg_idx] = {
            "query_type": query_type,
            "elapsed": elapsed,
            "sources": sources,
        }
        st.rerun()

    # ── Aktif Veri Baglamı expander ───────────────────────────────────────────
    with st.expander("📊 Aktif Veri Baglamı (LLM'e ne besleniyor)"):
        if _LLM_OK:
            try:
                ctx = build_rich_context()
                st.code(ctx, language="markdown")
            except Exception as e:
                st.warning(f"Baglam olusturulamadi: {e}")
        else:
            st.info("LLM modulu aktif degil.")

    # Chat gecmisini temizle butonu
    if st.session_state["chat_history"] and st.button("🗑️ Sohbeti Temizle"):
        st.session_state["chat_history"] = []
        st.session_state["rag_sources"] = {}
        st.rerun()


__all__ = [
    "render_sidebar",
    "page_tarla",
    "page_rover",
    "page_chat",
    "KDS_AKSIYONLAR",
    "_LLM_OK", "_FAISS_OK", "_YOLO_OK", "_WEATHER_OK", "_AGRO_OK",
]
