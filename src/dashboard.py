"""
TRAK-AI KDS — Streamlit Web Arayüzü
=====================================
3 sayfalı web dashboard.

Kullanım: streamlit run src/dashboard.py
"""
import sys
import os
import gc
import json
import time
import threading
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import paho.mqtt.client as mqtt
import folium
from streamlit_folium import st_folium

# ── Path ayarları (demo.py referans alınarak) ──────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
CP4_DIR = os.path.join(PROJECT_ROOT, "src", "cp4_rag")
sys.path.insert(0, CP2_DIR)
sys.path.insert(0, CP4_DIR)

from config import OLLAMA_MODEL
from build_index import load_faiss_index
from retriever import tri_rag_retrieve, format_context
from llm_engine import check_ollama_connection, rag_query

# Hava servisi (src/ altında — isteğe bağlı)
try:
    from weather_service import (
        get_current_weather,
        get_7day_forecast,
        get_weather_alerts,
    )
    _WEATHER_AVAILABLE = True
except ImportError:
    _WEATHER_AVAILABLE = False

# Agronomik takvim (src/ altında — isteğe bağlı)
try:
    from agro_calendar import (
        get_current_phenology,
        evaluate_planting_window,
        get_irrigation_advice,
        get_fertilization_advice,
        BUGDAY_TAKVIM,
        AYCICEGI_TAKVIM,
    )
    _AGRO_AVAILABLE = True
except ImportError:
    _AGRO_AVAILABLE = False

# ── Sabitler ──────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(PROJECT_ROOT, "data", "processed",
                        "master_feature_matrix_2017_2024.csv")
MQTT_BROKER = "localhost"
MQTT_PORT   = 1883
DEFAULT_LAT = 41.6940
DEFAULT_LON = 27.1050

SENARYO_A = {
    "timestamp": 0,
    "gps_lat": DEFAULT_LAT, "gps_lon": DEFAULT_LON, "gps_valid": True,
    "nem_1_pct": 28.0, "nem_2_pct": 26.5,
    "hava_temp_c": 20.5, "hava_nem_pct": 62.0,
    "engel_on_cm": 200, "engel_arka_cm": 999,
    "bbch_sinif": "BBCH_50_59", "bbch_guven": 0.88,
    "waypoint_id": 1, "rover_id": "trak-ai-rover-01",
}
SENARYO_B = {
    "timestamp": 0,
    "gps_lat": DEFAULT_LAT, "gps_lon": DEFAULT_LON, "gps_valid": True,
    "nem_1_pct": 11.0, "nem_2_pct": 28.0,
    "hava_temp_c": 28.5, "hava_nem_pct": 45.0,
    "engel_on_cm": 120, "engel_arka_cm": 999,
    "bbch_sinif": "BBCH_10_19", "bbch_guven": 0.71,
    "hastalik": "Mildiyö", "hastalik_guven": 0.82,
    "waypoint_id": 3, "rover_id": "trak-ai-rover-01",
}

FEATURE_LABELS = {
    "NDVI_trend_7d": "NDVI Trend (7g)",
    "drought_index_7d": "Kuraklık İndeksi",
    "NDVI_int": "NDVI",
    "GDD_cum": "Birikimli GDD",
    "tp_sum": "Yağış",
    "ssr_sum": "Güneş Radyasyonu",
    "t2m_mean": "Ortalama Sıcaklık",
    "EVI_int": "EVI",
    "GDD": "GDD",
    "dew_depression": "Çiğ Noktası Farkı",
}

# ── Sayfa yapılandırması (ilk Streamlit çağrısı) ───────────────────────────
st.set_page_config(
    page_title="TRAK-AIA KDS",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state başlatma ─────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "rover_data" not in st.session_state:
    st.session_state.rover_data = None
if "advisory_data" not in st.session_state:
    st.session_state.advisory_data = None
if "mqtt_status" not in st.session_state:
    st.session_state.mqtt_status = "Bağlı değil"


# ══════════════════════════════════════════════════════════════════════════
# Önbellekli kaynak yükleyiciler
# ══════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="FAISS indeksi yükleniyor (14.866 vektör)...")
def get_faiss():
    vs, ch = load_faiss_index()
    return vs, ch


@st.cache_data(ttl=300, show_spinner="CP-2 modeli tahmin yapıyor...")
def get_cp2_prediction(crop: str):
    from inference_cp2 import predict
    result = predict(crop)
    gc.collect()
    return result


@st.cache_data(show_spinner=False)
def get_ndvi_history(n: int = 30):
    if not os.path.exists(CSV_PATH):
        return None
    df = pd.read_csv(CSV_PATH)
    return df[["date", "NDVI_int", "t2m_mean", "tp_sum", "ssr_sum"]].tail(n).reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner=False)
