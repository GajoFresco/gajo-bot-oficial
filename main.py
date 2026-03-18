import os
import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
# URL pública de la imagen del menú que generamos con los envases reales
MENU_IMAGE_URL = os.environ.get('MENU_IMAGE_URL')
# ID de tu Google Sheet 'vitaminado' y recuperado
SHEET_ID = os.environ.get('SHEET_ID')
WEBHOOK_TOKEN = "GajoBot2026"

# --- 📗 CONEXIÓN CON GOOGLE SHEETS ---
def obtener_datos_vitaminados(id_qr):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Usa el archivo de credenciales de la cuenta recuperada
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        
        # Leemos solo las 4 columnas clave (A, B, C, D)
        datos = hoja.get_all_records()
        print(f"DEBUG - Filas leídas: {len(datos)}")
        
        for item in datos:
            if str(item.get("ID_Unico_QR")).strip() == str(id_qr).strip():
                return item # Devuelve [ID, Vaso, Codigo, Frase]
        return None
    except Exception as e:
        print(f"❌ Error en Google Sheets: {e}")
        return None

# --- 💬 FUNCIÓN PARA ENVIAR WHATSAPP (TEXTO) ---
def enviar_wa_texto(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=payload)

# --- 💬 FUNCIÓN PARA ENVIAR EL MENÚ (IMAGEN) ---
def enviar_menu_media(numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {"link": MENU_IMAGE_URL}
    }
    r = requests.post(url, headers=headers, json=payload)
    print(f"DEBUG - Status Envío Media: {r.status_code}")

# --- 🌐 EL WEBHOOK: Lógica de Descubrimiento ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    if request.method == 'POST':
        data = request.get_json()
        print(f"\n--- 📥 EVENTO RECIBIDO ---")
        try:
            if data.get('entry') and data['entry'][0].get('changes') and \
               data['entry'][0]['changes'][0]['value'].get('messages'):
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    msg_txt = msg_obj['text']['body'].strip()
                    print(f"📝 Mensaje: {msg_txt}")
                    
                    # Llamamos a la base vitaminada
                    info = obtener_datos_vitaminados(msg_txt)
                    
                    if info:
                        v = info.get('Numero_Vaso')
                        c = info.get('Codigo_Secreto')
                        f = info.get('Frase_Gajo')
                        
                        header = "¿Qué Gajo eres hoy? 🍹✨ ¡Descúbrelo aquí!\n\n"
                        
                        if v in [43, 100]:
                            # --- FLUJO DE GANADOR ---
                            respuesta = f"{header}¡Felicidades! 🎉 Eres un **Gajo Premiado (#{v})**.\n\nTu código de regalo es: **{c}** 🎁\nReenvía este código aquí mismo para agendar tu bebida gratis.\n\nFrescura a domicilio ¡pide ahora! 🚚🍓"
                        else:
                            # --- FLUJO NORMAL ---
                            respuesta = f"{header}¡Eres el **Gajo #{v}**!\n\n*{f}*\n\nFrescura a domicilio ¡pide ahora! 🚚🍓"
                        
                        # Primero enviamos el texto de descubrimiento
                        enviar_wa_texto(respuesta, num_cliente)
                        # E inmediatamente enviamos la imagen del menú
                        enviar_menu_media(num_cliente)
                    else:
                        # --- FALLBACK: CÓDIGO DEL FUTURO ---
                        fallback = "¡Huy! 🕵️‍♂️ Ese código no está en nuestra canasta. O es un error de dedo, o vienes del futuro y ese Gajo todavía no se corta. 🍋⏳\n\n¡Escanea un QR real para ganar premios!"
                        enviar_wa_texto(fallback, num_cliente)
                else:
                    print("ℹ️ Evento sin mensaje de texto.")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
