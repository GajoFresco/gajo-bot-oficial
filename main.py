import os
import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')
MENU_IMAGE_URL = os.environ.get('MENU_IMAGE_URL')
WEBHOOK_TOKEN = "GajoBot2026"

def obtener_datos_vitaminados(mensaje_recibido):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        datos = hoja.get_all_records()
        
        # Limpiamos lo que mandó el cliente
        msg = mensaje_recibido.upper().strip()
        print(f"🔎 DEBUG - Buscando '{msg}' en el Excel...")

        for item in datos:
            # Sacamos el ID de la columna A (ej: G-001-X8P)
            raw_id = str(item.get("ID_Unico_QR", ""))
            # Si es un link de wa.me, cortamos para quedarnos con el final
            id_db = raw_id.split("Gajo%20")[-1].upper().strip() if "Gajo%20" in raw_id else raw_id.upper().strip()

            if id_db in msg:
                print(f"✅ DEBUG - ¡Match! Vaso #{item.get('Numero_Vaso')}")
                return item
        
        print("❓ DEBUG - No hubo match en el Excel.")
        return None
    except Exception as e:
        print(f"❌ DEBUG - Error Sheets: {e}")
        return None

def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"📤 DEBUG - Meta Status: {r.status_code}")
    if r.status_code != 200:
        print(f"❌ DEBUG - Error Meta: {r.text}")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    if request.method == 'POST':
        data = request.get_json()
        
        # --- EL SENSOR MAESTRO ---
        print(f"\n--- 📥 NUEVO EVENTO ---")
        
        try:
            # Revisamos si el JSON trae mensajes
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    msg_txt = msg_obj['text']['body']
                    print(f"📩 MENSAJE RECIBIDO de {num_cliente}: {msg_txt}")
                    
                    info = obtener_datos_vitaminados(msg_txt)
                    
                    if info:
                        v, c, m = info.get('Numero_Vaso'), info.get('Codigo_Secreto'), info.get('Mantra_Asignado')
                        header = "¿Qué Gajo eres hoy? 🍹✨\n\n"
                        
                        if str(v) in ["43", "100"]:
                            res = f"{header}¡Felicidades! 🎉 Eres el **Gajo Premiado (#{v})**.\nCódigo: **{c}** 🎁\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        else:
                            res = f"{header}¡Eres el **Gajo #{v}**!\n\n*Mantra: {m}*\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        
                        enviar_wa(res, num_cliente)
                    else:
                        enviar_wa("¡Huy! 🕵️‍♂️ Ese Gajo no está en la canasta. ¿Seguro que escaneaste bien? 🍋", num_cliente)
            
            elif 'statuses' in data['entry'][0]['changes'][0]['value']:
                print("ℹ️ DEBUG - Notificación de estado (Enviado/Leído). Ignorando...")

        except Exception as e:
            print(f"❌ DEBUG - Error procesando: {e}")
        
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