def get_weather():
    if not _WEATHER_AVAILABLE:
        return None, None
    cur = get_current_weather()
    fc  = get_7day_forecast()
    return cur, fc


@st.cache_data(ttl=60, show_spinner=False)
def get_ollama_status():
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return True, models
    except Exception:
        pass
    return False, []


@st.cache_data(ttl=300, show_spinner="Tarla verileri derleniyor...")
def get_rich_context() -> str:
    """CP-2 tahminleri + hava + agronomik takvim bağlamını önbellekli olarak döndürür (5 dk TTL)."""
    from llm_engine import build_rich_context
    return build_rich_context()


# ══════════════════════════════════════════════════════════════════════════
# MQTT yardımcıları
# ══════════════════════════════════════════════════════════════════════════

def mqtt_publish(payload: dict) -> bool:
    payload = dict(payload)
    payload["timestamp"] = int(time.time())
    try:
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except AttributeError:
            c = mqtt.Client()
        c.connect(MQTT_BROKER, MQTT_PORT, keepalive=10)
        c.loop_start()
        c.publish("trakaia/rover/data", json.dumps(payload, ensure_ascii=False))
        time.sleep(0.3)
        c.loop_stop()
        c.disconnect()
        return True
    except Exception:
        return False


def mqtt_wait_advisory(timeout: int = 90) -> dict | None:
    result = [None]
    done = threading.Event()

    def _on_connect(client, userdata, flags, rc):
        client.subscribe("trakaia/kds/advisory")

    def _on_message(client, userdata, msg):
        try:
            result[0] = json.loads(msg.payload.decode("utf-8"))
            done.set()
        except Exception:
            pass

    try:
        try:
            c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except AttributeError:
            c = mqtt.Client()
        c.on_connect = _on_connect
        c.on_message = _on_message
        c.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        c.loop_start()
        done.wait(timeout=timeout)
        c.loop_stop()
        c.disconnect()
    except Exception:
        pass
    return result[0]


# ══════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/1px.png",
            width=1,
        )
        st.markdown("## 🌾 TRAK-AIA KDS")
        st.markdown("**TÜBİTAK 2209-A**  \nIşık Üniversitesi • 2026")
        st.divider()

        page = st.radio(
            "Sayfa",
            ["🌿 Tarla Durumu", "📡 Rover İzleme", "💬 Tarım Asistanı"],
            label_visibility="collapsed",
        )
        st.divider()

        # Ollama durumu
        ollama_ok, models = get_ollama_status()
        if ollama_ok:
            st.success(f"🟢 Ollama bağlı — {OLLAMA_MODEL}")
        else:
            st.error("🔴 Ollama bağlantı yok")

        # FAISS durumu
        vs, ch = get_faiss()
        if vs is not None:
            st.success(f"✅ FAISS — {len(ch):,} vektör yüklü")
        else:
            st.error("❌ FAISS yüklenmedi")

        st.divider()
        st.caption("Veri: Kırklareli-Vize pilot tarlası  \n41.694°N 27.105°E")

    return page


# ══════════════════════════════════════════════════════════════════════════
# Ortak başlık
# ══════════════════════════════════════════════════════════════════════════

def render_header(subtitle: str):
    st.markdown(
        "<h2 style='margin-bottom:0'>🌾 TRAK-AIA Akıllı Tarım Karar Destek Sistemi</h2>",
        unsafe_allow_html=True,
    )
    st.caption(subtitle)
    st.divider()


# ══════════════════════════════════════════════════════════════════════════
# SAYFA 1 — Tarla Durumu
# ══════════════════════════════════════════════════════════════════════════

def _health_color(status: str) -> str:
    s = status.upper()
    if s in ("CRITICAL", "LOW"):
        return "#e53935"
    if s in ("MODERATE",):
        return "#fb8c00"
    return "#43a047"


def _health_emoji(status: str) -> str:
    s = status.upper()
    if s in ("CRITICAL", "LOW"):
        return "🔴"
    if s in ("MODERATE",):
        return "🟡"
    return "🟢"


