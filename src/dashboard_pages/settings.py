"""⚙️ Settings — API durumu, Model Integrity, Audit logs, Konfigürasyon, Veri.

After v3 production push:
- API Durumu: live system_status_indicators
- Model Integrity: model_integrity.jsonl ledger
- Audit Logs: api_audit.jsonl
- Konfigürasyon: read-only view of EVRENLI sites + key config knobs
- Veri Yönetimi: DB export buttons + retrospective ingest trigger
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .shared.components import system_status_indicators
from .shared.data_loaders import load_integrity_ledger, load_api_audit


def _config_summary() -> dict:
    """Snapshot key configuration knobs for the read-only view."""
    out: dict = {}
    try:
        from prospective_validation import config as _flov
        out["EVRENLI_SITES"] = [
            {
                "id": s.id, "name": s.name,
                "lat": s.lat, "lon": s.lon,
                "owner": getattr(s, "owner", "—"),
                "area_da": getattr(s, "area_da", None),
            }
            for s in _flov.EVRENLI_SITES
        ]
        out["MVP_SITE_ID"] = getattr(_flov, "MVP_SITE_ID", None)
        out["INPUT_WINDOW"] = getattr(_flov, "INPUT_WINDOW", None)
        out["FORECAST_HORIZON_DAYS"] = getattr(_flov, "FORECAST_HORIZON_DAYS", None)
        out["DELTA_SCALE"] = getattr(_flov, "DELTA_SCALE", None)
        out["FEATURE_NAMES"] = list(getattr(_flov, "FEATURE_NAMES", []))
    except Exception as exc:                                           # noqa: BLE001
        out["error"] = str(exc)
    try:
        from cp4_rag import config as _rag_cfg
        out["OLLAMA_MODEL"] = getattr(_rag_cfg, "OLLAMA_MODEL", None)
        out["LLM_TEMPERATURE"] = getattr(_rag_cfg, "LLM_TEMPERATURE", None)
    except Exception:                                                  # noqa: BLE001
        pass
    return out


def _db_path() -> Path:
    try:
        from database import DB_PATH
        return Path(DB_PATH)
    except Exception:                                                  # noqa: BLE001
        return Path("data/trakaia.db")


def _table_export(table: str) -> bytes:
    """Read full table to CSV bytes (utf-8) — for download_button."""
    import sqlite3
    con = sqlite3.connect(_db_path())
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", con)
    finally:
        con.close()
    return df.to_csv(index=False).encode("utf-8")


def render() -> None:
    tabs = st.tabs([
        "🔌 API Durumu",
        "🔒 Model Integrity",
        "📜 Audit Logs",
        "⚙️ Konfigürasyon",
        "⬇️ Veri Yönetimi",
    ])

    # ── Tab 1: API Durumu ────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### Sistem Durumu")
        system_status_indicators()

        st.markdown("### LLM")
        try:
            from llm_engine import llm_status_text, get_llm_engine
            st.write(llm_status_text())
            eng = get_llm_engine()
            if eng is not None:
                st.caption(f"Base URL: `{eng.get('base_url')}`")
        except Exception as exc:                                       # noqa: BLE001
            st.warning(f"LLM modülü yüklenemedi: {exc}")

    # ── Tab 2: Model Integrity ───────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### Model Integrity Ledger (son 200 kayıt)")
        df = load_integrity_ledger(n=200)
        if df is None or df.empty:
            st.info("model_integrity.jsonl boş veya yok.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Tam ledger indir (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="model_integrity.csv",
                mime="text/csv",
            )

    # ── Tab 3: Audit Logs ────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### API Audit (son 200 çağrı)")
        df = load_api_audit(n=200)
        if df is None or df.empty:
            st.info("api_audit.jsonl boş veya yok.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ API audit indir (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="api_audit.csv",
                mime="text/csv",
            )

    # ── Tab 4: Konfigürasyon (read-only) ─────────────────────────────────────
    with tabs[3]:
        st.markdown("### EVRENLI Sahalar")
        cfg = _config_summary()
        sites = cfg.get("EVRENLI_SITES", [])
        if sites:
            st.dataframe(pd.DataFrame(sites), use_container_width=True,
                         hide_index=True)
        else:
            st.warning("Saha listesi okunamadi: " + str(cfg.get("error")))

        st.markdown("### Frozen Model Parametreleri")
        c1, c2, c3 = st.columns(3)
        c1.metric("INPUT_WINDOW",          cfg.get("INPUT_WINDOW", "—"))
        c2.metric("FORECAST_HORIZON_DAYS", cfg.get("FORECAST_HORIZON_DAYS", "—"))
        c3.metric("DELTA_SCALE",           cfg.get("DELTA_SCALE", "—"))
        st.caption(f"MVP saha: **{cfg.get('MVP_SITE_ID', '—')}**")

        feats = cfg.get("FEATURE_NAMES", [])
        if feats:
            with st.expander(f"17 Donmuş Özellik ({len(feats)})"):
                st.write(", ".join(feats))

        st.markdown("### RAG / LLM")
        st.write({
            "OLLAMA_MODEL":   cfg.get("OLLAMA_MODEL", "—"),
            "LLM_TEMPERATURE": cfg.get("LLM_TEMPERATURE", "—"),
        })

    # ── Tab 5: Veri Yönetimi ─────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### DB Tablo İndirme (CSV)")
        st.caption(f"DB konumu: `{_db_path()}`")
        TABLES = [
            "tarlalar", "rover_olcumler", "tarla_tahminler",
            "hava_kayitlari", "db_meta",
        ]
        cols = st.columns(len(TABLES))
        for col, t in zip(cols, TABLES):
            try:
                blob = _table_export(t)
                col.download_button(
                    f"⬇️ {t}",
                    blob,
                    file_name=f"{t}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key=f"export_{t}",
                )
            except Exception as exc:                                   # noqa: BLE001
                col.caption(f"❌ {t}: {exc}")

        st.divider()

        st.markdown("### Retrospective Backfill (rover_olcumler + hava_kayitlari)")
        c1, c2, c3 = st.columns(3)
        site = c1.selectbox(
            "Saha",
            options=[s["id"] for s in _config_summary().get("EVRENLI_SITES", [])]
                    or ["EVR_01"],
            key="settings_backfill_site",
        )
        year = c2.number_input("Yıl", min_value=2020, max_value=2030,
                               value=2025, step=1,
                               key="settings_backfill_year")
        cadence = c3.number_input("Cadence (gün)", min_value=1, max_value=30,
                                  value=7, step=1,
                                  key="settings_backfill_cadence")
        if st.button("📥 Backfill çalıştır", use_container_width=True):
            try:
                import sys as _sys
                _sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
                from backfill_rover_from_history import backfill_one
                with st.spinner(f"{site} {year} backfill (cadence={cadence})..."):
                    summary = backfill_one(site, int(year), int(cadence))
                if summary.get("status") == "ok":
                    st.success(
                        f"OK — {summary['rover_inserted']} rover satırı, "
                        f"{summary['weather_upserted']} hava upsert."
                    )
                    st.json(summary)
                else:
                    st.warning(summary)
            except Exception as exc:                                   # noqa: BLE001
                st.error(f"Backfill başarısız: {exc}")

        st.divider()
        st.markdown("### Tehlikeli İşlemler")
        with st.expander("🚨 DB Reset (geri alınamaz)"):
            confirm = st.text_input(
                'Onay icin "RESET DB" yazin', key="settings_db_reset_confirm")
            if st.button("DB'yi sifirla", type="primary"):
                if confirm != "RESET DB":
                    st.error("Onay metni eslesmiyor. Iptal edildi.")
                else:
                    try:
                        from database import _backup_old_db, init_db, DB_PATH
                        backup = _backup_old_db()
                        Path(DB_PATH).unlink(missing_ok=True)
                        init_db()
                        st.success(f"DB sifirlandi. Yedek: {backup}")
                    except Exception as exc:                           # noqa: BLE001
                        st.error(f"Reset basarisiz: {exc}")
