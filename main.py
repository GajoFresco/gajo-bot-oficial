import os
import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials
import json

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')
MENU_IMAGE_URL = os.environ.get('MENU_IMAGE_URL')
WEBHOOK_TOKEN = "GajoBot2026"

def obtener_datos(mensaje):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        datos = hoja.get_all_records()
        
        msg = mensaje.upper().strip()
        print(f"🔎 [EXCEL] Buscando coincidencia para: '{msg}'", flush=True)

        for item in datos:
            raw_id = str(item.get("ID_Unico_QR", ""))
            # Extraemos el ID final del link (ej: G-001-X8P)
            id_db = raw_id.split("Gajo%20")[-1].upper().strip() if "Gajo%20" in raw_id else raw_id.upper().strip()
            
            if id_db in msg:
                print(f"✅ [EXCEL] ¡Match encontrado! Vaso #{item.get('Numero_Vaso')}", flush=True)
                return item
        return None
    except Exception as e:
        print(f"❌ [EXCEL] Error: {e}", flush=True)
        return None

def enviar(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"📤 [META] Status: {r.status_code} | Respuesta: {r.text}", flush=True)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    if request.method == 'POST':
        data = request.get_json()
        
        # --- ESTO TIENE QUE SALIR SÍ O SÍ EN RENDER ---
        print("\n" + "="*30, flush=True)
        print("📥 ¡RECIBÍ ALGO DE META!", flush=True)
        print(json.dumps(data, indent=2), flush=True)
        print("="*30 + "\n", flush=True)
        
        try:
            # Detectar si es un mensaje
            value = data['entry'][0]['changes'][0]['value']
            if 'messages' in value:
                msg_obj = value['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    texto = msg_obj['text']['body']
                    print(f"📩 [MENSAJE] De {num_cliente}: {texto}", flush=True)
                    
                    info = obtener_datos(texto)
                    if info:
                        v, c, m = info.get('Numero_Vaso'), info.get('Codigo_Secreto'), info.get('Mantra_Asignado')
                        header = "¿Qué Gajo eres hoy? 🍹✨\n\n"
                        
                        if str(v) in ["43", "100"]:
                            res = f"{header}¡Felicidades! 🎉 Gajo Premiado (#{v}).\nCódigo: {c} 🎁"
                        else:
                            res = f"{header}¡Eres el Gajo #{v}!\n\n*Mantra: {m}*"
                        
                        enviar(res, num_cliente)
                    else:
                        enviar("¡Huy! 🕵️‍♂️ Ese Gajo no está en la canasta o vienes del futuro. ⏳", num_cliente)
            else:
                print("ℹ️ [INFO] No es un mensaje (es una notificación de estado).", flush=True)

        except Exception as e:
            print(f"❌ [ERROR] Fallo al procesar el JSON: {e}", flush=True)
        
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
