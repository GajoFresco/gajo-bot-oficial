import os
import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN DE RENDER ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')
MENU_IMAGE_URL = os.environ.get('MENU_IMAGE_URL')
WEBHOOK_TOKEN = "GajoBot2026"

# --- 📗 FUNCIÓN: BUSCAR EN LA BASE VITAMINADA ---
def obtener_datos_vitaminados(mensaje_recibido):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        datos = hoja.get_all_records()
        
        mensaje_recibido = mensaje_recibido.upper() # Pasamos a mayúsculas para evitar fallos
        
        for item in datos:
            # Extraemos el ID del link de la Columna A (ej: G-001-X8P)
            # El link termina en algo como Gajo%20G-001-X8P
            url_qr = str(item.get("ID_Unico_QR", ""))
            if "Gajo%20" in url_qr:
                id_esperado = url_qr.split("Gajo%20")[-1].upper()
            else:
                id_esperado = url_qr.upper()

            # Si el ID está contenido en lo que mandó el cliente
            if id_esperado and id_esperado in mensaje_recibido:
                return item
        return None
    except Exception as e:
        print(f"❌ Error en Sheets: {e}")
        return None

# --- 💬 FUNCIÓN: ENVIAR TEXTO ---
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

# --- 💬 FUNCIÓN: ENVIAR MENÚ ---
def enviar_menu_media(numero):
    if not MENU_IMAGE_URL:
        print("⚠️ No hay URL de imagen configurada.")
        return
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {"link": MENU_IMAGE_URL}
    }
    requests.post(url, headers=headers, json=payload)

# --- 🌐 EL WEBHOOK (LA RUTA PRINCIPAL) ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error de verificación", 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            if data.get('entry') and data['entry'][0].get('changes') and \
               data['entry'][0]['changes'][0]['value'].get('messages'):
                
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    msg_txt = msg_obj['text']['body'].strip()
                    print(f"📩 Mensaje recibido: {msg_txt}")
                    
                    # BUSQUEDA EN EL EXCEL
                    info = obtener_datos_vitaminados(msg_txt)
                    
                    if info:
                        # Extraemos datos según tus columnas exactas
                        v = info.get('Numero_Vaso')
                        c = info.get('Codigo_Secreto')
                        m = info.get('Mantra_Asignado')
                        
                        header = "¿Qué Gajo eres hoy? 🍹✨ ¡Descúbrelo aquí!\n\n"
                        
                        # Si es el vaso premiado (puedes cambiar el 43 por el que quieras)
                        if str(v) in ["43", "100"]:
                            respuesta = f"{header}¡Felicidades! 🎉 Eres un **Gajo Premiado (#{v})**.\n\nTu código de regalo es: **{c}** 🎁\nReenvía este código aquí mismo para agendar tu bebida gratis.\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        else:
                            respuesta = f"{header}¡Eres el **Gajo #{v}**!\n\n*Mantra del día: {m}*\n\nFrescura a domicilio ¡pide ahora! 🍓"
                        
                        enviar_wa_texto(respuesta, num_cliente)
                        enviar_menu_media(num_cliente)
                    else:
                        # FALLBACK SI EL CÓDIGO NO EXISTE
                        fallback = "¡Huy! 🕵️‍♂️ Ese código no está en nuestra canasta. O es un error de dedo, o vienes del futuro y ese Gajo todavía no se corta. 🍋⏳\n\n¡Escanea un QR real para ganar premios!"
                        enviar_wa_texto(fallback, num_cliente)
                
        except Exception as e:
            print(f"❌ ERROR GENERAL: {e}")
        
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
