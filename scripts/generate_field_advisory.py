"""
TRAK-AI Saha Verisi LLM Tavsiye Üretici
========================================

DB'den belirli bir saha çıkış verisini okur, sınıf bazında istatistik
çıkarır, LLM'den (Ollama / gemma3:4b) Türkçe çiftçi tavsiyesi alır ve
saha_raporlari tablosuna kaydeder.

LLM çağrı sayısı: Toplam sınıf sayısı + 1 genel = ~4 çağrı, ~3-5 dakika.

Kullanım:
    python scripts/generate_field_advisory.py
    python scripts/generate_field_advisory.py --kaynak gercek_saha_27may2026
    python scripts/generate_field_advisory.py --no-rag      # RAG'sız, daha hızlı

Sonuç:
  - Konsolda her tavsiyenin özeti
  - saha_raporlari tablosunda kalıcı kayıt
  - Streamlit dashboard'da görüntülenebilir hale gelir
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import init_db, get_connection            # noqa: E402

# LLM engine import - cp4_rag içinden
sys.path.insert(0, str(SRC_DIR / "cp4_rag"))
try:
    from llm_engine import check_ollama_connection, rover_alert_query, query_llm
    _LLM_OK = True
    _LLM_ERR = ""
except Exception as e:
    _LLM_OK = False
    _LLM_ERR = str(e)


DEFAULT_KAYNAK = "gercek_saha_27may2026"
DEFAULT_TARLA  = 1


# ── İstatistik çıkarımı ─────────────────────────────────────────────
def aggregate_field_data(kaynak: str) -> dict:
    """rover_olcumler tablosundan kaynak filtreli özet istatistikler."""
    with get_connection() as conn:
        # Genel istatistikler
        general = conn.execute("""
            SELECT
                COUNT(*) as total,
                MIN(timestamp) as min_ts,
                MAX(timestamp) as max_ts,
                AVG(nem_1_pct) as avg_nem,
                MIN(nem_1_pct) as min_nem,
                MAX(nem_1_pct) as max_nem,
                AVG(hava_temp_c) as avg_temp,
                MIN(hava_temp_c) as min_temp,
                MAX(hava_temp_c) as max_temp,
                AVG(engel_on_cm) as avg_engel
            FROM rover_olcumler
            WHERE kaynak = ?
        """, (kaynak,)).fetchone()

        # Sınıf bazında dağılım
        per_class = conn.execute("""
            SELECT
                bbch_sinif,
                COUNT(*) as n,
                AVG(nem_1_pct) as avg_nem,
                AVG(hava_temp_c) as avg_temp,
                AVG(goruntu_guven) as avg_guven,
                MIN(timestamp) as ilk_gozlem,
                MAX(timestamp) as son_gozlem
            FROM rover_olcumler
            WHERE kaynak = ? AND bbch_sinif IS NOT NULL
            GROUP BY bbch_sinif
            ORDER BY n DESC
        """, (kaynak,)).fetchall()

    return {
        "general": dict(general) if general else {},
        "classes": [dict(r) for r in per_class],
        "kaynak": kaynak,
    }


# ── Anomali context inşası (sınıf bazlı) ────────────────────────────
def build_class_context(class_data: dict, general: dict, kaynak: str) -> str:
    """Tek bir BBCH sınıfı için LLM'e gidecek anomali açıklaması."""
    sinif    = class_data["bbch_sinif"]
    n        = class_data["n"]
    avg_nem  = class_data["avg_nem"] or 0
    avg_temp = class_data["avg_temp"] or 0
    avg_guv  = class_data["avg_guven"] or 0
    ilk_ts   = class_data.get("ilk_gozlem", "")
    son_ts   = class_data.get("son_gozlem", "")

    total = general.get("total", 0)
    oran  = (n / total * 100) if total > 0 else 0

    # Sınıf adına göre anomali tipi
    sinif_lower = sinif.lower()
    if "hastalik" in sinif_lower:
        siddet = "KRİTİK" if oran > 30 else ("YÜKSEK" if oran > 15 else "ORTA")
        hastalik_tip = ("Pas (Puccinia)" if "pas" in sinif_lower
                        else ("Mildiyo (Plasmopara)" if "mildiyo" in sinif_lower
                              else sinif))
        return (
            f"BİTKİ HASTALIĞI TESPİTİ ({siddet} seviyeli)\n"
            f"Saha: {kaynak}\n"
            f"Hastalık: {hastalik_tip}\n"
            f"Tespit edilen fotoğraf: {n} adet (toplam {total} ölçümün %{oran:.1f}'i)\n"
            f"YOLOv8 sınıflandırma ortalama güven: %{avg_guv*100:.0f}\n"
            f"Ortalama toprak nemi (bu sınıfta): %{avg_nem:.1f}\n"
            f"Ortalama hava sıcaklığı: {avg_temp:.1f}°C\n"
            f"İlk gözlem: {ilk_ts}, son gözlem: {son_ts}\n"
            f"\nLütfen bu hastalığın kontrolü için pratik, eyleme dönük "
            f"Türkçe tavsiye ver. Önerilen ilaçlar, dozaj, uygulama zamanı, "
            f"havalandırma/sulama önerileri dahil. Tarla EVR_01 (Vize/Kırklareli)."
        )
    elif "saglikli" in sinif_lower or "sağlıklı" in sinif_lower:
        return (
            f"SAĞLIKLI BİTKİ ÖLÇÜMÜ (bilgilendirme)\n"
            f"Saha: {kaynak}\n"
            f"Sınıf: {sinif}\n"
            f"Tespit: {n} adet (toplam {total} ölçümün %{oran:.1f}'i)\n"
            f"Ortalama güven: %{avg_guv*100:.0f}\n"
            f"Ortalama toprak nemi: %{avg_nem:.1f}\n"
            f"Ortalama hava sıcaklığı: {avg_temp:.1f}°C\n"
            f"\nBitki sağlıklı görünüyor. Bu durumun sürdürülmesi için "
            f"önleyici sulama, gübreleme ve hastalık takip önerilerini "
            f"Türkçe ver. Trakya buğdayı için sezonluk planlama dahil."
        )
    elif "stres" in sinif_lower:
        return (
            f"BİTKİ STRES TESPİTİ\n"
            f"Saha: {kaynak}\n"
            f"Stres tipi: {sinif}\n"
            f"Tespit: {n} adet (toplam {total} ölçümün %{oran:.1f}'i)\n"
            f"Ortalama nem: %{avg_nem:.1f}\n"
            f"Ortalama sıcaklık: {avg_temp:.1f}°C\n"
            f"\nStresin azaltılması için Türkçe tavsiye ver "
            f"(sulama planı, gübre, gölgeleme vb.)."
        )
    else:
        return (
            f"Sınıf: {sinif}\n"
            f"Tespit: {n} kayıt (%{oran:.1f})\n"
            f"Bu sınıf için çiftçi tavsiyesi ver."
        )


