from pathlib import Path

import spss
import SpssClient


base = Path(r"C:\Users\Melih Kalkan\Desktop\Trak-AI_KDS\outputs\spss_moderation")
with open(str(base / "spss_hiyerarsik_regresyon_from_sav.sps"), "r", encoding="utf-8") as handle:
    syntax = handle.read()
output_path = str(base / "spss_regresyon_output.spv")

SpssClient.StartClient()
doc = SpssClient.NewOutputDoc()
doc.SetAsDesignatedOutputDoc()
try:
    spss.Submit(syntax)
    print("output_items", doc.GetOutputItems().Size())
    doc.SaveAs(output_path)
finally:
    SpssClient.StopClient()

print(output_path)
