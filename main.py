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
mensajes_procesados = set() # Para evitar el bucle de mensajes

def conectar_sheet(nombre_hoja="Hoja 1"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(nombre_hoja)
    except Exception as e:
        print(f"❌ Error conectando a {nombre_hoja}: {e}")
        return None

def anotar_log(telefono, nombre, emisor, mensaje):
    try:
        h_logs = conectar_sheet("Chat_Logs")
        if h_logs:
            ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
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
            col = "Telefono_Cliente" if nombre_hoja == "Hoja 1" else "Telefono"
            if str(item.get(col)) == str(telefono): return i
        return None
    except: return None

def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
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
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                msg_id = msg_obj['id'] # ID único del mensaje
                
                # --- FILTRO ANTIDUPLICADOS ---
                if msg_id in mensajes_procesados:
                    return "OK", 200
                mensajes_procesados.add(msg_id)
                if len(mensajes_procesados) > 100: mensajes_procesados.pop()

                num = msg_obj['from']
                texto = msg_obj.get('text', {}).get('body', "").strip()
                ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")

                # Identificar usuario para el log
                fila_qr = buscar_fila_por_telefono(num, "Hoja 1")
                fila_prospecto = buscar_fila_por_telefono(num, "Prospectos")
                nombre_log = "Desconocido"
                if fila_qr: nombre_log = "Cliente QR"
                if fila_prospecto: nombre_log = "Prospecto"

                # 1. ¿ESPERANDO NOMBRE?
                if num in esperando_nombre:
                    valor = esperando_nombre[num]
                    if valor == "PROSPECTO":
                        conectar_sheet("Prospectos").append_row(["MANUAL", texto, num, "Registro inicial", ahora])
                        anotar_log(num, texto, "Cliente", f"Se registró como: {texto}")
                        enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. En un momento te atenderán personalmente. 🍹", num)
                    else:
                        h_qr = conectar_sheet("Hoja 1")
                        h_qr.update_cell(valor, 5, texto)
                        h_qr.update_cell(valor, 6, num)
                        anotar_log(num, texto, "Cliente", f"Registro QR: {texto}")
                        enviar_wa(f"¡Listo, {texto}! ✨ Ya vinculé tu Gajo. En un momento te atenderán personalmente. 🍹", num)
                    del esperando_nombre[num]
                    return "OK", 200

                # 2. ¿QR?
                info = buscar_id_qr(texto)
                if info:
                    f = info['fila_index']
                    conectar_sheet("Hoja 1").update_cell(f, 9, texto)
                    anotar_log(num, info.get('Nombre_Cliente', 'Cliente QR'), "Cliente", f"Escaneó QR: {texto}")
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{info['Numero_Vaso']}.", num)
                    else:
                        esperando_nombre[num] = f
                        enviar_wa(f"¡Gajo #{info['Numero_Vaso']}! 🍹 ¿Cómo te llamas para registrar tu pedido? ✍️", num)
                    return "OK", 200

                # 3. CONOCIDO
                if fila_qr or fila_prospecto:
                    anotar_log(num, nombre_log, "Cliente", texto)
                    return "OK", 200
                
                # 4. NUEVO
                anotar_log(num, "Nuevo", "Cliente", texto)
                esperando_nombre[num] = "PROSPECTO"
                enviar_wa("¡Hola! 🍹 Bienvenido a **Gajo Fresco**. No encontré un pedido activo. ¿Cómo te llamas para atenderte personalmente? ✨", num)

        except: pass
        return "OK", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