def build_general_context(data: dict) -> str:
    """Tüm saha çıkışı için genel özet anomali context'i."""
    g = data["general"]
    classes = data["classes"]
    total = g.get("total", 0)

    classes_str = "\n".join(
        f"  - {c['bbch_sinif']}: {c['n']} adet (%{c['n']/total*100:.1f})"
        for c in classes if c["bbch_sinif"]
    )

    return (
        f"SAHA ÇIKIŞ ÖZETİ — {data['kaynak']}\n"
        f"Tarla: EVR_01 (Vize/Kırklareli)\n"
        f"Toplam ölçüm: {total}\n"
        f"Süre: {g.get('min_ts', '?')} -> {g.get('max_ts', '?')}\n"
        f"\nSENSÖR ORTALAMALARI:\n"
        f"  Toprak Nemi: ort %{g.get('avg_nem', 0):.1f} "
        f"(min %{g.get('min_nem', 0):.1f}, max %{g.get('max_nem', 0):.1f})\n"
        f"  Hava Sıcaklık: ort {g.get('avg_temp', 0):.1f}°C "
        f"(min {g.get('min_temp', 0):.1f}, max {g.get('max_temp', 0):.1f})\n"
        f"  Engel ortalama: {g.get('avg_engel', 0):.0f} cm\n"
        f"\nSINIFLANDIRMA DAĞILIMI (YOLOv8):\n"
        f"{classes_str}\n"
        f"\nBu saha çıkışı için **bütüncül bir Türkçe tavsiye** ver: "
        f"genel sağlık durumu, acil yapılacaklar, hangi sıraya göre "
        f"müdahale edilmeli, sulama/gübre/ilaç önceliği. "
        f"Çiftçinin pratik kararlarını destekleyecek şekilde."
    )


