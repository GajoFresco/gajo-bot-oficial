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
        
        mensaje_clean = mensaje_recibido.upper()
        print(f"🔎 DEBUG - Buscando coincidencia para: '{mensaje_clean}'")

        for item in datos:
            url_qr = str(item.get("ID_Unico_QR", ""))
            # Extraemos el ID del link (ej: G-001-X8P)
            if "Gajo%20" in url_qr:
                id_esperado = url_qr.split("Gajo%20")[-1].upper()
            else:
                id_esperado = url_qr.upper()

            if id_esperado and id_esperado in mensaje_clean:
                print(f"✅ DEBUG - ¡Match encontrado! Vaso #{item.get('Numero_Vaso')}")
                return item
        
        print("❓ DEBUG - No se encontró el ID en el Excel.")
        return None
    except Exception as e:
        print(f"❌ DEBUG - Error en Sheets: {e}")
        return None

def enviar_wa_texto(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"📤 DEBUG - Status Envío: {r.status_code}")
    if r.status_code != 200:
        print(f"❌ DEBUG - Error de Meta: {r.text}")

def enviar_menu_media(numero):
    if not MENU_IMAGE_URL: return
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", "to": numero,
        "type": "image", "image": {"link": MENU_IMAGE_URL}
    }
    requests.post(url, headers=headers, json=payload)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            if data.get('entry') and data['entry'][0].get('changes') and \
               data['entry'][0]['changes'][0]['value'].get('messages'):
                
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    msg_txt = msg_obj['text']['body'].strip()
                    print(f"\n📩 DEBUG - Mensaje de {num_cliente}: {msg_txt}")
                    
                    info = obtener_datos_vitaminados(msg_txt)
                    
                    if info:
                        v = info.get('Numero_Vaso')
                        c = info.get('Codigo_Secreto')
                        m = info.get('Mantra_Asignado')
                        header = "¿Qué Gajo eres hoy? 🍹✨\n\n"
                        
                        if str(v) in ["43", "100"]:
                            res = f"{header}¡Felicidades! 🎉 Eres el **Gajo Premiado (#{v})**.\nCódigo: **{c}** 🎁\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        else:
                            res = f"{header}¡Eres el **Gajo #{v}**!\n\n*Mantra: {m}*\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        
                        enviar_wa_texto(res, num_cliente)
                        enviar_menu_media(num_cliente)
                    else:
                        fallback = "¡Huy! 🕵️‍♂️ Ese Gajo no está en la canasta o vienes del futuro. ⏳\n¡Escanea un QR real!"
                        enviar_wa_texto(fallback, num_cliente)
        except Exception as e:
            print(f"❌ DEBUG - Error General: {e}")
        
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
