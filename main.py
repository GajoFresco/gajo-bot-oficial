import os
import requests
import gspread
import datetime
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN ---
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')
WEBHOOK_TOKEN = "GajoBot2026"

esperando_nombre = {}

def conectar_sheet(nombre_hoja="Hoja 1"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(nombre_hoja)
    except: return None

# --- 📝 FUNCIÓN PARA ANOTAR EN EL DIARIO ---
def anotar_log(telefono, nombre, emisor, mensaje):
    try:
        h_logs = conectar_sheet("Chat_Logs")
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        h_logs.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def buscar_id_qr(mensaje):
    try:
        hoja = conectar_sheet("Hoja 1")
        datos = hoja.get_all_records()
        msg = mensaje.upper().strip()
        for i, item in enumerate(datos, start=2):
            raw_id = str(item.get("ID_Unico_QR", ""))
            id_db = raw_id.split("Gajo%20")[-1].upper().strip() if "Gajo%20" in raw_id else raw_id.upper().strip()
            if id_db and id_db in msg:
                item['fila_index'] = i
                return item
        return None
    except: return None

def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
    requests.post(url, headers=headers, json=payload)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN: return request.args.get("hub.challenge")
        return "Error", 403

    if request.method == 'POST':
        data = request.get_json()
        try:
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                msg_val = data['entry'][0]['changes'][0]['value']['messages'][0]
                num = msg_val['from']
                texto = msg_val.get('text', {}).get('body', "").strip()
                ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # 1. ¿ES CÓDIGO QR?
                info = buscar_id_qr(texto)
                if info:
                    f = info['fila_index']
                    h_qr = conectar_sheet("Hoja 1")
                    h_qr.update_cell(f, 9, texto)
                    h_qr.update_cell(f, 10, ahora)
                    nombre_actual = info.get('Nombre_Cliente', 'Sin Registro')
                    anotar_log(num, nombre_actual, "Cliente", f"Escaneó QR: {texto}")
                    
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{info['Numero_Vaso']}.", num)
                    else:
                        esperando_nombre[num] = f
                        enviar_wa(f"¡Gajo #{info['Numero_Vaso']}! 🍹 ¿Cómo te llamas para registrar tu pedido? ✍️", num)
                    return "OK", 200

                # 2. ¿ES NOMBRE?
                if num in esperando_nombre:
                    f = esperando_nombre[num]
                    h_qr = conectar_sheet("Hoja 1")
                    h_qr.update_cell(f, 5, texto)
                    h_qr.update_cell(f, 6, num)
                    anotar_log(num, texto, "Cliente", f"Se registró como: {texto}")
                    enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. En un momento te atenderán personalmente. 🍹", num)
                    del esperando_nombre[num]
                    return "OK", 200

                # 3. YA ESTÁ EN LA LISTA (PLATICA NORMAL)
                anotar_log(num, "Cliente", "Cliente", texto)
                # Saludo por defecto si es la primera vez que escribe sin QR
                if texto.upper() == "HOLA":
                     enviar_wa("¡Hola! 🍹 Bienvenido a Gajo Fresco. En un momento te atenderán personalmente. ✨", num)

        except: pass
        return "OK", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