# ── DB'ye tavsiye kaydı ─────────────────────────────────────────────
def save_advisory(record: dict) -> int:
    """saha_raporlari tablosuna tek tavsiye kayıt et."""
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO saha_raporlari
                (tarla_id, kaynak, rapor_tipi, bbch_sinif, olcum_sayisi,
                 ortalama_nem, ortalama_temp, ortalama_guven,
                 anomali_aciklama, llm_tavsiye, llm_sure_sec, llm_model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["tarla_id"], record["kaynak"], record["rapor_tipi"],
            record.get("bbch_sinif"),
            record.get("olcum_sayisi"), record.get("ortalama_nem"),
            record.get("ortalama_temp"), record.get("ortalama_guven"),
            record.get("anomali_aciklama"), record.get("llm_tavsiye"),
            record.get("llm_sure_sec"), record.get("llm_model"),
        ))
        conn.commit()
        return int(cur.lastrowid)


# ── Ana akış ────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="DB'den saha LLM tavsiye üret")
    ap.add_argument("--kaynak", default=DEFAULT_KAYNAK,
                    help=f"Veri kaynak filtresi (default: {DEFAULT_KAYNAK})")
    ap.add_argument("--tarla-id", type=int, default=DEFAULT_TARLA)
    ap.add_argument("--skip-general", action="store_true",
                    help="Sadece sınıf bazlı, genel tavsiye atla")
    ap.add_argument("--dry-run", action="store_true",
                    help="LLM çağrı yapma, sadece istatistik ve prompt göster")
    args = ap.parse_args()

    if not _LLM_OK and not args.dry_run:
        print(f"[HATA] LLM engine import edilemedi: {_LLM_ERR}")
        print(f"       --dry-run ile sadece istatistikleri görebilirsin")
        sys.exit(1)

    init_db()

    print(f"[FIELD] Kaynak:    {args.kaynak}")
    print(f"[FIELD] Tarla ID:  {args.tarla_id}")
    print(f"[FIELD] " + "=" * 50)

    # 1. Veri özetini al
    data = aggregate_field_data(args.kaynak)
    g = data["general"]
    total = g.get("total", 0)

    if total == 0:
        print(f"[HATA] '{args.kaynak}' kaynaklı kayıt bulunamadı.")
        sys.exit(1)

    print(f"[FIELD] Toplam ölçüm: {total}")
    print(f"[FIELD] Süre:         {g['min_ts']} -> {g['max_ts']}")
    print(f"[FIELD] Nem ort:      %{g['avg_nem']:.1f}")
    print(f"[FIELD] Temp ort:     {g['avg_temp']:.1f}°C")
    print(f"[FIELD] " + "-" * 50)
    print(f"[FIELD] Sınıf dağılımı:")
    for c in data["classes"]:
        oran = c["n"] / total * 100
        print(f"          {c['n']:3d}x {c['bbch_sinif']:<25s} (%{oran:.1f})")
    print(f"[FIELD] " + "=" * 50)

    if args.dry_run:
        print()
        print("--- DRY RUN — Genel context preview ---")
        print(build_general_context(data))
        for c in data["classes"]:
            print()
            print(f"--- Sınıf context: {c['bbch_sinif']} ---")
            print(build_class_context(c, g, args.kaynak))
        return

    # 2. Ollama bağlantısını kontrol et
    if not check_ollama_connection():
        print("[HATA] Ollama bağlantısı kurulamadı. 'ollama serve' çalışıyor mu?")
        sys.exit(1)

    print("[FIELD] Ollama bağlandı. LLM çağrıları başlıyor...")
    print()

    advisories = []

    # 3. Her sınıf için LLM tavsiyesi
    for class_data in data["classes"]:
        sinif = class_data["bbch_sinif"]
        print(f"[LLM] Sınıf bazlı tavsiye üretiliyor: {sinif} ({class_data['n']} kayıt)")
        anomaly_ctx = build_class_context(class_data, g, args.kaynak)

        t0 = time.time()
        try:
            result = rover_alert_query(
                anomaly_context=anomaly_ctx,
                field_context="",  # RAG'sız basit mod (daha hızlı, ~30-90sn yerine ~30sn)
            )
            duration = round(time.time() - t0, 1)
            answer = result.get("answer", "(boş yanıt)")
            tokens = result.get("tokens", 0)
            model = result.get("model", "gemma3:4b")
            print(f"[LLM]   OK {duration:.1f}s, {tokens} token, {len(answer)} karakter")
            print(f"[LLM]   İlk 200 karakter: {answer[:200]}...")
            print()

            rec = {
                "tarla_id": args.tarla_id,
                "kaynak": args.kaynak,
                "rapor_tipi": "sinif_bazli",
                "bbch_sinif": sinif,
                "olcum_sayisi": class_data["n"],
                "ortalama_nem": class_data["avg_nem"],
                "ortalama_temp": class_data["avg_temp"],
                "ortalama_guven": class_data["avg_guven"],
                "anomali_aciklama": anomaly_ctx,
                "llm_tavsiye": answer,
                "llm_sure_sec": duration,
                "llm_model": model,
            }
            row_id = save_advisory(rec)
            print(f"[DB]    Kayıt eklendi: saha_raporlari.id={row_id}")
            advisories.append(rec)
            print()
        except Exception as e:
            print(f"[LLM]   HATA: {e}")
            print()

    # 4. Genel tavsiye (opsiyonel)
    if not args.skip_general:
        print(f"[LLM] Genel saha tavsiyesi üretiliyor...")
        anomaly_ctx = build_general_context(data)
        t0 = time.time()
        try:
            result = rover_alert_query(
                anomaly_context=anomaly_ctx,
                field_context="",
            )
            duration = round(time.time() - t0, 1)
            answer = result.get("answer", "(boş yanıt)")
            tokens = result.get("tokens", 0)
            model = result.get("model", "gemma3:4b")
            print(f"[LLM]   OK {duration:.1f}s, {tokens} token, {len(answer)} karakter")
            print(f"[LLM]   İlk 200 karakter: {answer[:200]}...")

            rec = {
                "tarla_id": args.tarla_id,
                "kaynak": args.kaynak,
                "rapor_tipi": "genel",
                "bbch_sinif": None,
                "olcum_sayisi": total,
                "ortalama_nem": g["avg_nem"],
                "ortalama_temp": g["avg_temp"],
                "ortalama_guven": None,
                "anomali_aciklama": anomaly_ctx,
                "llm_tavsiye": answer,
                "llm_sure_sec": duration,
                "llm_model": model,
            }
            row_id = save_advisory(rec)
            print(f"[DB]    Genel tavsiye kaydedildi: saha_raporlari.id={row_id}")
            advisories.append(rec)
        except Exception as e:
            print(f"[LLM]   HATA: {e}")

    # 5. Özet rapor
    print()
    print("=" * 60)
    print(f"TAMAMLANDI — {len(advisories)} tavsiye üretildi + DB'ye yazıldı")
    print("=" * 60)
    toplam_sure = sum(a["llm_sure_sec"] for a in advisories)
    print(f"  Toplam LLM süresi:  {toplam_sure:.0f} saniye")
    print(f"  Kayıt yeri:         saha_raporlari (kaynak='{args.kaynak}')")
    print()
    print(f"Streamlit dashboard'da görmek için:")
    print(f"  streamlit run src/dashboard_pages/saha_raporu.py")


if __name__ == "__main__":
    main()
