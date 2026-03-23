import os
import requests
import gspread
import datetime
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- 📋 CONFIGURACIÓN DE RENDER ---
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
    except Exception as e:
        print(f"❌ Error conectando a {nombre_hoja}: {e}")
        return None

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
    except Exception as e:
        print(f"❌ Error buscando ID: {e}")
        return None

def buscar_fila_por_telefono(telefono, nombre_hoja="Hoja 1"):
    try:
        hoja = conectar_sheet(nombre_hoja)
        datos = hoja.get_all_records()
        for i, item in enumerate(datos, start=2):
            tel_db = str(item.get("Telefono_Cliente") or item.get("Telefono", ""))
            if tel_db == str(telefono):
                return i
        return None
    except:
        return None

def registrar_prospecto_nuevo(nombre, telefono):
    try:
        hoja = conectar_sheet("Prospectos")
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        hoja.append_row(["MANUAL", nombre, telefono, "Registro inicial sin QR", ahora])
    except Exception as e:
        print(f"❌ Error prospecto: {e}")

def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
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
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                texto = msg_obj.get('text', {}).get('body', "").strip()
                texto_upper = texto.upper()
                ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # 1. ESPERANDO NOMBRE
                if num_cliente in esperando_nombre:
                    valor = esperando_nombre[num_cliente]
                    if valor == "PROSPECTO":
                        registrar_prospecto_nuevo(texto, num_cliente)
                        enviar_wa(f"¡Listo, {texto}! Ya te registré. 📝 En un momento Luis te atenderá. 🍹", num_cliente)
                    else:
                        hoja_qr = conectar_sheet("Hoja 1")
                        hoja_qr.update_cell(valor, 5, texto)
                        hoja_qr.update_cell(valor, 6, num_cliente)
                        hoja_qr.update_cell(valor, 9, f"Registro: {texto}")
                        hoja_qr.update_cell(valor, 10, ahora)
                        enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. 🍹", num_cliente)
                    del esperando_nombre[num_cliente]
                    return "OK", 200

                # 2. CÓDIGO QR
                info = buscar_id_qr(texto)
                if info:
                    fila = info['fila_index']
                    hoja_qr = conectar_sheet("Hoja 1")
                    hoja_qr.update_cell(fila, 9, f"QR: {texto}")
                    hoja_qr.update_cell(fila, 10, ahora)
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{info.get('Numero_Vaso')}.", num_cliente)
                    else:
                        esperando_nombre[num_cliente] = fila
                        enviar_wa(f"¡Eres el **Gajo #{info.get('Numero_Vaso')}**! 🍹\n\n¿Cómo te llamas? ✍️", num_cliente)
                    return "OK", 200

                # 3. SILENCIO TÁCTICO
                fila_qr = buscar_fila_por_telefono(num_cliente, "Hoja 1")
                fila_prospecto = buscar_fila_por_telefono(num_cliente, "Prospectos")
                if fila_qr:
                    conectar_sheet("Hoja 1").update_cell(fila_qr, 9, texto)
                    conectar_sheet("Hoja 1").update_cell(fila_qr, 10, ahora)
                    return "OK", 200
                if fila_prospecto:
                    conectar_sheet("Prospectos").update_cell(fila_prospecto, 4, texto)
                    conectar_sheet("Prospectos").update_cell(fila_prospecto, 5, ahora)
                    return "OK", 200

                # 4. BIENVENIDA
                esperando_nombre[num_cliente] = "PROSPECTO"
                enviar_wa("¡Hola! 🍹 No encontré un pedido activo. ¿Cómo te llamas para que Luis te atienda? ✨", num_cliente)
                return "OK", 200

        except Exception as e:
            print(f"❌ Error: {e}")
        return "OK", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
