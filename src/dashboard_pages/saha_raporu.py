"""
TRAK-AI Saha Çıkış Raporu — Streamlit Module Page
==================================================

Master dashboard'da "🌾 Saha Raporu" sekmesi olarak render edilir.

Gösterir:
  - Üst seviye istatistik kartları (5'li)
  - Sınıf dağılım bar chart + tablo
  - Zaman serisi: nem + sıcaklık
  - LLM tavsiye paneli (genel + sınıf bazlı tab'lar)
  - Sınıflandırılmış fotoğraf grid'i

Standalone test (master dashboard olmadan):
    streamlit run src/dashboard_pages/saha_raporu.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Project paths (master dashboard tarafından zaten ekli olabilir, idempotent)
THIS_FILE   = Path(__file__).resolve()
PROJECT_DIR = THIS_FILE.parent.parent.parent
SRC_DIR     = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import init_db, get_connection             # noqa: E402


# ════════════════════════════════════════════════════════════════════
# DB sorguları (cached)
# ════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30)
def _get_available_kaynaks() -> list[str]:
    """rover_olcumler tablosundaki tüm kaynak değerleri."""
    init_db()
    with get_connection() as c:
        rows = c.execute(
            "SELECT DISTINCT kaynak FROM rover_olcumler "
            "WHERE kaynak IS NOT NULL "
            "ORDER BY kaynak DESC"
        ).fetchall()
    return [r["kaynak"] for r in rows]


@st.cache_data(ttl=30)
def _get_field_data(kaynak: str) -> pd.DataFrame:
    """Belirli kaynak için tüm rover_olcumler satırları."""
    with get_connection() as c:
        rows = c.execute(
            "SELECT id, timestamp, nem_1_pct, hava_temp_c, hava_nem_pct, "
            "       engel_on_cm, bbch_sinif, goruntu_guven, goruntu_yolu, "
            "       waypoint_label, rover_id "
            "FROM rover_olcumler WHERE kaynak = ? "
            "ORDER BY timestamp ASC",
            (kaynak,)
        ).fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


@st.cache_data(ttl=30)
def _get_advisories(kaynak: str) -> pd.DataFrame:
    """saha_raporlari tablosundan LLM tavsiyeleri."""
    with get_connection() as c:
        rows = c.execute(
            "SELECT id, rapor_tipi, bbch_sinif, olcum_sayisi, ortalama_nem, "
            "       ortalama_temp, ortalama_guven, llm_tavsiye, llm_sure_sec, "
            "       llm_model, created_at "
            "FROM saha_raporlari WHERE kaynak = ? "
            "ORDER BY rapor_tipi DESC, olcum_sayisi DESC",
            (kaynak,)
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def _emoji_for(sinif: str) -> str:
    """Sınıf adına göre uygun emoji."""
    s = str(sinif).lower()
    if "saglikli" in s or "sağlıklı" in s: return "🌱"
    if "hastalik" in s and "pas" in s:     return "🔴"
    if "hastalik" in s and "mildiyo" in s: return "🟠"
    if "hastalik" in s:                    return "⚠️"
    if "stres" in s and "kurak" in s:      return "🌵"
    if "stres" in s and "besin" in s:      return "🟡"
    if "hasat" in s:                       return "🌾"
    return "📝"


# ════════════════════════════════════════════════════════════════════
# Render fonksiyonu (master dashboard tarafından çağrılır)
# ════════════════════════════════════════════════════════════════════
def render() -> None:
    """Saha Raporu sekmesinin tam içeriği."""

    st.markdown("### 🌾 Saha Çıkış Raporu")
    st.caption("Rover telemetrisi + YOLOv8 sınıflandırma + LLM tavsiyesi — "
               "birleşik analiz görünümü")

    kaynaks = _get_available_kaynaks()
    if not kaynaks:
        st.warning(
            "Henüz hiçbir saha çıkışı verisi yok.\n\n"
            "Saha verisi DB'ye yüklemek için terminalden:\n"
            "```\npython scripts/import_rover_log.py\n"
            "python scripts/classify_rover_images.py\n"
            "python scripts/generate_field_advisory.py\n```"
        )
        return

    # ── Kaynak seçici (sayfa içinde, sidebar yerine) ─────────────────
    c_sel, c_btn, c_pf = st.columns([3, 1, 1])
    with c_sel:
        secili_kaynak = st.selectbox(
            "Saha Çıkışı (kaynak)",
            options=kaynaks,
            index=0,
            help="rover_olcumler.kaynak alanı — saha çıkışlarını ayırmak için etiket",
            key="saha_raporu_kaynak",
        )
    with c_btn:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("🔄 Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_pf:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        show_photos = st.checkbox("📷 Foto'lar", value=True,
                                   key="saha_raporu_show_photos")

    df = _get_field_data(secili_kaynak)
    advisories_df = _get_advisories(secili_kaynak)

    if df.empty:
        st.error(f"Seçili kaynak için veri bulunamadı: `{secili_kaynak}`")
        return

    # ── Üst seviye metrik kartları ───────────────────────────────────
    total = len(df)
    class_counts = (df["bbch_sinif"].dropna().value_counts()
                    if "bbch_sinif" in df else pd.Series())
    n_classified = int(class_counts.sum())
    hastalik_n = sum(v for k, v in class_counts.items()
                     if "hastalik" in str(k).lower())
    hastalik_oran = (hastalik_n / n_classified * 100) if n_classified > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Toplam Ölçüm", f"{total}")
    c2.metric("Sınıflandırılmış", f"{n_classified}")
    if df["nem_1_pct"].notna().any():
        c3.metric("Ortalama Nem", f"%{df['nem_1_pct'].mean():.1f}")
    else:
        c3.metric("Ortalama Nem", "—")
    if df["hava_temp_c"].notna().any():
        c4.metric("Ortalama Sıcaklık", f"{df['hava_temp_c'].mean():.1f}°C")
    else:
        c4.metric("Ortalama Sıcaklık", "—")

    if hastalik_oran > 0:
        c5.metric(
            "Hastalık Oranı",
            f"%{hastalik_oran:.1f}",
            delta=f"{hastalik_n} foto",
            delta_color="inverse" if hastalik_oran > 20 else "off",
        )
    else:
        c5.metric("Hastalık Oranı", "%0", "Sağlıklı")

    if total > 0 and df["timestamp"].notna().any():
        sure_dakika = (df["timestamp"].max() - df["timestamp"].min()
                       ).total_seconds() / 60
        st.caption(
            f"⏱ Toplam süre: **{sure_dakika:.0f} dakika** "
            f"({df['timestamp'].min().strftime('%H:%M')} - "
            f"{df['timestamp'].max().strftime('%H:%M')})"
        )

    st.divider()

    # ── 2-kolon: Sınıf dağılımı + Zaman serisi ──────────────────────
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("#### 🌱 Sınıf Dağılımı")
        if not class_counts.empty:
            chart_df = pd.DataFrame({
                "Sınıf": class_counts.index,
                "Adet": class_counts.values,
            })
            st.bar_chart(chart_df.set_index("Sınıf"), height=280,
                         color="#7eb77f")
            pct_df = chart_df.copy()
            pct_df["%"] = (pct_df["Adet"] / pct_df["Adet"].sum() * 100).round(1)
            pct_df["%"] = pct_df["%"].astype(str) + "%"
            st.dataframe(pct_df, hide_index=True, use_container_width=True)
        else:
            st.info("Henüz sınıflandırma yapılmadı")

    with col_right:
        st.markdown("#### 📈 Zaman Serisi — Nem & Sıcaklık")
        if df["timestamp"].notna().any():
            ts_df = df[["timestamp", "nem_1_pct", "hava_temp_c"]].dropna(
                subset=["timestamp"])
            if not ts_df.empty:
                ts_df = ts_df.set_index("timestamp")
                st.line_chart(ts_df, height=280,
                              color=["#7aa2f7", "#e07474"])
            else:
                st.info("Zaman serisi verisi yok")
        else:
            st.info("Zaman damgası verisi yok")

    st.divider()

    # ── LLM Tavsiyeleri ──────────────────────────────────────────────
    st.markdown("#### 🤖 LLM Tavsiyeleri (gemma3:4b)")

    if advisories_df.empty:
        st.warning(
            "Bu saha çıkışı için henüz LLM tavsiyesi üretilmedi.\n\n"
            "Üretmek için terminalden:\n"
            "```\npython scripts/generate_field_advisory.py\n```\n\n"
            "Süre: ~2 dakika (4 LLM çağrısı)."
        )
    else:
        genel = advisories_df[advisories_df["rapor_tipi"] == "genel"]
        sinif_bazli = advisories_df[advisories_df["rapor_tipi"] == "sinif_bazli"]

        # Genel tavsiye üstte
        if not genel.empty:
            row = genel.iloc[0]
            with st.container(border=True):
                st.markdown("##### 📋 Genel Saha Tavsiyesi")
                st.caption(
                    f"Model: `{row['llm_model']}`  •  "
                    f"Süre: {row['llm_sure_sec']:.0f}sn  •  "
                    f"Üretildi: {row['created_at']}"
                )
                st.markdown(row["llm_tavsiye"])

        # Sınıf bazlı tab'lar
        if not sinif_bazli.empty:
            st.markdown("##### 🌿 Sınıf Bazlı Tavsiyeler")
            sinif_listesi = sinif_bazli["bbch_sinif"].tolist()
            tab_labels = [f"{_emoji_for(s)} {s}" for s in sinif_listesi]
            tabs = st.tabs(tab_labels)

            for i, (_, row) in enumerate(sinif_bazli.iterrows()):
                with tabs[i]:
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    cc1.metric("Tespit", f"{int(row['olcum_sayisi'])} foto")
                    cc2.metric("Ort. Nem",
                               f"%{row['ortalama_nem']:.1f}"
                               if row["ortalama_nem"] else "—")
                    cc3.metric("Ort. Sıcaklık",
                               f"{row['ortalama_temp']:.1f}°C"
                               if row["ortalama_temp"] else "—")
                    cc4.metric("Ort. Güven",
                               f"%{row['ortalama_guven']*100:.0f}"
                               if row["ortalama_guven"] else "—")
                    st.caption(
                        f"LLM süre: {row['llm_sure_sec']:.0f}sn  •  "
                        f"Üretildi: {row['created_at']}"
                    )
                    st.markdown(row["llm_tavsiye"])

    st.divider()

    # ── Fotoğraf grid'i ─────────────────────────────────────────────
    if show_photos:
        st.markdown("#### 🖼 Sınıflandırılmış Fotoğraflar")

        photo_rows = df[df["goruntu_yolu"].notna()].copy()
        if photo_rows.empty:
            st.info("Henüz classify edilmiş foto yok.")
        else:
            photo_limit = st.slider("Max foto adedi", 4, 24, 12, step=4,
                                     key="saha_raporu_photo_limit")
            if len(photo_rows) > photo_limit:
                step = len(photo_rows) // photo_limit
                photo_rows = photo_rows.iloc[::step].head(photo_limit)

            # Sadece varolan dosyalar
            photo_rows = photo_rows[photo_rows["goruntu_yolu"].apply(
                lambda p: Path(p).exists() if p else False
            )]

            if photo_rows.empty:
                st.warning("Foto dosyaları diskte bulunamadı.")
            else:
                n_cols = 4
                for i in range(0, len(photo_rows), n_cols):
                    cols = st.columns(n_cols)
                    for j, (_, row) in enumerate(
                            photo_rows.iloc[i:i+n_cols].iterrows()):
                        with cols[j]:
                            try:
                                st.image(
                                    row["goruntu_yolu"],
                                    caption=(
                                        f"id={int(row['id'])} • "
                                        f"{row['bbch_sinif']}\n"
                                        f"güven=%{float(row['goruntu_guven'])*100:.0f}"
                                    ),
                                    use_container_width=True,
                                )
                            except Exception as e:
                                st.caption(f"Foto yüklenemedi: {e}")

        st.divider()

    # ── Detay tablo (expandable) ─────────────────────────────────────
    with st.expander(f"📋 Tüm ölçüm verileri ({total} satır)"):
        display_cols = ["id", "timestamp", "nem_1_pct", "hava_temp_c",
                        "engel_on_cm", "bbch_sinif", "goruntu_guven",
                        "waypoint_label"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], hide_index=True,
                     use_container_width=True, height=400)


# ════════════════════════════════════════════════════════════════════
# Standalone mode (streamlit run direkt çalıştırıldığında)
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    st.set_page_config(
        page_title="TRAK-AI Saha Çıkış Raporu",
        page_icon="🌾",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render()