def _trend_emoji(trend: str) -> str:
    t = trend.upper()
    if "DECLINING" in t:
        return "📉"
    if "GROWING" in t:
        return "📈"
    return "➡️"


def page_tarla_durumu():
    render_header("Model tahminleri ve tarla sağlık analizi")

    col_w, col_s = st.columns(2)

    crops = [("Wheat", "🌾 Buğday", col_w), ("Sunflower", "🌻 Ayçiçeği", col_s)]

    for crop_key, crop_label, col in crops:
        with col:
            with st.spinner(f"{crop_label} tahmin ediliyor..."):
                try:
                    pred = get_cp2_prediction(crop_key)
                    ok = True
                except Exception as e:
                    ok = False
                    err = str(e)

            if not ok:
                st.error(f"{crop_label}: Model yüklenemedi — {err}")
                continue

            health = pred["health"]
            trend  = pred["trend"]
            color  = _health_color(health["status"])
            emoji  = _health_emoji(health["status"])
            temoji = _trend_emoji(trend["trend"])

            st.markdown(f"### {crop_label}")
            st.markdown(
                f"""<div style="background:{color}22;border-left:4px solid {color};
                padding:12px;border-radius:6px;margin-bottom:8px">
                <span style="font-size:1.4em">{emoji} <b>{health['status']}</b></span><br>
                <span style="color:#555">{health['desc']}</span><br>
                <b>Tavsiye:</b> {health['action']}
                </div>""",
                unsafe_allow_html=True,
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Mevcut NDVI", f"{pred['current_ndvi']:.4f}")
            m2.metric("Tahmin (t+7)", f"{pred['predicted_ndvi']:.4f}",
                      delta=f"{trend['delta']:+.4f}")
            m3.metric("Trend", f"{temoji} {trend['trend']}")

            with st.expander("Model detayları"):
                st.caption(
                    f"**Model:** {pred['model_used']}  \n"
                    f"**Mimari:** {pred['architecture']}  \n"
                    f"**Veri kaynağı:** {pred['data_source']}"
                )
                st.info(trend["alert"])

    st.divider()

    # ── NDVI Trend Grafiği ────────────────────────────────────────────────
    st.subheader("📊 Son 30 Günlük NDVI Trendi")
    hist = get_ndvi_history(30)
    if hist is not None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist["date"], y=hist["NDVI_int"],
            mode="lines+markers", name="NDVI (interpolated)",
            line=dict(color="#388e3c", width=2),
            marker=dict(size=5),
        ))
        # Sağlık eşik çizgileri
        for y_val, label, color in [
            (0.15, "Kritik", "#e53935"),
            (0.40, "Ortalama", "#fb8c00"),
            (0.70, "İyi", "#43a047"),
        ]:
            fig.add_hline(y=y_val, line_dash="dot", line_color=color,
                          annotation_text=label, annotation_position="right")
        fig.update_layout(
            height=300, margin=dict(t=20, b=20, l=0, r=80),
            xaxis_title="Tarih", yaxis_title="NDVI",
            yaxis=dict(range=[0, 1]),
            plot_bgcolor="#fafafa",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Veri dosyası bulunamadı.")

    st.divider()

    # ── İklim Özeti ───────────────────────────────────────────────────────
    st.subheader("🌡️ Son 15 Günlük İklim Özeti")
    clim = get_ndvi_history(15)
    if clim is not None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ort. Sıcaklık",
                  f"{clim['t2m_mean'].mean():.1f} °C")
        c2.metric("Toplam Yağış",
                  f"{clim['tp_sum'].sum():.1f} mm")
        c3.metric("Güneş Radyasyonu",
                  f"{clim['ssr_sum'].mean()/1e6:.1f} MJ/m²")
        c4.metric("Veri Dönemi",
                  f"{clim['date'].iloc[0]} – {clim['date'].iloc[-1]}")

    st.divider()

    # ── Hava Durumu (Open-Meteo) ──────────────────────────────────────────
    st.subheader("🌤️ 7 Günlük Hava Tahmini")
    wx_cur, wx_fc = get_weather()

    if wx_cur:
        wc1, wc2, wc3, wc4 = st.columns(4)
        wc1.metric("🌡️ Anlık Sıcaklık", f"{wx_cur['temp_c']:.1f} °C")
        wc2.metric("💧 Nem", f"%{wx_cur['humidity']:.0f}")
        wc3.metric("💨 Rüzgar", f"{wx_cur['wind_kmh']:.0f} km/h")
        wc4.metric("🌱 Toprak Sıcaklığı", f"{wx_cur['soil_temp_c']:.1f} °C")

    if wx_fc:
        alerts = get_weather_alerts(wx_fc)
        for alert in alerts:
            if alert["level"] == "error":
                st.error(f"⚠️ {alert['text']}")
            else:
                st.warning(f"⚠️ {alert['text']}")

        fc_df = pd.DataFrame(wx_fc)
        fig_wx = go.Figure()
        fig_wx.add_trace(go.Bar(
            name="Yağış (mm)", x=fc_df["date"], y=fc_df["precip_mm"],
            marker_color="#1565c0", opacity=0.7, yaxis="y2",
        ))
        fig_wx.add_trace(go.Scatter(
            name="Maks °C", x=fc_df["date"], y=fc_df["temp_max"],
            mode="lines+markers", line=dict(color="#e53935", width=2),
        ))
        fig_wx.add_trace(go.Scatter(
            name="Min °C", x=fc_df["date"], y=fc_df["temp_min"],
            mode="lines+markers", line=dict(color="#1565c0", width=2, dash="dot"),
        ))
        fig_wx.update_layout(
            height=280, margin=dict(t=10, b=10, l=0, r=60),
            plot_bgcolor="#fafafa",
            legend=dict(orientation="h", y=1.1),
            yaxis=dict(title="Sıcaklık (°C)"),
            yaxis2=dict(title="Yağış (mm)", overlaying="y",
                        side="right", showgrid=False),
        )
        st.plotly_chart(fig_wx, use_container_width=True)
    elif not _WEATHER_AVAILABLE:
        st.info("Hava servisi bulunamadı (weather_service.py eksik).")
    else:
        st.warning("Open-Meteo API'ye erişilemiyor (offline mod).")

    st.divider()

    # ── SHAP Feature Importance (statik) ─────────────────────────────────
    st.subheader("🔍 Özellik Önemi (SHAP — Buğday Conv-LSTM)")
    features_ranked = [
        ("NDVI_trend_7d", 0.31),
        ("drought_index_7d", 0.22),
        ("NDVI_int", 0.17),
        ("GDD_cum", 0.11),
        ("tp_sum", 0.08),
        ("ssr_sum", 0.06),
        ("t2m_mean", 0.03),
        ("EVI_int", 0.02),
    ]
    feat_df = pd.DataFrame(features_ranked, columns=["Özellik", "SHAP Değeri"])
    feat_df["Özellik"] = feat_df["Özellik"].map(
        lambda x: FEATURE_LABELS.get(x, x)
    )
    fig2 = go.Figure(go.Bar(
        x=feat_df["SHAP Değeri"], y=feat_df["Özellik"],
        orientation="h", marker_color="#1565c0",
    ))
    fig2.update_layout(
        height=280, margin=dict(t=10, b=10, l=0, r=20),
        xaxis_title="Ortalama |SHAP| değeri",
        plot_bgcolor="#fafafa",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig2, use_container_width=True)

    if not _AGRO_AVAILABLE:
        return

    st.divider()

    # ── Agronomik Takvim ──────────────────────────────────────────────────
    st.subheader("🌱 Agronomik Takvim")
    wx_cur2, wx_fc2 = get_weather() if _WEATHER_AVAILABLE else (None, None)
    now_month = datetime.now().month

    col_w, col_s = st.columns(2)

    _EVRE_EMOJI = {
        "ekim_cimlenme": "🌱", "kardeslenme": "🌿", "sapa_kalkma": "🌾",
        "basaklanma": "🌾", "ciceklenme": "🌸", "dane_dolumu": "🌾",
        "olgunlasma": "🟡", "cimlenme": "🌱", "yaprak": "🍃",
        "sap_uzamasi": "📏", "tabla_olusumu": "🌻", "dane_dolumu": "🌻",
        "ara_donem": "💤",
    }

    for col, crop, takvim in [
        (col_w, "Wheat", BUGDAY_TAKVIM),
        (col_s, "Sunflower", AYCICEGI_TAKVIM),
    ]:
        with col:
            st.markdown(f"**{'🌾 Buğday' if crop == 'Wheat' else '🌻 Ayçiçeği'}**")
            fen = get_current_phenology(crop, now_month)
            emoji = _EVRE_EMOJI.get(fen["evre"], "🔵")
            kritik_badge = " 🔴 KRİTİK" if fen["kritik_mi"] else ""
            st.markdown(f"{emoji} **{fen['aciklama']}**{kritik_badge}")
            st.caption(f"BBCH {fen['bbch_aralik']}")

            # Ekim penceresi
            ekim_bas = takvim["ekim_ay_baslangic"]
            ekim_bit = takvim["ekim_ay_bitis"]
            if ekim_bas <= ekim_bit:
                in_ekim = ekim_bas <= now_month <= ekim_bit
            else:
                in_ekim = now_month >= ekim_bas or now_month <= ekim_bit

            if in_ekim and wx_cur2:
                ekim = evaluate_planting_window(crop, wx_cur2, wx_fc2)
                ekim_color = "🟢" if ekim["ekim_uygun"] else "🔴"
                st.metric("Ekim Penceresi", f"{ekim_color} {ekim['skor']}/100", ekim["gerekce"][:60])
            elif in_ekim:
                st.metric("Ekim Penceresi", "⚪ Hava verisi yok", "")
            else:
                st.metric("Ekim Penceresi", "⬜ Dönem değil", f"Ekim: {ekim_bas}-{ekim_bit}. ay")

            # Sulama tavsiyesi
            soil_m = wx_cur2.get("soil_moisture", 30) if wx_cur2 else 30
            sulama = get_irrigation_advice(crop, now_month, soil_m, wx_fc2)
            acil_color = {"ACIL": "🔴", "PLANLI": "🟡", "GEREKSIZ": "🟢"}.get(sulama["aciliyet"], "⚪")
            st.metric(
                "Sulama",
                f"{acil_color} {sulama['aciliyet']}",
                f"{sulama['miktar_ton_dekar']} ton/dekar — {sulama['zamanlama']}" if sulama["sulama_gerekli"] else sulama["gerekce"][:55],
            )

            # Gübreleme
            gubre = get_fertilization_advice(crop, now_month)
            if gubre["gubre_zamani"]:
                st.info(f"🌿 **Gübreleme:** {gubre['aciklama']}")

    # Yıllık fenoloji takvimi (Plotly timeline)
    st.markdown("**Yıllık Fenoloji Takvimi**")
    month_labels = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

    wheat_palette = ["#e3f2fd", "#bbdefb", "#90caf9", "#64b5f6", "#42a5f5", "#2196f3", "#1565c0"]
    sun_palette   = ["#fff8e1", "#ffecb3", "#ffe082", "#ffd54f", "#ffca28", "#ffc107", "#e65100"]

    fig_pheno = go.Figure()

    for crop_label, takvim_data, palette in [
        ("🌾 Buğday", BUGDAY_TAKVIM, wheat_palette),
        ("🌻 Ayçiçeği", AYCICEGI_TAKVIM, sun_palette),
    ]:
        for i, (evre_adi, evre) in enumerate(takvim_data["fenoloji"].items()):
            months = sorted(evre["ay"])
            color = palette[i % len(palette)]

            # Build contiguous month ranges
            ranges = []
            if months:
                s, e = months[0], months[0]
                for m in months[1:]:
                    if m == e + 1:
                        e = m
                    else:
                        ranges.append((s, e))
                        s = e = m
                ranges.append((s, e))

            for s_m, e_m in ranges:
                active = s_m <= now_month <= e_m
                fig_pheno.add_trace(go.Bar(
                    x=[e_m - s_m + 1],
                    y=[crop_label],
                    base=[s_m - 1],
                    orientation="h",
                    marker_color="#ff5722" if active else color,
                    marker_line_width=0.5,
                    marker_line_color="white",
                    hovertemplate=(
                        f"<b>{evre['aciklama']}</b><br>"
                        f"BBCH: {evre['bbch']}<br>"
                        f"Ay: {month_labels[s_m-1]}"
                        + (f"–{month_labels[e_m-1]}" if s_m != e_m else "")
                        + "<extra></extra>"
                    ),
                    showlegend=False,
                ))

    fig_pheno.add_vline(
        x=now_month - 0.5,
        line_dash="dash",
        line_color="#d32f2f",
        line_width=2,
        annotation_text=f"▼ {month_labels[now_month - 1]}",
        annotation_position="top right",
        annotation_font_color="#d32f2f",
    )
    fig_pheno.update_layout(
        barmode="overlay",
        height=180,
        margin=dict(t=30, b=20, l=10, r=10),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(12)),
            ticktext=month_labels,
            range=[-0.5, 11.5],
        ),
        plot_bgcolor="#fafafa",
        paper_bgcolor="white",
        bargap=0.25,
    )
    st.plotly_chart(fig_pheno, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# SAYFA 2 — Rover İzleme
# ══════════════════════════════════════════════════════════════════════════

def page_rover_izleme():
    render_header("Otonom IoT Sensör Gezgini — ÇP-3")

    # ── Test butonları ────────────────────────────────────────────────────
    st.subheader("📤 Mock Veri Gönder")
    b1, b2 = st.columns(2)

    with b1:
        if st.button("🟢 Senaryo A — Normal Tarla", use_container_width=True):
            ok = mqtt_publish(SENARYO_A)
            if ok:
                st.session_state.rover_data = dict(SENARYO_A)
                st.session_state.advisory_data = None
                st.success("Senaryo A gönderildi. Orchestrator işliyor...")
                with st.spinner("Tavsiye bekleniyor (maks. 90 sn)..."):
                    adv = mqtt_wait_advisory(90)
                if adv:
                    st.session_state.advisory_data = adv
                    st.rerun()
            else:
                st.error("MQTT broker'a bağlanılamadı (Mosquitto çalışıyor mu?)")

    with b2:
        if st.button("🔴 Senaryo B — Çoklu Anomali", use_container_width=True):
            ok = mqtt_publish(SENARYO_B)
            if ok:
                st.session_state.rover_data = dict(SENARYO_B)
                st.session_state.advisory_data = None
                st.success("Senaryo B gönderildi. Orchestrator işliyor...")
                with st.spinner("LLM tavsiye üretiyor (maks. 90 sn)..."):
                    adv = mqtt_wait_advisory(90)
                if adv:
                    st.session_state.advisory_data = adv
                    st.rerun()
            else:
                st.error("MQTT broker'a bağlanılamadı (Mosquitto çalışıyor mu?)")

    st.divider()

    # ── Son sensör verisi ─────────────────────────────────────────────────
    rover = st.session_state.rover_data
    adv   = st.session_state.advisory_data

    st.subheader("📟 Son Rover Verisi")

    if rover is None:
        st.info("Henüz veri yok. Yukarıdaki butonlardan test verisi gönderin.")
        lat, lon = DEFAULT_LAT, DEFAULT_LON
    else:
        lat = rover.get("gps_lat", DEFAULT_LAT)
        lon = rover.get("gps_lon", DEFAULT_LON)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nem Sensör 1", f"{rover.get('nem_1_pct', '—'):.1f} %")
        c2.metric("Nem Sensör 2", f"{rover.get('nem_2_pct', '—'):.1f} %")
        c3.metric("Hava Sıcaklığı", f"{rover.get('hava_temp_c', '—'):.1f} °C")
        c4.metric("BBCH Evresi", rover.get("bbch_sinif", "—"))

    # Anomaliler
    if adv and adv.get("anomaly_count", 0) > 0:
        st.error(
            f"⚠️ **{adv['anomaly_count']} Anomali Tespit Edildi**",
            icon="🚨",
        )
        for a in adv.get("anomalies", []):
            badge = {"KRITIK": "🔴", "YUKSEK": "🟠", "ORTA": "🟡"}.get(
                a["seviye"], "⚪"
            )
            st.markdown(f"{badge} **[{a['seviye']}] {a['tip']}** — {a['aciklama']}")
    elif adv:
        st.success("✅ Anomali tespit edilmedi")

    st.divider()

    # ── GPS Haritası ──────────────────────────────────────────────────────
    st.subheader("🗺️ GPS Konumu")
    m = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap")
    folium.Marker(
        [lat, lon],
        popup=f"trak-ai-rover-01\n{lat:.4f}°N, {lon:.4f}°E",
        tooltip="Rover konumu",
        icon=folium.Icon(color="green" if (adv and adv.get("anomaly_count", 0) == 0)
                         else "red", icon="tractor", prefix="fa"),
    ).add_to(m)
    folium.Circle(
        [lat, lon], radius=50,
        color="#1565c0", fill=True, fill_opacity=0.15,
    ).add_to(m)
    st_folium(m, height=350, width=None, returned_objects=[])

    st.divider()

    # ── Advisory göster ───────────────────────────────────────────────────
    if adv and adv.get("advisory"):
        st.subheader("💡 KDS Tavsiyesi")
        if adv.get("llm_triggered"):
            dur = adv.get("duration_sec")
            st.caption(
                f"Gemma-3-4B tarafından üretildi"
                + (f" · {dur:.1f} sn" if dur else "")
            )
            st.info(adv["advisory"])
        else:
            st.success(adv["advisory"])


# ══════════════════════════════════════════════════════════════════════════
# SAYFA 3 — Tarım Asistanı
# ══════════════════════════════════════════════════════════════════════════

ORNEK_SORULAR = [
    "Ayçiçeğime ne zaman su vermeliyim?",
    "Buğdayda mildiyö belirtileri neler?",
    "Tarlam için gübreleme takvimi öner",
]


def page_tarim_asistani():
    render_header("RAG destekli Türkçe tarım danışmanı")

    vs, ch = get_faiss()
    ollama_ok, _ = get_ollama_status()

    if vs is None:
        st.error("FAISS indeksi yüklenemedi. Önce `python main_rag.py build` çalıştırın.")
        return
    if not ollama_ok:
        st.warning("Ollama bağlantısı yok. Yanıtlar üretilemez.")

    # Örnek sorular sidebar'da
    with st.sidebar:
        st.divider()
        st.markdown("**Örnek Sorular**")
        for soru in ORNEK_SORULAR:
            if st.button(soru, key=f"ornek_{soru[:20]}", use_container_width=True):
                st.session_state._pending_question = soru

    # Aktif veri bağlamı — LLM'e beslenen güncel veriler
    with st.expander("📊 Aktif Veri Bağlamı (LLM'e beslenen güncel veriler)", expanded=False):
        rich_ctx = get_rich_context()
        st.code(rich_ctx, language="text")
        st.caption("Her 5 dakikada bir güncellenir. Tıkla → kapat.")

    # Chat geçmişini göster
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📚 Kaynak Belgeler"):
                    for i, src in enumerate(msg["sources"], 1):
                        method = src.get("method", "")
                        boost = " ★" if src.get("boosted") else ""
                        st.caption(
                            f"**Kaynak {i}:** {src['metadata'].get('source','?')} "
                            f"({method}{boost})"
                        )
                        st.text(src["text"][:300] + ("..." if len(src["text"]) > 300 else ""))

    # Bekleyen örnek soru varsa input'a koy
    pending = st.session_state.pop("_pending_question", None)

    user_input = st.chat_input("Sorunuzu yazın...") or pending

    if user_input:
        # Kullanıcı mesajını ekle
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # RAG + LLM
        with st.chat_message("assistant"):
            with st.spinner("Bilgi tabanı taranıyor ve yanıt üretiliyor..."):
                try:
                    docs = tri_rag_retrieve(user_input, vs, ch)
                    context = format_context(docs)
                    result = rag_query(user_input, context, get_rich_context())
                    answer = result.get("answer", "Yanıt alınamadı.")
                    dur = result.get("duration_sec", 0)
                    tok = result.get("tokens", 0)
                except Exception as e:
                    answer = f"Hata: {e}"
                    docs = []
                    dur, tok = 0, 0

            st.markdown(answer)
            if dur:
                st.caption(f"⏱ {dur:.1f} sn · {tok} token · {OLLAMA_MODEL}")
            if docs:
                with st.expander("📚 Kaynak Belgeler"):
                    for i, src in enumerate(docs, 1):
                        method = src.get("method", "")
                        boost = " ★" if src.get("boosted") else ""
                        st.caption(
                            f"**Kaynak {i}:** {src['metadata'].get('source','?')} "
                            f"({method}{boost})"
                        )
                        st.text(src["text"][:300] + ("..." if len(src["text"]) > 300 else ""))

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer,
            "sources": docs,
        })


# ══════════════════════════════════════════════════════════════════════════
# Ana giriş noktası
# ══════════════════════════════════════════════════════════════════════════

def main():
    page = render_sidebar()

    if page == "🌿 Tarla Durumu":
        page_tarla_durumu()
    elif page == "📡 Rover İzleme":
        page_rover_izleme()
    else:
        page_tarim_asistani()

    st.markdown(
        "<div style='text-align:center;color:#999;font-size:0.8em;margin-top:2em'>"
        "TÜBİTAK 2209-A &nbsp;•&nbsp; Işık Üniversitesi &nbsp;•&nbsp; 2026"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
