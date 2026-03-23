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

def anotar_log(telefono, nombre, emisor, mensaje):
    try:
        h_logs = conectar_sheet("Chat_Logs")
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        h_logs.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: print("❌ Error anotando log")

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

def buscar_fila_por_telefono(telefono, nombre_hoja="Hoja 1"):
    try:
        hoja = conectar_sheet(nombre_hoja)
        datos = hoja.get_all_records()
        for i, item in enumerate(datos, start=2):
            col_tel = "Telefono_Cliente" if nombre_hoja == "Hoja 1" else "Telefono"
            if str(item.get(col_tel)) == str(telefono): return i
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

                # --- SIEMPRE ANOTAR EN LOG (Para ver el "Hola" en la App) ---
                # Buscamos si ya tiene nombre en algún lado para el log
                fila_qr = buscar_fila_por_telefono(num, "Hoja 1")
                fila_prospecto = buscar_fila_por_telefono(num, "Prospectos")
                nombre_para_log = "Cliente Nuevo"
                if fila_qr: nombre_para_log = "Cliente QR"
                if fila_prospecto: nombre_para_log = "Prospecto"
                
                anotar_log(num, nombre_para_log, "Cliente", texto)

                # 1. ¿ESPERANDO NOMBRE PARA REGISTRO?
                if num in esperando_nombre:
                    valor = esperando_nombre[num]
                    if valor == "PROSPECTO":
                        conectar_sheet("Prospectos").append_row(["MANUAL", texto, num, "Registro inicial", ahora])
                        enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. En un momento te atenderán personalmente. 🍹", num)
                    else:
                        h_qr = conectar_sheet("Hoja 1")
                        h_qr.update_cell(valor, 5, texto)
                        h_qr.update_cell(valor, 6, num)
                        enviar_wa(f"¡Listo, {texto}! ✨ Pedido vinculado. En un momento te atenderán personalmente. 🍹", num)
                    del esperando_nombre[num]
                    return "OK", 200

                # 2. ¿ES UN CÓDIGO QR?
                info = buscar_id_qr(texto)
                if info:
                    f = info['fila_index']
                    conectar_sheet("Hoja 1").update_cell(f, 9, texto)
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{info['Numero_Vaso']}.", num)
                    else:
                        esperando_nombre[num] = f
                        enviar_wa(f"¡Gajo #{info['Numero_Vaso']}! 🍹 ¿Cómo te llamas para registrar tu pedido? ✍️", num)
                    return "OK", 200

                # 3. SI YA ES CONOCIDO, EL BOT SE CALLA (Luis responde desde App)
                if fila_qr or fila_prospecto:
                    print(f"🤫 Cliente {num} conocido. Bot en silencio.")
                    return "OK", 200
                
                # 4. SI LLEGÓ AQUÍ, ES DESCONOCIDO TOTAL
                esperando_nombre[num] = "PROSPECTO"
                bienvenida = (
                    "¡Hola! 🍹 Bienvenido a **Gajo Fresco**.\n\n"
                    "No encontré un pedido activo con tu número. ¿Cómo te llamas para que te atiendan personalmente? ✨"
                )
                enviar_wa(bienvenida, num)

        except Exception as e: print(f"❌ Error: {e}")
        return "OK", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
