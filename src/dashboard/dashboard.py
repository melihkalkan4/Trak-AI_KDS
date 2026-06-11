"""
TRAK-AI Rover Dashboard
=======================
Masaustu GUI: MQTT broker'a baglanir, MOCK + GERCEK rover'lari ayri
sekmelerde gosterir, gercek rover'in motorunu uzaktan kontrol eder,
DB kayitlarini insan onayindan gecirir.

Mimari:
  - Topbar: baglanti durumu + broker config
  - Motor Kontrol Toolbar: sadece gercek rover'a (trakaia/rover/cmd)
  - Top-level Notebook: 2 sekme
      [Gercek Rover]  → rover_id='trak-ai-rover-*' patterns
      [Mock Rover]    → rover_id='MOCK_ROVER_*'    patterns
  - Her sekme: kendi RoverView (sensorler, kamera, log, advisory, pending DB)
  - Mesaj routing: payload['rover_id'] -> match eden RoverView

Veri akisi:
  ESP32 / mock_rover -> trakaia/rover/data -> orchestrator -> (anomali + LLM)
    -> trakaia/db/pending  -> dashboard 'Bekleyen Kayitlar' tab'i
    -> kullanici Onayla -> database.add_rover_olcum(tarla_id, rover_data)

Bagimliliklar: tkinter (built-in), paho-mqtt, Pillow, database (proje icinden)
Calistirma:   python src/dashboard/dashboard.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import queue
import sys
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional

# src/ klasorunu sys.path'e ekle (database.py import icin)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR  = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    raise SystemExit("paho-mqtt kurulu degil. Once: pip install paho-mqtt")

try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# GPS harita için opsiyonel kütüphane
# pip install tkintermapview
try:
    import tkintermapview
    _MAP_AVAILABLE = True
except ImportError:
    _MAP_AVAILABLE = False

try:
    from database import add_rover_olcum, init_db
    _DB_AVAILABLE = True
    _DB_IMPORT_ERROR = ""
except Exception as e:
    _DB_AVAILABLE = False
    _DB_IMPORT_ERROR = str(e)


# ──────────────────────────────────────────────────────────────────────
# Sabitler
# ──────────────────────────────────────────────────────────────────────
TOPIC_TELEMETRY  = "trakaia/rover/data"
TOPIC_ADVISORY   = "trakaia/kds/advisory"
TOPIC_CMD        = "trakaia/rover/cmd"
TOPIC_DB_PENDING = "trakaia/db/pending"
TOPIC_WILD       = "trakaia/#"

DEFAULT_BROKER   = "localhost"
DEFAULT_PORT     = 1883
DEFAULT_DRIVE_MS = 1000

# Mock rover prefix'i — mock_rover bu kimlikle yayin yapar
MOCK_ROVER_PREFIX = "MOCK_"

# Renkler (dark tema)
COLOR_BG       = "#1e1e2e"
COLOR_PANEL    = "#27273a"
COLOR_PANEL_LT = "#32324a"
COLOR_TEXT     = "#dcdcdc"
COLOR_LABEL    = "#9aa0c4"
COLOR_VALUE    = "#f5f5dc"
COLOR_OK       = "#7eb77f"
COLOR_WARN     = "#e0c074"
COLOR_BAD      = "#e07474"
COLOR_ACCENT   = "#7aa2f7"
COLOR_MOCK     = "#bb9af7"
COLOR_REAL     = "#7eb77f"
COLOR_BTN_FG   = "#000000"


# ──────────────────────────────────────────────────────────────────────
# RoverView — bir rover'in sensor+kamera+log+advisory+pending UI'ini cizer
# ──────────────────────────────────────────────────────────────────────
class RoverView:
    """Tek bir rover icin tum panelleri yonetir.

    Dashboard her sekme icin ayri instance acar.
    matches(rover_id) ile MQTT mesaji bu view'a mi ait kontrol edilir.
    """

    def __init__(self, parent: tk.Widget, label: str,
                 matches_fn: Callable[[str], bool],
                 accent: str,
                 db_writable: bool = True) -> None:
        self.parent = parent
        self.label = label
        self._matches_fn = matches_fn
        self.accent = accent
        self.db_writable = db_writable

        # Durum
        self.last_telemetry: dict = {}
        self.last_msg_time: Optional[float] = None
        self.pending_records: list[dict] = []
        self._photo_ref: Optional["ImageTk.PhotoImage"] = None

        # Sub-widget referanslari (build sonrasi atanir)
        self.sensor_vars: dict[str, tk.StringVar] = {}
        self.log_text: Optional[tk.Text] = None
        self.advisory_text: Optional[tk.Text] = None
        self.image_label: Optional[tk.Label] = None
        self.image_info_var: Optional[tk.StringVar] = None
        self.heartbeat_var: Optional[tk.StringVar] = None
        self.pending_inner: Optional[tk.Frame] = None
        self.pending_canvas: Optional[tk.Canvas] = None
        self.pending_empty_label: Optional[tk.Label] = None
        self._notebook: Optional[ttk.Notebook] = None
        self._pending_tab_idx: int = 1

        self._build()

    def matches(self, rover_id: str) -> bool:
        return self._matches_fn(rover_id or "")

    # ── UI insaasi ──────────────────────────────────────────────────
    def _build(self) -> None:
        main = tk.Frame(self.parent, bg=COLOR_BG)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1, minsize=290)
        main.columnconfigure(1, weight=2, minsize=400)
        main.columnconfigure(2, weight=2, minsize=320)
        main.rowconfigure(0, weight=3)
        main.rowconfigure(1, weight=2)

        self._build_sensor_panel(main)
        self._build_camera_panel(main)
        self._build_log_panel(main)
        self._build_bottom_tabs(main)

    def _build_sensor_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text=f" {self.label} — Canli Sensorler ",
                              bg=COLOR_PANEL, fg=self.accent,
                              font=("Segoe UI", 10, "bold"),
                              bd=1, relief="solid", labelanchor="nw")
        frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=(8, 4))

        rows = [
            ("rover_id",      "Rover ID",       ""),
            ("tarla_id",      "Tarla ID",       ""),
            ("activity",      "Durum",          ""),    # IDLE / ACTIVE
            ("--sep--",       "",                ""),
            ("nem_1_pct",     "Toprak Nem 1",   "%"),
            ("nem_2_pct",     "Toprak Nem 2",   "%"),
            ("hava_temp_c",   "Hava Sicaklik",  "C"),
            ("hava_nem_pct",  "Hava Nem",       "%"),
            ("--sep--",       "",                ""),
            ("engel_on_cm",   "Engel On",       "cm"),
            ("engel_arka_cm", "Engel Arka",     "cm"),
            ("--sep--",       "",                ""),
            ("gps_lat",       "GPS Lat",        ""),
            ("gps_lon",       "GPS Lon",        ""),
            ("waypoint_label","Waypoint",       ""),
            ("--sep--",       "",                ""),
            ("bbch_sinif",    "BBCH",           ""),
            ("bbch_guven",    "BBCH Guven",     ""),
            ("hastalik",      "Hastalik",       ""),
            ("hastalik_guven","Hast. Guven",    ""),
        ]

        inner = tk.Frame(frame, bg=COLOR_PANEL)
        inner.pack(fill="both", expand=True, padx=10, pady=8)

        for key, label, unit in rows:
            if key == "--sep--":
                tk.Frame(inner, bg=COLOR_BG, height=1).pack(fill="x", pady=5)
                continue
            line = tk.Frame(inner, bg=COLOR_PANEL)
            line.pack(fill="x", pady=2)
            tk.Label(line, text=label, width=14, anchor="w",
                     fg=COLOR_LABEL, bg=COLOR_PANEL,
                     font=("Segoe UI", 9)).pack(side="left")
            var = tk.StringVar(value="—")
            self.sensor_vars[key] = var
            tk.Label(line, textvariable=var, anchor="e",
                     fg=COLOR_VALUE, bg=COLOR_PANEL,
                     font=("Consolas", 10, "bold")).pack(side="left", fill="x", expand=True)
            tk.Label(line, text=unit, fg=COLOR_LABEL, bg=COLOR_PANEL,
                     width=4, anchor="w").pack(side="left")

        tk.Frame(inner, bg=COLOR_BG, height=1).pack(fill="x", pady=5)
        hb_line = tk.Frame(inner, bg=COLOR_PANEL)
        hb_line.pack(fill="x", pady=2)
        tk.Label(hb_line, text="Son veri", width=14, anchor="w",
                 fg=COLOR_LABEL, bg=COLOR_PANEL).pack(side="left")
        self.heartbeat_var = tk.StringVar(value="—")
        tk.Label(hb_line, textvariable=self.heartbeat_var, anchor="w",
                 fg=COLOR_VALUE, bg=COLOR_PANEL,
                 font=("Consolas", 9)).pack(side="left", fill="x", expand=True)

    def _build_camera_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text=" Kamera (en son JPEG) ",
                              bg=COLOR_PANEL, fg=self.accent,
                              font=("Segoe UI", 10, "bold"),
                              bd=1, relief="solid", labelanchor="nw")
        frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=(8, 4))

        self.image_label = tk.Label(frame, bg=COLOR_PANEL,
                                    text="(henuz goruntu yok)",
                                    fg=COLOR_LABEL,
                                    font=("Segoe UI", 10, "italic"))
        self.image_label.pack(fill="both", expand=True, padx=10, pady=10)

        info = tk.Frame(frame, bg=COLOR_PANEL)
        info.pack(fill="x", padx=10, pady=(0, 8))
        self.image_info_var = tk.StringVar(value="—")
        tk.Label(info, textvariable=self.image_info_var,
                 fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Consolas", 9)).pack(side="left")

    def _build_log_panel(self, parent: tk.Widget) -> None:
        frame = tk.LabelFrame(parent, text=" MQTT Mesaj Akisi ",
                              bg=COLOR_PANEL, fg=self.accent,
                              font=("Segoe UI", 10, "bold"),
                              bd=1, relief="solid", labelanchor="nw")
        frame.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=(8, 4))

        text_frame = tk.Frame(frame, bg=COLOR_PANEL)
        text_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.log_text = tk.Text(text_frame, bg="#181826", fg=COLOR_TEXT,
                                insertbackground=COLOR_TEXT,
                                font=("Consolas", 9), wrap="word",
                                relief="flat", height=20)
        scroll = tk.Scrollbar(text_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        for tag, color in [("ts", "#7aa2f7"), ("topic", "#bb9af7"),
                           ("ok", COLOR_OK), ("bad", COLOR_BAD),
                           ("warn", COLOR_WARN), ("cmd", COLOR_ACCENT)]:
            self.log_text.tag_configure(tag, foreground=color)

    def _build_bottom_tabs(self, parent: tk.Widget) -> None:
        notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, columnspan=3, sticky="nsew",
                      padx=8, pady=(4, 8))
        self._notebook = notebook

        # Anomali & Tavsiye sekmesi
        adv_tab = tk.Frame(notebook, bg=COLOR_PANEL)
        notebook.add(adv_tab, text="Anomali & Tavsiye")
        adv_frame = tk.Frame(adv_tab, bg=COLOR_PANEL)
        adv_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.advisory_text = tk.Text(adv_frame, bg="#181826", fg=COLOR_TEXT,
                                     font=("Consolas", 10), wrap="word",
                                     relief="flat", height=8)
        adv_scroll = tk.Scrollbar(adv_frame, command=self.advisory_text.yview)
        self.advisory_text.configure(yscrollcommand=adv_scroll.set)
        adv_scroll.pack(side="right", fill="y")
        self.advisory_text.pack(side="left", fill="both", expand=True)
        self.advisory_text.tag_configure("title", foreground=COLOR_WARN,
                                         font=("Consolas", 10, "bold"))
        self.advisory_text.tag_configure("ts",    foreground=COLOR_ACCENT)
        self.advisory_text.tag_configure("body",  foreground=COLOR_TEXT)

        # Bekleyen DB sekmesi
        pending_tab = tk.Frame(notebook, bg=COLOR_PANEL)
        notebook.add(pending_tab, text="Bekleyen DB (0)")
        self._pending_tab_idx = 1

        if not self.db_writable:
            tk.Label(pending_tab,
                     text=f"(database.py import edilemedi: {_DB_IMPORT_ERROR})",
                     fg=COLOR_BAD, bg=COLOR_PANEL,
                     font=("Segoe UI", 10, "italic")).pack(pady=20)
            return

        cvs_frame = tk.Frame(pending_tab, bg=COLOR_PANEL)
        cvs_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.pending_canvas = tk.Canvas(cvs_frame, bg=COLOR_PANEL, highlightthickness=0)
        pscroll = tk.Scrollbar(cvs_frame, command=self.pending_canvas.yview)
        self.pending_canvas.configure(yscrollcommand=pscroll.set)
        pscroll.pack(side="right", fill="y")
        self.pending_canvas.pack(side="left", fill="both", expand=True)

        self.pending_inner = tk.Frame(self.pending_canvas, bg=COLOR_PANEL)
        self.pending_canvas.create_window((0, 0), window=self.pending_inner, anchor="nw")
        self.pending_inner.bind(
            "<Configure>",
            lambda e: self.pending_canvas.configure(
                scrollregion=self.pending_canvas.bbox("all")
            ),
        )
        self.pending_empty_label = tk.Label(
            self.pending_inner,
            text=f"({self.label} icin bekleyen kayit yok)",
            fg=COLOR_LABEL, bg=COLOR_PANEL,
            font=("Segoe UI", 10, "italic"))
        self.pending_empty_label.pack(pady=20, padx=12, anchor="w")

    # ── Mesaj islayicilar (Dashboard'dan cagrilir) ──────────────────
    def handle_telemetry(self, payload: dict, ts: str) -> None:
        self.last_msg_time = time.time()
        summary = self._telemetry_summary(payload)
        self._append_log(ts, TOPIC_TELEMETRY, summary, "ok")
        self._update_sensors(payload)
        self._maybe_update_image(payload)

    def handle_advisory(self, payload: dict, ts: str) -> None:
        self.last_msg_time = time.time()
        self._append_log(ts, TOPIC_ADVISORY, "ADVISORY", "warn")
        self._append_advisory(ts, payload)

    def handle_pending(self, payload: dict, ts: str) -> None:
        self._append_log(ts, TOPIC_DB_PENDING, "BEKLEYEN KAYIT", "warn")
        self._add_pending_card(payload)

    # ── Log + sensor + image guncelleyiciler ────────────────────────
    def _telemetry_summary(self, p: dict) -> str:
        return (f"Nem={p.get('nem_1_pct', '?')!s:>5} "
                f"Temp={p.get('hava_temp_c', '?')!s:>5} "
                f"Engel={p.get('engel_on_cm', '?')!s:>4}cm "
                f"BBCH={p.get('bbch_sinif', '?')}")

    def _append_log(self, ts: str, topic: str, body: str, tag: str) -> None:
        if self.log_text is None:
            return
        self.log_text.insert("end", f"[{ts}] ", "ts")
        short = topic.split("/", 1)[-1] if "/" in topic else topic
        self.log_text.insert("end", f"{short} ", "topic")
        self.log_text.insert("end", f"{body}\n", tag)
        self.log_text.see("end")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 500:
            self.log_text.delete("1.0", f"{line_count - 500}.0")

    def _append_advisory(self, ts: str, payload: dict) -> None:
        if self.advisory_text is None:
            return
        self.advisory_text.insert("end", f"[{ts}] ", "ts")
        anomali_tip = payload.get("anomali_tipi") or payload.get("anomali") or "ANOMALI"
        self.advisory_text.insert("end", f"{anomali_tip}\n", "title")
        tavsiye = (payload.get("tavsiye") or payload.get("advisory")
                   or payload.get("text")
                   or json.dumps(payload, ensure_ascii=False, indent=2))
        self.advisory_text.insert("end", f"{tavsiye}\n", "body")
        self.advisory_text.insert("end", "─" * 80 + "\n", "ts")
        self.advisory_text.see("end")

    def _update_sensors(self, payload: dict) -> None:
        self.last_telemetry = payload
        for key, var in self.sensor_vars.items():
            val = payload.get(key)
            if val is None:
                if key in ("nem_2_pct", "engel_arka_cm", "engel_on_cm"):
                    var.set("yok")
                continue
            if isinstance(val, float):
                if key == "nem_2_pct" and val < 0:
                    var.set("yok"); continue
                if key in ("gps_lat", "gps_lon"):
                    var.set(f"{val:.6f}")
                elif key in ("bbch_guven", "hastalik_guven"):
                    var.set(f"{val:.0%}")
                else:
                    var.set(f"{val:.2f}")
            else:
                var.set(str(val))

        # GPS koordinatlari hep 0 ise "fix yok"
        if payload.get("gps_lat", 0) == 0 and payload.get("gps_lon", 0) == 0:
            if "gps_lat" in self.sensor_vars:
                self.sensor_vars["gps_lat"].set("fix yok")
            if "gps_lon" in self.sensor_vars:
                self.sensor_vars["gps_lon"].set("fix yok")

    def _maybe_update_image(self, payload: dict) -> None:
        if not _PIL_AVAILABLE or self.image_label is None:
            return
        b64 = payload.get("image") or payload.get("image_b64") or ""
        if not b64:
            return
        try:
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw))
            max_w = max(300, self.image_label.winfo_width() - 20)
            max_h = max(200, self.image_label.winfo_height() - 20)
            img.thumbnail((max_w, max_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._photo_ref = photo
            self.image_label.configure(image=photo, text="")
            if self.image_info_var is not None:
                self.image_info_var.set(f"{img.width}x{img.height}  |  {len(raw)} byte JPEG")
        except Exception as e:
            self.image_label.configure(text=f"(goruntu decode hatasi: {e})")

    # ── Pending DB onay kartlari ────────────────────────────────────
    def _add_pending_card(self, payload: dict) -> None:
        if not self.db_writable or self.pending_inner is None:
            return
        if self.pending_empty_label is not None:
            self.pending_empty_label.destroy()
            self.pending_empty_label = None

        record_id = f"rec_{int(time.time() * 1000) % 1000000}_{len(self.pending_records)}"
        self.pending_records.append({"id": record_id, "payload": payload})

        card = tk.Frame(self.pending_inner, bg=COLOR_PANEL_LT,
                        bd=1, relief="solid", highlightthickness=0)
        card.pack(fill="x", pady=4, padx=4)

        hdr = tk.Frame(card, bg=COLOR_PANEL_LT)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hdr, text=f"⏱ {payload.get('timestamp', '?')}",
                 fg=self.accent, bg=COLOR_PANEL_LT,
                 font=("Consolas", 10, "bold")).pack(side="left")
        tk.Label(hdr, text=f" rover={payload.get('rover_id', '?')}",
                 fg=COLOR_LABEL, bg=COLOR_PANEL_LT,
                 font=("Consolas", 10)).pack(side="left")
        tk.Label(hdr, text=f"  tarla={payload.get('tarla_id', '?')}",
                 fg=COLOR_LABEL, bg=COLOR_PANEL_LT,
                 font=("Consolas", 10)).pack(side="left")

        summary = self._format_record_summary(payload)
        tk.Label(card, text=summary, fg=COLOR_TEXT, bg=COLOR_PANEL_LT,
                 font=("Consolas", 9), wraplength=1100, justify="left",
                 anchor="w").pack(fill="x", padx=10, pady=(0, 4))

        anomaliler = payload.get("anomaliler")
        if anomaliler:
            try:
                if isinstance(anomaliler, str):
                    anomaliler = json.loads(anomaliler)
                if anomaliler:
                    tk.Label(card, text="⚠ Anomali: " + " | ".join(anomaliler),
                             fg=COLOR_WARN, bg=COLOR_PANEL_LT,
                             font=("Consolas", 9, "bold"),
                             wraplength=1100, justify="left",
                             anchor="w").pack(fill="x", padx=10)
            except Exception:
                pass

        btns = tk.Frame(card, bg=COLOR_PANEL_LT)
        btns.pack(fill="x", padx=10, pady=(4, 8))
        tk.Button(btns, text="✓ Onayla & DB'ye yaz",
                  bg=COLOR_OK, fg=COLOR_BTN_FG,
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  padx=14, pady=4,
                  command=lambda: self._approve(record_id, card)).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="✗ Reddet", bg=COLOR_BAD, fg=COLOR_BTN_FG,
                  font=("Segoe UI", 10), relief="flat",
                  padx=14, pady=4,
                  command=lambda: self._reject(record_id, card)).pack(side="left")

        self._update_pending_tab_title()

    def _format_record_summary(self, p: dict) -> str:
        return "\n".join([
            f"GPS=({p.get('gps_lat', 0)}, {p.get('gps_lon', 0)}) | "
            f"WP={p.get('waypoint_label') or p.get('waypoint_id', '?')}",
            f"Nem1={p.get('nem_1_pct', '?')}% | "
            f"Nem2={p.get('nem_2_pct', '?')}% | "
            f"Temp={p.get('hava_temp_c', '?')}°C | "
            f"HavaNem={p.get('hava_nem_pct', '?')}%",
            f"BBCH={p.get('bbch_sinif', '?')} ({p.get('bbch_guven', 0)}) | "
            f"Hastalik={p.get('hastalik', '-')} ({p.get('hastalik_guven', 0)})"
        ])

    def _approve(self, record_id: str, card: tk.Widget) -> None:
        rec = next((r for r in self.pending_records if r["id"] == record_id), None)
        if rec is None:
            return
        payload = rec["payload"]
        tarla_id = int(payload.get("tarla_id", 1))
        rover_data = {k: v for k, v in payload.items() if k != "tarla_id"}
        try:
            row_id = add_rover_olcum(tarla_id, rover_data)
            ts = datetime.now().strftime("%H:%M:%S")
            self._append_log(ts, "db/insert",
                             f"OK rover_olcumler.id={row_id} tarla_id={tarla_id}", "ok")
            self._flash_card_then_remove(record_id, card, COLOR_OK)
        except Exception as e:
            ts = datetime.now().strftime("%H:%M:%S")
            self._append_log(ts, "db/insert", f"HATA: {e}", "bad")

    def _reject(self, record_id: str, card: tk.Widget) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_log(ts, "db/skip", "Reddedildi (DB'ye yazilmadi)", "warn")
        self._remove_pending(record_id, card)

    def _flash_card_then_remove(self, record_id: str, card: tk.Widget, color: str) -> None:
        try:
            card.configure(bg=color)
            for child in card.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=color)
            card.after(700, lambda: self._remove_pending(record_id, card))
        except tk.TclError:
            self._remove_pending(record_id, card)

    def _remove_pending(self, record_id: str, card: tk.Widget) -> None:
        self.pending_records = [r for r in self.pending_records if r["id"] != record_id]
        try:
            card.destroy()
        except tk.TclError:
            pass
        self._update_pending_tab_title()
        if not self.pending_records and self.pending_inner is not None and self.pending_empty_label is None:
            self.pending_empty_label = tk.Label(
                self.pending_inner,
                text=f"({self.label} icin bekleyen kayit yok)",
                fg=COLOR_LABEL, bg=COLOR_PANEL,
                font=("Segoe UI", 10, "italic"))
            self.pending_empty_label.pack(pady=20, padx=12, anchor="w")

    def _update_pending_tab_title(self) -> None:
        if self._notebook is None:
            return
        try:
            self._notebook.tab(self._pending_tab_idx,
                               text=f"Bekleyen DB ({len(self.pending_records)})")
        except Exception:
            pass

    def tick(self) -> None:
        """Heartbeat tick — Dashboard her saniye cagiriyor."""
        if self.heartbeat_var is None:
            return
        if self.last_msg_time:
            age = time.time() - self.last_msg_time
            if age < 10:
                self.heartbeat_var.set(f"{age:.1f} sn once  ✓")
            elif age < 60:
                self.heartbeat_var.set(f"{age:.0f} sn once  (gecikme)")
            else:
                m = int(age // 60); s = int(age % 60)
                self.heartbeat_var.set(f"{m}dk {s}sn once  ⚠ rover sessiz")


# ──────────────────────────────────────────────────────────────────────
# MQTT Bridge
# ──────────────────────────────────────────────────────────────────────
class MqttBridge:
    def __init__(self, msg_queue: "queue.Queue[dict]") -> None:
        self.queue = msg_queue
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.host = DEFAULT_BROKER
        self.port = DEFAULT_PORT

    def connect(self, host: str, port: int) -> None:
        self.host = host; self.port = port
        self.disconnect()
        try:
            client_id = f"trakai-dashboard-{int(time.time())}"
            # paho-mqtt 2.x explicit API version (eski warning'i susturur)
            try:
                self.client = mqtt.Client(
                    client_id=client_id,
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                )
            except (AttributeError, TypeError):
                # paho-mqtt < 2.0 (eski API)
                self.client = mqtt.Client(client_id=client_id)
            self.client.on_connect    = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message    = self._on_message
            self.client.connect_async(host, port, keepalive=30)
            self.client.loop_start()
        except Exception as e:
            self.queue.put({"_type": "status", "ok": False, "msg": f"baglanti hatasi: {e}"})

    def disconnect(self) -> None:
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
            self.connected = False

    def publish(self, topic: str, payload: str) -> bool:
        if self.client is None or not self.connected:
            self.queue.put({"_type": "status", "ok": False, "msg": "publish: baglanti yok"})
            return False
        try:
            self.client.publish(topic, payload)
            return True
        except Exception as e:
            self.queue.put({"_type": "status", "ok": False, "msg": f"publish hatasi: {e}"})
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            result, mid = client.subscribe(TOPIC_WILD)
            print(f"[DASH][MQTT] CONNECTED rc=0, subscribe({TOPIC_WILD}) -> result={result} mid={mid}")
            self.queue.put({"_type": "status", "ok": True, "msg": f"Baglandi: {self.host}:{self.port}"})
        else:
            self.connected = False
            print(f"[DASH][MQTT] CONNECT REDDEDILDI rc={rc}")
            self.queue.put({"_type": "status", "ok": False, "msg": f"Baglanti reddedildi (rc={rc})"})

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        print(f"[DASH][MQTT] DISCONNECTED rc={rc}")
        self.queue.put({"_type": "status", "ok": False, "msg": "Baglanti kesildi"})

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8", errors="replace"))
        except Exception:
            payload = {"_raw": msg.payload.decode("utf-8", errors="replace")}
        rid = payload.get("rover_id", "?") if isinstance(payload, dict) else "?"
        print(f"[DASH][MQTT] msg topic={msg.topic} rover_id={rid} bytes={len(msg.payload)}")
        self.queue.put({"_type": "msg", "topic": msg.topic, "payload": payload})


# ──────────────────────────────────────────────────────────────────────
# Ana pencere
# ──────────────────────────────────────────────────────────────────────
class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TRAK-AI Rover Dashboard")
        self.geometry("1440x900")
        self.configure(bg=COLOR_BG)
        self.minsize(1100, 720)

        self.msg_queue: "queue.Queue[dict]" = queue.Queue()
        self.bridge = MqttBridge(self.msg_queue)

        # DB init (idempotent — migration burada calisir)
        if _DB_AVAILABLE:
            try:
                init_db()
            except Exception as e:
                print(f"[DB] init hatasi: {e}")

        self._build_ui()
        self.after(200, self._connect_clicked)
        self.after(100, self._drain_queue)
        self.after(1000, self._tick_status)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_PANEL, foreground=COLOR_LABEL,
                        padding=(16, 8), font=("Segoe UI", 11, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_PANEL_LT)],
                  foreground=[("selected", COLOR_ACCENT)])

        self._build_topbar()
        self._build_motor_control()
        self._build_rover_notebook()

    def _build_topbar(self) -> None:
        topbar = tk.Frame(self, bg=COLOR_BG, height=44)
        topbar.pack(side="top", fill="x", padx=8, pady=(8, 0))
        topbar.pack_propagate(False)

        tk.Label(topbar, text="TRAK-AI Rover Dashboard",
                 font=("Segoe UI", 14, "bold"),
                 fg=COLOR_ACCENT, bg=COLOR_BG).pack(side="left", padx=6)

        right = tk.Frame(topbar, bg=COLOR_BG)
        right.pack(side="right")

        tk.Label(right, text="Broker:", fg=COLOR_LABEL, bg=COLOR_BG).pack(side="left", padx=(0, 4))
        self.host_var = tk.StringVar(value=DEFAULT_BROKER)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        tk.Entry(right, textvariable=self.host_var, width=18, bg=COLOR_PANEL, fg=COLOR_TEXT,
                 insertbackground=COLOR_TEXT, relief="flat").pack(side="left")
        tk.Label(right, text=":", fg=COLOR_LABEL, bg=COLOR_BG).pack(side="left")
        tk.Entry(right, textvariable=self.port_var, width=6, bg=COLOR_PANEL, fg=COLOR_TEXT,
                 insertbackground=COLOR_TEXT, relief="flat").pack(side="left", padx=(0, 8))
        tk.Button(right, text="Baglan", bg=COLOR_ACCENT, fg=COLOR_BTN_FG,
                  relief="flat", padx=12, command=self._connect_clicked).pack(side="left", padx=(0, 8))

        self.status_indicator = tk.Label(right, text="●", font=("Segoe UI", 18),
                                         fg=COLOR_BAD, bg=COLOR_BG)
        self.status_indicator.pack(side="left")
        self.status_text = tk.Label(right, text="baglanti yok", fg=COLOR_LABEL, bg=COLOR_BG)
        self.status_text.pack(side="left", padx=(2, 6))

    def _build_motor_control(self) -> None:
        frame = tk.LabelFrame(self,
                              text=" Rover Motor Kontrol (sadece Gercek Rover) ",
                              bg=COLOR_PANEL, fg=COLOR_REAL,
                              font=("Segoe UI", 10, "bold"),
                              bd=1, relief="solid", labelanchor="nw")
        frame.pack(side="top", fill="x", padx=8, pady=(8, 0))

        inner = tk.Frame(frame, bg=COLOR_PANEL)
        inner.pack(fill="x", padx=12, pady=10)

        dur_frame = tk.Frame(inner, bg=COLOR_PANEL)
        dur_frame.pack(side="left", padx=(0, 20))
        tk.Label(dur_frame, text="Sure:", fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        self.duration_var = tk.StringVar(value=str(DEFAULT_DRIVE_MS))
        ttk.Combobox(dur_frame, textvariable=self.duration_var,
                     values=["300", "500", "1000", "2000", "3000", "5000"],
                     width=6, state="readonly").pack(side="left")
        tk.Label(dur_frame, text="ms", fg=COLOR_LABEL, bg=COLOR_PANEL).pack(side="left", padx=(2, 0))

        btns = tk.Frame(inner, bg=COLOR_PANEL)
        btns.pack(side="left")

        def big_btn(text, cmd, color=COLOR_ACCENT):
            return tk.Button(btns, text=text, bg=color, fg=COLOR_BTN_FG,
                             font=("Segoe UI", 14, "bold"),
                             relief="flat", padx=18, pady=6,
                             activebackground="#aac6ff", command=cmd)

        # Sistemi aktive/uykuya — boot anında rover IDLE'dir, hareket etmek için ACTIVATE şart
        big_btn("🟢 BAŞLAT", lambda: self._send_cmd("ACTIVATE", do=0), color=COLOR_OK).pack(side="left", padx=3)
        big_btn("💤 UYKU",   lambda: self._send_cmd("SLEEP",    do=0), color="#9aa0c4").pack(side="left", padx=(3, 20))

        # Manuel sürüş butonları
        big_btn("←  Sol",    lambda: self._send_cmd("LEFT")).pack(side="left", padx=3)
        big_btn("↑  Ileri",  lambda: self._send_cmd("FORWARD")).pack(side="left", padx=3)
        big_btn("↓  Geri",   lambda: self._send_cmd("BACK")).pack(side="left", padx=3)
        big_btn("→  Sag",    lambda: self._send_cmd("RIGHT")).pack(side="left", padx=3)
        big_btn("⏹  DUR",    lambda: self._send_cmd("STOP", do=0), color=COLOR_BAD).pack(side="left", padx=(20, 3))
        big_btn("▶  Otonom", lambda: self._send_cmd("AUTO", do=0), color=COLOR_OK).pack(side="left", padx=3)

        self.cmd_status = tk.Label(inner, text="—", fg=COLOR_LABEL, bg=COLOR_PANEL,
                                   font=("Consolas", 10))
        self.cmd_status.pack(side="right", padx=10)

    def _build_rover_notebook(self) -> None:
        """Top-level notebook: Gercek Rover + Mock Rover sekmeleri."""
        nb = ttk.Notebook(self)
        nb.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 8))

        # Gercek rover sekmesi
        real_tab = tk.Frame(nb, bg=COLOR_BG)
        nb.add(real_tab, text="🛰  Gercek Rover")
        self.real_view = RoverView(
            real_tab, label="Gercek Rover",
            matches_fn=lambda rid: not rid.startswith(MOCK_ROVER_PREFIX),
            accent=COLOR_REAL,
            db_writable=_DB_AVAILABLE,
        )

        # Mock rover sekmesi
        mock_tab = tk.Frame(nb, bg=COLOR_BG)
        nb.add(mock_tab, text="🧪  Mock Rover")
        self.mock_view = RoverView(
            mock_tab, label="Mock Rover",
            matches_fn=lambda rid: rid.startswith(MOCK_ROVER_PREFIX),
            accent=COLOR_MOCK,
            db_writable=_DB_AVAILABLE,
        )

        # GPS Harita sekmesi (OpenStreetMap tile)
        map_tab = tk.Frame(nb, bg=COLOR_BG)
        nb.add(map_tab, text="🗺  GPS Harita")
        self._build_map_view(map_tab)

        # Manuel Görsel Yükleme sekmesi (saha test backup)
        upload_tab = tk.Frame(nb, bg=COLOR_BG)
        nb.add(upload_tab, text="🖼  Görsel Yükle")
        self._build_upload_view(upload_tab)

    def _build_map_view(self, parent: tk.Widget) -> None:
        """Rover ve waypoint'leri OpenStreetMap üzerinde göster."""
        # Tk haritası eklentisi yok ise placeholder
        if not _MAP_AVAILABLE:
            tk.Label(parent,
                     text=("Harita kütüphanesi kurulu değil.\n\n"
                           "Yüklemek için PowerShell'de:\n"
                           "    pip install tkintermapview"),
                     fg=COLOR_BAD, bg=COLOR_BG,
                     font=("Segoe UI", 12, "italic"),
                     justify="center").pack(expand=True, padx=20, pady=20)
            return

        # Üst kontrol barı
        topbar = tk.Frame(parent, bg=COLOR_PANEL, height=44)
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text=" 📍 Rover Konum ve Waypoint Haritası ",
                 fg=COLOR_ACCENT, bg=COLOR_PANEL,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)

        self.map_info_var = tk.StringVar(value="GPS fix yok — sahaya çıkınca aktive olur")
        tk.Label(topbar, textvariable=self.map_info_var,
                 fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Consolas", 10)).pack(side="left", padx=20)

        tk.Button(topbar, text="🔍 Rover'a odakla",
                  bg=COLOR_ACCENT, fg=COLOR_BTN_FG, relief="flat", padx=10,
                  command=self._focus_rover_on_map).pack(side="right", padx=8)

        tk.Button(topbar, text="🎯 Waypoint'lere odakla",
                  bg=COLOR_PANEL_LT, fg=COLOR_TEXT, relief="flat", padx=10,
                  command=self._focus_waypoints_on_map).pack(side="right", padx=4)

        # Harita widget'ı
        self.map_widget = tkintermapview.TkinterMapView(
            parent, width=900, height=600, corner_radius=0)
        self.map_widget.pack(side="top", fill="both", expand=True)

        # EVR_01 saha merkezi (config.h'deki ilk waypoint civarı)
        DEFAULT_LAT = 41.0450
        DEFAULT_LON = 27.2050
        self.map_widget.set_position(DEFAULT_LAT, DEFAULT_LON)
        self.map_widget.set_zoom(18)

        # Tile server seçimi (varsayılan OpenStreetMap)
        # self.map_widget.set_tile_server("https://tile.openstreetmap.org/{z}/{x}/{y}.png")

        # Waypoint marker'ları (config.h ile tutarlı, dashboard tarafında ayrı kopya)
        # NOT: ESP32 firmware'deki waypoint'lerle senkron tutmak için ileride MQTT
        #      üzerinden config olarak da gönderilebilir.
        self._waypoints = [
            {"label": "W1_kuzey", "lat": 41.0450, "lon": 27.2050},
            {"label": "W2_dogu",  "lat": 41.0445, "lon": 27.2055},
            {"label": "W3_guney", "lat": 41.0440, "lon": 27.2050},
            {"label": "W4_bati",  "lat": 41.0445, "lon": 27.2045},
        ]
        self._waypoint_markers = []
        for wp in self._waypoints:
            marker = self.map_widget.set_marker(
                wp["lat"], wp["lon"], text=wp["label"],
                marker_color_circle="#7aa2f7",
                marker_color_outside="#27273a",
                text_color="white")
            self._waypoint_markers.append(marker)

        # Rover marker (henüz pozisyon yoksa gizli)
        self._rover_marker = None
        self._rover_path = []          # rover'ın iz koordinatları
        self._rover_path_lines = []    # çizilen line objeleri

    def _focus_rover_on_map(self) -> None:
        if not _MAP_AVAILABLE or not hasattr(self, "map_widget"):
            return
        # En son rover lat/lon'una odakla (real_view'dan al)
        lat = self.real_view.last_telemetry.get("gps_lat", 0)
        lon = self.real_view.last_telemetry.get("gps_lon", 0)
        if lat and lon and lat != 0 and lon != 0:
            self.map_widget.set_position(lat, lon)
            self.map_widget.set_zoom(19)
        else:
            self.map_info_var.set("GPS fix yok — rover'a odaklanılamadı")

    def _focus_waypoints_on_map(self) -> None:
        if not _MAP_AVAILABLE or not hasattr(self, "map_widget"):
            return
        # Waypoint'lerin merkezine odakla
        lats = [wp["lat"] for wp in self._waypoints]
        lons = [wp["lon"] for wp in self._waypoints]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        self.map_widget.set_position(center_lat, center_lon)
        self.map_widget.set_zoom(18)

    def _update_map_from_telemetry(self, payload: dict) -> None:
        """RoverView her telemetri aldığında çağırılır — haritayı güncelle."""
        if not _MAP_AVAILABLE or not hasattr(self, "map_widget"):
            return
        lat = payload.get("gps_lat", 0)
        lon = payload.get("gps_lon", 0)
        gps_valid = payload.get("gps_valid", False)

        if not gps_valid or lat == 0 or lon == 0:
            self.map_info_var.set("GPS fix yok (kapalı alanda normal)")
            return

        # Rover marker ekle/güncelle
        rover_id = payload.get("rover_id", "rover")
        if self._rover_marker is None:
            self._rover_marker = self.map_widget.set_marker(
                lat, lon, text=f"🛰 {rover_id}",
                marker_color_circle="#7eb77f",
                marker_color_outside="#27273a",
                text_color="white")
        else:
            self._rover_marker.set_position(lat, lon)

        # İz çizimi
        self._rover_path.append((lat, lon))
        if len(self._rover_path) >= 2:
            try:
                # Son 2 noktayı çizgiyle birleştir
                line = self.map_widget.set_path(self._rover_path[-2:],
                                                 color="#7eb77f", width=3)
                self._rover_path_lines.append(line)
            except Exception:
                pass

        # Bilgi güncelle
        nem = payload.get("nem_1_pct", "?")
        wp = payload.get("waypoint_label", "?")
        self.map_info_var.set(
            f"📍 ({lat:.6f}, {lon:.6f}) | Nem={nem!s:>4} | Hedef WP={wp}"
        )

    # ════════════════════════════════════════════════════════════════
    # Manuel Görsel Yükleme — saha test backup
    # ESP32-CAM ulaşılamazsa, dış kamera/telefonla çekilen görseli
    # dashboard'dan MQTT'ye yollayıp orchestrator pipeline'ı test eder
    # ════════════════════════════════════════════════════════════════
    def _build_upload_view(self, parent: tk.Widget) -> None:
        if not _PIL_AVAILABLE:
            tk.Label(parent,
                     text=("Pillow kütüphanesi yok. Yüklemek için:\n"
                           "    pip install Pillow"),
                     fg=COLOR_BAD, bg=COLOR_BG,
                     font=("Segoe UI", 12, "italic"),
                     justify="center").pack(expand=True, padx=20, pady=20)
            return

        # Ana grid: 2 kolon (sol: kontroller, sağ: önizleme + log)
        main = tk.Frame(parent, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)
        main.columnconfigure(0, weight=1, minsize=380)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # ─── SOL PANEL: Form + Butonlar ────────────────────────────
        left = tk.LabelFrame(main, text=" 📋 Test Telemetrisi ",
                             bg=COLOR_PANEL, fg=COLOR_ACCENT,
                             font=("Segoe UI", 10, "bold"),
                             bd=1, relief="solid", labelanchor="nw")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        inner = tk.Frame(left, bg=COLOR_PANEL)
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Açıklama metni
        info_text = (
            "ESP32-CAM erişilemediğinde sahada manuel test için.\n"
            "Telefonla bitki fotoğrafı çek, buradan yükle, MQTT'ye "
            "rover'dan gelmiş gibi yayınla.\n"
            "Orchestrator (LLM + RAG + DB onay) zincirini tetikler."
        )
        tk.Label(inner, text=info_text, fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Segoe UI", 9, "italic"),
                 wraplength=350, justify="left").pack(fill="x", pady=(0, 12), anchor="w")

        # Form alanları
        self._upload_vars: dict[str, tk.StringVar] = {}
        form_fields = [
            ("rover_id",      "Rover ID",       "trak-ai-rover-01"),
            ("tarla_id",      "Tarla ID",       "1"),
            ("waypoint_label","Waypoint",       "W1_kuzey"),
            ("nem_1_pct",     "Toprak Nem %",   "35"),
            ("hava_temp_c",   "Hava Sıc °C",    "22"),
            ("hava_nem_pct",  "Hava Nem %",     "60"),
            ("gps_lat",       "GPS Lat",        "41.0450"),
            ("gps_lon",       "GPS Lon",        "27.2050"),
            ("bbch_sinif",    "BBCH Tahmini",   "BBCH_50_59"),
            ("hastalik",      "Hastalık (boş=yok)", ""),
        ]
        for key, label, default in form_fields:
            row = tk.Frame(inner, bg=COLOR_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=16, anchor="w",
                     fg=COLOR_LABEL, bg=COLOR_PANEL,
                     font=("Segoe UI", 9)).pack(side="left")
            var = tk.StringVar(value=default)
            self._upload_vars[key] = var
            tk.Entry(row, textvariable=var, bg=COLOR_PANEL_LT, fg=COLOR_TEXT,
                     insertbackground=COLOR_TEXT, relief="flat", width=18).pack(
                side="left", fill="x", expand=True)

        # Resize ayarı
        tk.Frame(inner, bg=COLOR_BG, height=1).pack(fill="x", pady=8)
        resize_row = tk.Frame(inner, bg=COLOR_PANEL)
        resize_row.pack(fill="x", pady=4)
        self._upload_resize_var = tk.BooleanVar(value=True)
        tk.Checkbutton(resize_row,
                       text="QVGA'ya küçült (320×240, JPEG q=15) — gerçek CAM'i taklit",
                       variable=self._upload_resize_var,
                       bg=COLOR_PANEL, fg=COLOR_TEXT,
                       selectcolor=COLOR_PANEL_LT,
                       activebackground=COLOR_PANEL,
                       font=("Segoe UI", 9)).pack(anchor="w")

        # Dosya seçim + gönder butonları
        tk.Frame(inner, bg=COLOR_BG, height=1).pack(fill="x", pady=8)
        btns = tk.Frame(inner, bg=COLOR_PANEL)
        btns.pack(fill="x", pady=4)
        tk.Button(btns, text="📁 Dosya Seç…",
                  bg=COLOR_ACCENT, fg=COLOR_BTN_FG,
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  padx=14, pady=6,
                  command=self._upload_choose_file).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="🚀 MQTT'ye Gönder",
                  bg=COLOR_OK, fg=COLOR_BTN_FG,
                  font=("Segoe UI", 10, "bold"), relief="flat",
                  padx=14, pady=6,
                  command=self._upload_publish).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="✗ Temizle",
                  bg=COLOR_PANEL_LT, fg=COLOR_TEXT,
                  font=("Segoe UI", 10), relief="flat",
                  padx=14, pady=6,
                  command=self._upload_clear).pack(side="left")

        # Dosya bilgisi label
        self._upload_file_var = tk.StringVar(value="(dosya seçilmedi)")
        tk.Label(inner, textvariable=self._upload_file_var,
                 fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Consolas", 9),
                 wraplength=350, justify="left",
                 anchor="w").pack(fill="x", pady=(8, 0), anchor="w")

        # Durum
        self._upload_status_var = tk.StringVar(value="Hazır")
        tk.Label(inner, textvariable=self._upload_status_var,
                 fg=COLOR_OK, bg=COLOR_PANEL,
                 font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(8, 0), anchor="w")

        # ─── SAĞ PANEL: Image preview + Geçmiş log ──────────────────
        right = tk.LabelFrame(main, text=" 🖼  Önizleme ve Geçmiş ",
                              bg=COLOR_PANEL, fg=COLOR_ACCENT,
                              font=("Segoe UI", 10, "bold"),
                              bd=1, relief="solid", labelanchor="nw")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Preview alanı
        preview_frame = tk.Frame(right, bg=COLOR_PANEL)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._upload_preview = tk.Label(preview_frame,
                                         text="(henüz görsel seçilmedi)",
                                         bg="#181826", fg=COLOR_LABEL,
                                         font=("Segoe UI", 11, "italic"))
        self._upload_preview.pack(fill="both", expand=True)
        self._upload_photo_ref: Optional[ImageTk.PhotoImage] = None
        self._upload_jpeg_b64: Optional[str] = None

        # Geçmiş log
        log_frame = tk.Frame(right, bg=COLOR_PANEL)
        log_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(log_frame, text="Yükleme Geçmişi:",
                 fg=COLOR_LABEL, bg=COLOR_PANEL,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self._upload_log = tk.Text(log_frame, bg="#181826", fg=COLOR_TEXT,
                                    font=("Consolas", 9), wrap="word",
                                    relief="flat", height=5)
        self._upload_log.pack(fill="x")
        self._upload_log.tag_configure("ok",   foreground=COLOR_OK)
        self._upload_log.tag_configure("warn", foreground=COLOR_WARN)
        self._upload_log.tag_configure("bad",  foreground=COLOR_BAD)
        self._upload_log.tag_configure("ts",   foreground=COLOR_ACCENT)

    def _upload_choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Görsel dosyasını seç",
            filetypes=[("Görsel dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp"),
                       ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path)
            original_size = img.size
            if self._upload_resize_var.get():
                # Gerçek ESP32-CAM çıktısını taklit: QVGA, JPEG q=15
                img.thumbnail((320, 240), Image.LANCZOS)
                # JPEG dönüşümü için RGB'ye çevir (PNG alfa olabilir)
                if img.mode != "RGB":
                    img = img.convert("RGB")
            # Preview için PIL → tk
            preview_img = img.copy()
            preview_img.thumbnail(
                (max(400, self._upload_preview.winfo_width() - 20),
                 max(300, self._upload_preview.winfo_height() - 20)),
                Image.LANCZOS)
            self._upload_photo_ref = ImageTk.PhotoImage(preview_img)
            self._upload_preview.configure(image=self._upload_photo_ref, text="")

            # JPEG buffer + base64
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=15 if self._upload_resize_var.get() else 85)
            jpeg_bytes = buf.getvalue()
            self._upload_jpeg_b64 = base64.b64encode(jpeg_bytes).decode("ascii")

            filename = os.path.basename(path)
            self._upload_file_var.set(
                f"📁 {filename}\n"
                f"   Original: {original_size[0]}×{original_size[1]}\n"
                f"   İşlenmiş: {img.size[0]}×{img.size[1]}\n"
                f"   JPEG boyut: {len(jpeg_bytes) / 1024:.1f} KB\n"
                f"   Base64: {len(self._upload_jpeg_b64) / 1024:.1f} KB")
            self._upload_status_var.set("✓ Hazır — MQTT'ye Gönder ile yayınla")
            self._upload_log_add(f"Yüklendi: {filename} → {len(jpeg_bytes)} byte JPEG", "ok")
        except Exception as e:
            self._upload_status_var.set(f"✗ Hata: {e}")
            self._upload_log_add(f"Yükleme hatası: {e}", "bad")

    def _upload_publish(self) -> None:
        if not self._upload_jpeg_b64:
            messagebox.showwarning("Görsel yok",
                                   "Önce 'Dosya Seç' ile bir görsel seçin.")
            return
        # Form değerlerini al
        try:
            tarla_id = int(self._upload_vars["tarla_id"].get())
            nem      = float(self._upload_vars["nem_1_pct"].get())
            temp     = float(self._upload_vars["hava_temp_c"].get())
            havanem  = float(self._upload_vars["hava_nem_pct"].get())
            gps_lat  = float(self._upload_vars["gps_lat"].get())
            gps_lon  = float(self._upload_vars["gps_lon"].get())
        except ValueError as e:
            messagebox.showerror("Form hatası",
                                 f"Sayısal değer parse edilemedi: {e}")
            return

        rover_id    = self._upload_vars["rover_id"].get().strip()
        waypoint_lb = self._upload_vars["waypoint_label"].get().strip()
        bbch        = self._upload_vars["bbch_sinif"].get().strip()
        hastalik    = self._upload_vars["hastalik"].get().strip()

        # MQTT payload — gerçek rover formatıyla aynı
        payload = {
            "timestamp":    int(time.time()),
            "rover_id":     rover_id,
            "tarla_id":     tarla_id,
            "saha_id":      "EVR_01",
            "durum":        "MANUEL_UPLOAD",       # gerçek rover'dan ayırma
            "gps_lat":      gps_lat,
            "gps_lon":      gps_lon,
            "gps_valid":    True,
            "nem_1_pct":    nem,
            "hava_temp_c":  temp,
            "hava_nem_pct": havanem,
            "bbch_sinif":   bbch,
            "bbch_guven":   0.75,                  # manuel: orta güven
            "waypoint_id":  0,
            "waypoint_label": waypoint_lb,
            "image":        self._upload_jpeg_b64,
        }
        if hastalik:
            payload["hastalik"] = hastalik
            payload["hastalik_guven"] = 0.85
        payload_str = json.dumps(payload, ensure_ascii=False)

        ok = self.bridge.publish(TOPIC_TELEMETRY, payload_str)
        if ok:
            size_kb = len(payload_str) / 1024
            self._upload_status_var.set(f"✓ Gönderildi! ({size_kb:.1f} KB)")
            self._upload_log_add(
                f"MQTT → {TOPIC_TELEMETRY} ({size_kb:.1f} KB) — "
                f"rover={rover_id} tarla={tarla_id} nem={nem}%", "ok")
        else:
            self._upload_status_var.set("✗ Yayın başarısız — broker bağlantısı yok")
            self._upload_log_add("MQTT yayın HATA — bridge offline", "bad")

    def _upload_clear(self) -> None:
        self._upload_jpeg_b64 = None
        self._upload_photo_ref = None
        self._upload_preview.configure(image="", text="(henüz görsel seçilmedi)")
        self._upload_file_var.set("(dosya seçilmedi)")
        self._upload_status_var.set("Hazır")

    def _upload_log_add(self, msg: str, tag: str = "ok") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._upload_log.insert("end", f"[{ts}] ", "ts")
        self._upload_log.insert("end", f"{msg}\n", tag)
        self._upload_log.see("end")

    # ── Event handler'lar ────────────────────────────────────────────
    def _connect_clicked(self) -> None:
        host = self.host_var.get().strip() or DEFAULT_BROKER
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            port = DEFAULT_PORT
        self.bridge.connect(host, port)

    def _on_close(self) -> None:
        self.bridge.disconnect()
        self.destroy()

    def _send_cmd(self, cmd: str, do: Optional[int] = None) -> None:
        """Motor komutu yayinla — sadece gercek rover icin."""
        try:
            duration = int(self.duration_var.get())
        except ValueError:
            duration = DEFAULT_DRIVE_MS
        msg = {"cmd": cmd}
        if do is None:
            msg["duration_ms"] = duration
        elif do > 0:
            msg["duration_ms"] = do
        ok = self.bridge.publish(TOPIC_CMD, json.dumps(msg))
        ts = datetime.now().strftime("%H:%M:%S")
        info = f"{cmd}" + (f" ({msg.get('duration_ms', 0)}ms)" if "duration_ms" in msg else "")
        if ok:
            self.cmd_status.configure(text=f"[{ts}] → {info}", fg=COLOR_OK)
            self.real_view._append_log(ts, TOPIC_CMD, info, "cmd")
        else:
            self.cmd_status.configure(text=f"[{ts}] ✗ {info} (offline)", fg=COLOR_BAD)

    # ── Periyodik isler ─────────────────────────────────────────────
    def _drain_queue(self) -> None:
        try:
            while True:
                item = self.msg_queue.get_nowait()
                self._handle_item(item)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._drain_queue)

    def _handle_item(self, item: dict) -> None:
        if item.get("_type") == "status":
            self._set_status(item["ok"], item["msg"])
        elif item.get("_type") == "msg":
            self._route_mqtt(item["topic"], item["payload"])

    def _set_status(self, ok: bool, msg: str) -> None:
        color = COLOR_OK if ok else COLOR_BAD
        self.status_indicator.configure(fg=color)
        self.status_text.configure(text=msg)

    def _route_mqtt(self, topic: str, payload: dict) -> None:
        """rover_id'ye gore dogru RoverView'a yonlendir."""
        ts = datetime.now().strftime("%H:%M:%S")
        rover_id = payload.get("rover_id", "") or ""

        view = self.mock_view if self.mock_view.matches(rover_id) else self.real_view

        if topic == TOPIC_TELEMETRY:
            view.handle_telemetry(payload, ts)
            # GPS Harita güncellemesi — sadece gerçek rover için (mock GPS sabit nokta)
            if view is self.real_view:
                try:
                    self._update_map_from_telemetry(payload)
                except Exception:
                    pass   # harita widget'ı kurulu değilse sessiz geç
        elif topic == TOPIC_ADVISORY:
            view.handle_advisory(payload, ts)
        elif topic == TOPIC_DB_PENDING:
            view.handle_pending(payload, ts)
        elif topic == TOPIC_CMD:
            pass   # Kendi yolladigimiz komut echo'su, sessiz gec
        else:
            view._append_log(ts, topic, str(payload)[:80], "warn")

    def _tick_status(self) -> None:
        self.real_view.tick()
        self.mock_view.tick()
        self.after(1000, self._tick_status)


def main() -> None:
    Dashboard().mainloop()


if __name__ == "__main__":
    main()
