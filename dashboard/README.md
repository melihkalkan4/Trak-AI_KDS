# `dashboard/` is deprecated

The standalone FLOV viewer that lived here (`dashboard/flov_dashboard.py`)
has been folded into the unified master dashboard.

**Entry point now:**

```bash
streamlit run src/dashboard.py
```

The old script is preserved verbatim under
`archive/old_dashboards/flov_dashboard.py` for reference.

See `docs/DASHBOARD_GUIDE.md` for the new architecture.
