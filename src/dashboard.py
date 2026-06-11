"""
TRAK-AI KDS — Master Dashboard (unified router)
================================================
8 sekme: 🏠 Ana | 🌿 Tarla Detay | 🚜 Rover | 💬 SCRAG |
         ✅ FLOV | 🔬 X-Modal | 🌦️ Hava | ⚙️ Settings

Calistirma:
    streamlit run src/dashboard.py

This is the single entry point for the entire DSS. Page rendering logic
lives under `src/dashboard_pages/<page>/__init__.py` (and `_legacy_pages.py`
for the original farmer-facing surface).
"""
from __future__ import annotations

import os
import sys
import logging

# ── Path Kurulumu ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
_CP4_DIR = os.path.join(PROJECT_ROOT, "src", "cp4_rag")
for _p in [_SRC_DIR, _CP2_DIR, _CP4_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

# ── Streamlit page config (must be the very first Streamlit call) ────────────
st.set_page_config(
    page_title="TRAK-AIA KDS",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB init (single point of truth — legacy module no longer calls it) ──────
try:
    from database import init_db
    init_db()
except Exception as exc:                                            # noqa: BLE001
    st.error(f"Veritabani baslatma hatasi: {exc}")


# ── Auto-ensure tarla_tahminler is populated (first-launch convenience) ──
def _auto_ensure_predictions() -> None:
    """If tarla_tahminler is empty for any active tarla, run the crop-aware
    pipeline once. Cached via session state so it runs at most once per
    Streamlit session."""
    if st.session_state.get("_auto_predict_done"):
        return
    try:
        import sqlite3
        from pathlib import Path
        db = Path(PROJECT_ROOT) / "data" / "trakai.db"
        if not db.exists():
            return
        con = sqlite3.connect(db)
        try:
            missing = con.execute("""
                SELECT t.id FROM tarla t
                LEFT JOIN tarla_tahminler tt ON tt.tarla_id = t.id
                WHERE tt.id IS NULL
            """).fetchall()
        finally:
            con.close()
        if not missing:
            st.session_state["_auto_predict_done"] = True
            return

        st.toast(f"{len(missing)} tarla için tahmin hesaplanıyor...",
                 icon="⚙️")
        import subprocess
        subprocess.run(
            [sys.executable,
             str(Path(PROJECT_ROOT) / "scripts" / "predict_all_tarlalar.py")],
            cwd=PROJECT_ROOT, capture_output=True, timeout=300,
        )
        st.session_state["_auto_predict_done"] = True
    except Exception as exc:                                        # noqa: BLE001
        logging.getLogger("trakai.dashboard").warning(
            "auto-predict failed: %s", exc)


_auto_ensure_predictions()


# ── Auto-ensure rover_olcumler için anomali tespiti + advisory ──────────────
def _auto_ensure_field_processing() -> None:
    """rover_olcumler tablosunda eksik anomali tespitlerini doldur, eksik
    saha kaynaklarına LLM advisory üret. Cache: session state.

    Adımlar:
      1. anomaliler IS NULL olan rover_olcumler satırları için
         orchestrator.detect_anomalies() çağır + DB güncelle (~15sn)
      2. saha_raporlari'nda eksik kaynak varsa generate_field_advisory.py
         (~2dk per kaynak, background)
    """
    if st.session_state.get("_auto_field_processed"):
        return
    try:
        import sqlite3
        from pathlib import Path
        db = Path(PROJECT_ROOT) / "data" / "trakai.db"
        if not db.exists():
            return

        con = sqlite3.connect(db)
        try:
            # Eksik anomali kontrolü
            missing_anom = con.execute(
                "SELECT COUNT(*) FROM rover_olcumler "
                "WHERE anomaliler IS NULL"
            ).fetchone()[0]
            # Eksik saha advisory kontrolü
            all_kaynaks = con.execute(
                "SELECT DISTINCT kaynak FROM rover_olcumler "
                "WHERE kaynak IS NOT NULL"
            ).fetchall()
            existing_rapor = con.execute(
                "SELECT DISTINCT kaynak FROM saha_raporlari"
            ).fetchall()
        finally:
            con.close()

        all_kaynaks_set = {r[0] for r in all_kaynaks}
        existing_set = {r[0] for r in existing_rapor}
        missing_kaynaks = all_kaynaks_set - existing_set

        if missing_anom == 0 and not missing_kaynaks:
            st.session_state["_auto_field_processed"] = True
            return

        import subprocess

        # 1. Anomali tespiti (hızlı, senkron)
        if missing_anom > 0:
            st.toast(f"{missing_anom} kayıt için anomali tespiti çalışıyor...",
                     icon="⚙️")
            try:
                subprocess.run(
                    [sys.executable,
                     str(Path(PROJECT_ROOT) / "scripts" / "process_field_data.py"),
                     "--skip-lstm", "--skip-advisory"],
                    cwd=PROJECT_ROOT, capture_output=True, timeout=120,
                )
                st.toast(f"Anomali tespiti tamamlandı ({missing_anom} kayıt)",
                         icon="✓")
            except subprocess.TimeoutExpired:
                logging.getLogger("trakai.dashboard").warning(
                    "anomaly detection timeout (120s)")

        # 2. Eksik saha advisory (yavaş, fire-and-forget — background)
        if missing_kaynaks:
            st.toast(
                f"{len(missing_kaynaks)} saha için LLM tavsiyesi "
                f"arka planda üretiliyor (~2 dk/saha)...",
                icon="🤖",
            )
            # Popen ile fire-and-forget — dashboard'u bloklamaz
            try:
                subprocess.Popen(
                    [sys.executable,
                     str(Path(PROJECT_ROOT) / "scripts" / "process_field_data.py"),
                     "--skip-anomaly", "--skip-lstm"],
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception as exc:                                # noqa: BLE001
                logging.getLogger("trakai.dashboard").warning(
                    "advisory background launch failed: %s", exc)

        st.session_state["_auto_field_processed"] = True
    except Exception as exc:                                        # noqa: BLE001
        logging.getLogger("trakai.dashboard").warning(
            "auto-field-processing failed: %s", exc)


_auto_ensure_field_processing()


# ── Auto-ensure FLOV + Cross-Modal + YOLOv8 log (tarih-bazlı) ────────────────
def _auto_ensure_validation_artifacts() -> None:
    """Tarih-tabanlı kontrol: FLOV, Cross-Modal, YOLOv8 log dosyaları
    güncel mi? Değilse otomatik üret.

    Kontrol stratejisi:
      - reports/prospective/EVR_01_<year>_validation_per_stage.csv
        → yoksa veya 24+ saat eskiyse  python scripts/validate_evr01.py
      - logs/visual_field_yolov8.jsonl
        → DB'de classified record varsa ve log yoksa, üret
      - logs/visual_consensus_alerts.jsonl
        → bugünden 7+ gün önceyse  scripts/run_cross_modal_validation.py
    """
    if st.session_state.get("_auto_validation_done"):
        return
    try:
        from datetime import datetime, timedelta, date
        from pathlib import Path
        import subprocess

        now = datetime.now()
        proj = Path(PROJECT_ROOT)
        triggers: list[tuple[str, list[str]]] = []

        # 1. FLOV validation — per-stage CSV
        flov_csv = (proj / "reports" / "prospective"
                    / f"EVR_01_{now.year}_validation_per_stage.csv")
        flov_needs_update = True
        if flov_csv.exists():
            age = now.timestamp() - flov_csv.stat().st_mtime
            if age < 86400:  # 24 saat
                flov_needs_update = False
        if flov_needs_update:
            triggers.append((
                "FLOV validation",
                [sys.executable, str(proj / "scripts" / "validate_evr01.py"),
                 "--site", "EVR_01", "--year", str(now.year)],
            ))

        # 2. YOLOv8 saha log — DB'de classified varsa ve log eksikse
        yolo_log = proj / "logs" / "visual_field_yolov8.jsonl"
        yolo_needs_update = True
        if yolo_log.exists() and yolo_log.stat().st_size > 0:
            age = now.timestamp() - yolo_log.stat().st_mtime
            if age < 86400:
                yolo_needs_update = False
        if yolo_needs_update:
            triggers.append((
                "YOLOv8 saha log",
                [sys.executable, str(proj / "scripts" / "generate_yolov8_field_log.py")],
            ))

        # 3. Cross-Modal validation — son 30 günü kapsayan window
        xmod_log = proj / "logs" / "visual_consensus_alerts.jsonl"
        xmod_needs_update = True
        if xmod_log.exists() and xmod_log.stat().st_size > 0:
            age = now.timestamp() - xmod_log.stat().st_mtime
            if age < 86400:
                xmod_needs_update = False
        if xmod_needs_update:
            end_date = now.date()
            start_date = end_date - timedelta(days=30)
            triggers.append((
                "Cross-Modal validation",
                [sys.executable, str(proj / "scripts" / "run_cross_modal_validation.py"),
                 "--site", "EVR_01",
                 "--start", start_date.isoformat(),
                 "--end", end_date.isoformat(),
                 "--step", "5"],
            ))

        if not triggers:
            st.session_state["_auto_validation_done"] = True
            return

        # Her tetikte toast + subprocess (timeout korumalı)
        for label, cmd in triggers:
            st.toast(f"{label} çalışıyor (güncel değil)...", icon="⚙️")
            try:
                result = subprocess.run(
                    cmd, cwd=PROJECT_ROOT, capture_output=True,
                    timeout=180, encoding="utf-8", errors="replace",
                )
                if result.returncode == 0:
                    st.toast(f"{label} tamamlandı", icon="✓")
                else:
                    logging.getLogger("trakai.dashboard").warning(
                        "%s failed (rc=%s): %s",
                        label, result.returncode,
                        (result.stderr or "")[:200]
                    )
                    st.toast(f"{label} hata verdi (log'a bakın)", icon="⚠️")
            except subprocess.TimeoutExpired:
                logging.getLogger("trakai.dashboard").warning(
                    "%s timeout", label)
                st.toast(f"{label} timeout — atlandı", icon="⚠️")
            except Exception as exc:                            # noqa: BLE001
                logging.getLogger("trakai.dashboard").warning(
                    "%s exception: %s", label, exc)

        st.session_state["_auto_validation_done"] = True
    except Exception as exc:                                    # noqa: BLE001
        logging.getLogger("trakai.dashboard").warning(
            "auto-validation failed: %s", exc)


_auto_ensure_validation_artifacts()


# ── Auto-ensure BBCH hibrit motor + Sentinel-2 NDVI (günlük güncel) ─────────
def _auto_ensure_bbch_and_ndvi() -> None:
    """Günlük tarih-bazlı kontrol: Sentinel-2 NDVI ve hibrit BBCH güncel mi?

    1. Sentinel-2 NDVI son 30 gün → ndvi_kayitlari tablosu
       (en son tarihi bugünden 2 günden eskiyse refetch)
    2. Tüm rover_olcumler kayıtlarına hibrit BBCH değeri yaz
       (bbch_sinif IS NULL olanlar veya son 24sa güncellenmedi)
    """
    if st.session_state.get("_auto_bbch_done"):
        return
    try:
        import sqlite3
        from datetime import datetime, timedelta
        from pathlib import Path
        import subprocess

        proj = Path(PROJECT_ROOT)
        db = proj / "data" / "trakai.db"
        if not db.exists():
            return

        # Sentinel-2 son güncellik kontrolü
        s2_needs_update = True
        try:
            con = sqlite3.connect(db)
            try:
                # ndvi_kayitlari var mı?
                exists = con.execute(
                    "SELECT name FROM sqlite_master WHERE name='ndvi_kayitlari'"
                ).fetchone()
                if exists:
                    last = con.execute(
                        "SELECT MAX(tarih) FROM ndvi_kayitlari WHERE tarla_id=1"
                    ).fetchone()
                    if last and last[0]:
                        last_date = datetime.fromisoformat(last[0]).date()
                        if (datetime.now().date() - last_date).days < 3:
                            s2_needs_update = False
            finally:
                con.close()
        except Exception:                                       # noqa: BLE001
            pass

        if s2_needs_update:
            st.toast("Sentinel-2 NDVI son 30 gün çekiliyor...", icon="🛰️")
            try:
                subprocess.run(
                    [sys.executable,
                     str(proj / "scripts" / "fetch_sentinel2_ndvi.py"),
                     "--days", "30"],
                    cwd=PROJECT_ROOT, capture_output=True,
                    timeout=180, encoding="utf-8", errors="replace",
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                st.toast("NDVI verisi güncel", icon="✓")
            except Exception as e:                              # noqa: BLE001
                logging.getLogger("trakai.dashboard").warning(
                    "NDVI fetch failed: %s", e)

        # BBCH motor — her zaman çalıştır (cache'li session ile günde 1 kez)
        st.toast("Hibrit BBCH motoru tüm tarlalar için hesaplıyor...",
                 icon="🌾")
        try:
            subprocess.run(
                [sys.executable,
                 str(proj / "scripts" / "update_all_bbch.py"), "--all"],
                cwd=PROJECT_ROOT, capture_output=True,
                timeout=60, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            st.toast("BBCH evreleri güncellendi", icon="✓")
        except Exception as e:                                  # noqa: BLE001
            logging.getLogger("trakai.dashboard").warning(
                "BBCH update failed: %s", e)

        st.session_state["_auto_bbch_done"] = True
    except Exception as exc:                                    # noqa: BLE001
        logging.getLogger("trakai.dashboard").warning(
            "auto-bbch failed: %s", exc)


_auto_ensure_bbch_and_ndvi()


# ── Shared utilities ─────────────────────────────────────────────────────────
from dashboard_pages.shared.styling import (
    apply_trakai_theme, render_main_banner, render_theme_toggle,
)
from dashboard_pages.shared.session import init_session_state, get_active_site
from dashboard_pages.shared.components import (
    render_global_alert_bar, system_status_indicators,
)

logger = logging.getLogger("trakai.dashboard")


# ── Page registry ────────────────────────────────────────────────────────────
# Each entry: (label, lazy renderer that returns a callable).
# Lazy import keeps cold-start fast and avoids cascading import errors.
def _legacy_render(page_fn_name: str):
    def _runner():
        from dashboard_pages import _legacy_pages as legacy   # type: ignore
        site = get_active_site()
        if site.tarla is None:
            st.error("Tarla bulunamadi. Veritabanini kontrol edin.")
            return
        getattr(legacy, page_fn_name)(site.db_tarla_id, site.tarla)
    return _runner


def _module_render(module_path: str):
    def _runner():
        mod = __import__(module_path, fromlist=["render"])
        mod.render()
    return _runner


PAGES: dict[str, callable] = {
    "🏠 Ana":           _module_render("dashboard_pages.home"),
    "🌿 Tarla Detay":   _legacy_render("page_tarla"),
    "🚜 Rover":         _legacy_render("page_rover"),
    "🌾 Saha Raporu":   _module_render("dashboard_pages.saha_raporu"),
    "💬 SCRAG":         _legacy_render("page_chat"),
    "✅ FLOV":          _module_render("dashboard_pages.flov_validation"),
    "🔬 X-Modal":       _module_render("dashboard_pages.cross_modal"),
    "🌦️ Hava":          _module_render("dashboard_pages.weather"),
    "⚙️ Settings":      _module_render("dashboard_pages.settings"),
}


# ── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    """Render unified sidebar: brand, site selectors, status, navigation."""
    with st.sidebar:
        st.markdown("# 🌾 TRAK-AIA KDS")
        st.caption("Melih Kalkan • Işık Üniversitesi Bitirme Tezi • 2026")

        # Theme toggle (sistem / aydınlık / karanlık)
        render_theme_toggle()

        st.divider()

        # ── Single tarla selector (research_code bridges to FLOV/EVR_xx) ─────
        try:
            from database import get_tarlalar
            tarlalar = get_tarlalar() or []
            if tarlalar:
                def _lbl(t: dict) -> str:
                    rc = t.get("research_code")
                    tag = f" [{rc}]" if rc else ""
                    crop = t.get("aktif_urun") or "?"
                    return f"{t['isim']}{tag} ({crop})"
                labels = {t["id"]: _lbl(t) for t in tarlalar}
                st.selectbox(
                    "Tarla",
                    options=list(labels.keys()),
                    format_func=lambda x: labels[x],
                    key="tarla_id",
                )
            else:
                st.warning("DB'de tarla yok. `python src/database.py --reset` cagirin.")
        except Exception as exc:                                    # noqa: BLE001
            st.caption(f"DB tarla listesi yok ({exc})")

        # ── Research year (for FLOV/cross-modal artefact lookup) ─────────────
        st.number_input("Yil", min_value=2024, max_value=2030, step=1,
                        key="research_year")

        st.divider()

        # ── Navigation ───────────────────────────────────────────────────────
        nav_target = st.session_state.get("nav_target")
        nav_options = list(PAGES.keys())
        default_idx = nav_options.index(nav_target) if nav_target in nav_options else 0
        page = st.radio("Sayfa", nav_options, index=default_idx,
                        label_visibility="collapsed", key="active_page")
        # Clear cross-page jump target after consumption.
        if nav_target:
            st.session_state["nav_target"] = None

        st.divider()
        st.markdown("**Sistem Durumu**")
        system_status_indicators()

    return page


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    apply_trakai_theme()
    init_session_state()

    page = render_sidebar()

    # Global alert bar (CRITICAL across FLOV / X-Modal / Weather).
    render_global_alert_bar()

    # Light banner per top-level tab.
    subtitle_map = {
        "🏠 Ana":           "Cok kaynakli karar destek sistemi",
        "🌿 Tarla Detay":   "Bitki sagligi, verim, fenoloji",
        "🚜 Rover":         "Alan robotu telemetri ve anomali",
        "🌾 Saha Raporu":   "Rover + YOLOv8 + LLM tavsiyesi (saha cikis ozeti)",
        "💬 SCRAG":         "Bilgi tabanli tarim asistani",
        "✅ FLOV":          "Forward-looking validation",
        "🔬 X-Modal":       "Saha · Uydu · Ozellik 3-yollu konsensus",
        "🌦️ Hava":          "ERA5 + Open-Meteo + climatology",
        "⚙️ Settings":      "API durumu, model integrity, audit",
    }
    render_main_banner(page.split(" ", 1)[-1] if " " in page else page,
                       subtitle_map.get(page, ""))

    # Dispatch.
    runner = PAGES.get(page)
    if runner is None:
        st.error(f"Bilinmeyen sayfa: {page}")
        return
    try:
        runner()
    except Exception as exc:                                        # noqa: BLE001
        logger.exception("Page render failed: %s", page)
        st.error(f"Sayfa yuklenemedi: {exc}")
        with st.expander("Hata detayi"):
            import traceback
            st.code(traceback.format_exc(), language="python")


if __name__ == "__main__":
    main()
