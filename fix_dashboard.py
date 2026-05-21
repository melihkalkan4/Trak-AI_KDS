import re

with open('src/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('VERI_KEYWORDS = [')
end_idx = content.find('def page_tarim_asistani():')

new_func = """
def generate_chat_response(user_question: str, vectorstore, tarla_id: int) -> dict:
    from cp4_rag.agentic_rag import handle_user_request
    from database import get_tarla, get_son_tahmin, get_rover_olcumler
    from weather_service import get_current_weather
    
    tarla = get_tarla(tarla_id) or {}
    tahmin = get_son_tahmin(tarla_id) or {}
    olcumler = get_rover_olcumler(tarla_id, limit=1)
    son_rover = olcumler[0] if olcumler else {}
    
    try:
        wx_cur = get_current_weather()
        if isinstance(wx_cur, tuple):
            wx_cur = wx_cur[0]
    except:
        wx_cur = {}
    if wx_cur is None:
        wx_cur = {}
        
    tarla_verileri = {
        "urun": tarla.get("aktif_urun", "Bilinmiyor"),
        "alan_dekar": tarla.get("alan_dekar", "Bilinmiyor"),
        "toprak_tipi": tarla.get("toprak_tipi", "Bilinmiyor"),
        "ndvi_mevcut": tahmin.get("ndvi_mevcut", "Bilinmiyor"),
        "ndvi_tahmin": tahmin.get("ndvi_tahmin_7gun", "Bilinmiyor"),
        "saglik_durumu": tahmin.get("saglik_durumu", "Bilinmiyor"),
        "verim_tahmini": tahmin.get("verim_tahmini_kg_dekar", "Bilinmiyor"),
        "toprak_nemi": son_rover.get("nem_1_pct") or wx_cur.get("soil_moisture", 100),
        "hava_sicaklik": son_rover.get("hava_temp_c") or wx_cur.get("temp_c", 20),
        "hastalik": son_rover.get("hastalik", "Yok") or "Yok"
    }
    
    return handle_user_request(user_question, tarla_verileri, vectorstore)


"""

content = content[:start_idx] + new_func + content[end_idx:]

content = content.replace('def page_tarim_asistani():', 'def page_tarim_asistani(tarla_id: int):')
content = content.replace('result = generate_chat_response(user_input, vectorstore, chunks)', 'result = generate_chat_response(user_input, vectorstore, tarla_id)')
content = content.replace('page_tarim_asistani()', 'page_tarim_asistani(selected_id)')

with open('src/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated dashboard.py!')