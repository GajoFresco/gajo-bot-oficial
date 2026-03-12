import os
import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials

# 1. CREAMOS LA APP (Esto debe ir arriba de todo)
app = Flask(__name__)

# --- 📋 CONFIGURACIÓN ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')
WEBHOOK_TOKEN = "GajoBot2026"

# --- 📗 CONEXIÓN CON GOOGLE SHEETS ---
def obtener_datos_vaso(id_qr):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        datos = hoja.get_all_records()
        return next((item for item in datos if str(item["ID_Unico_QR"]).strip() == str(id_qr).strip()), None)
    except Exception as e:
        print(f"Error Sheets: {e}")
        return None

# --- 💬 FUNCIÓN ENVIAR WHATSAPP ---
def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, headers=headers, json=data)
    print(f"Respuesta de Meta: {r.status_code} - {r.text}")

# --- 🌐 EL WEBHOOK REFORZADO ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error de token", 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            if data.get('entry') and data['entry'][0].get('changes') and data['entry'][0]['changes'][0]['value'].get('messages'):
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                if 'text' in msg_obj:
                    mensaje_cliente = msg_obj['text']['body'].strip()
                    info = obtener_datos_vaso(mensaje_cliente)

                    if info:
                        vaso = info['Numero_Vaso']
                        clave = info['Codigo_Secreto']
                        if vaso in [43, 100]:
                            respuesta = f"¡Felicidades! 🎉 Eres el cliente #{vaso}.\n¡GANASTE UN TOPPING EXTRA! 🍓\nClave: {clave}\n\n¿Qué coctel te preparamos?"
                        else:
                            respuesta = f"¡Hola! 🍹 Estás disfrutando el Gajo #{vaso}.\nGracias por preferirnos.\n\nRecuerda que pidiendo por aquí el precio es especial. ✨"
                    else:
                        respuesta = "¡Hola! 🍹 Bienvenido a Gajo!. Escanea el QR de tu vaso para ver si tienes premio o para ordenar de nuevo."
                    
                    enviar_wa(respuesta, num_cliente)
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return "EVENT_RECEIVED", 200

    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
