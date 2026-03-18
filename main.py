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

# Diccionario temporal para el flujo de registro
esperando_nombre = {}

# --- 📗 FUNCIONES DE BASE DE DATOS ---
def conectar_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Error conectando a Sheets: {e}")
        return None

def buscar_id_qr(mensaje):
    try:
        hoja = conectar_sheet()
        datos = hoja.get_all_records()
        msg = mensaje.upper().strip()
        for i, item in enumerate(datos, start=2):
            raw_id = str(item.get("ID_Unico_QR", ""))
            # Extraer el ID después de "Gajo%20" si existe
            id_db = raw_id.split("Gajo%20")[-1].upper().strip() if "Gajo%20" in raw_id else raw_id.upper().strip()
            
            if id_db and id_db in msg:
                item['fila_index'] = i
                return item
        return None
    except Exception as e:
        print(f"❌ Error buscando ID: {e}")
        return None

def usuario_ya_registrado(telefono):
    try:
        hoja = conectar_sheet()
        datos = hoja.get_all_records()
        for item in datos:
            if str(item.get("Telefono_Cliente")) == str(telefono) and item.get("Nombre_Cliente"):
                return True
        return False
    except:
        return False

def registrar_datos_cliente(fila, nombre, telefono):
    try:
        hoja = conectar_sheet()
        hoja.update_cell(fila, 5, nombre) # Columna E
        hoja.update_cell(fila, 6, telefono) # Columna F
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")

# --- 💬 FUNCIÓN: ENVIAR WHATSAPP ---
def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp", 
        "to": numero, 
        "type": "text", 
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=payload)

# --- 🚀 WEBHOOK PRINCIPAL ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error de verificación", 403

    if request.method == 'POST':
        data = request.get_json()

        # --- 🔥 LÍNEA MAESTRA PARA CAZAR EL CÓDIGO DE FACEBOOK ---
        # Esto imprimirá TODO lo que llegue a Render. Busca aquí tu código.
        print(f"🚨 ALERTA DE DATOS ENTRANTES: {data}")
        # -------------------------------------------------------

        try:
            # Verificamos si es un mensaje de WhatsApp
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                # Si el mensaje no tiene texto (es imagen o botón), evitamos que truene
                texto = msg_obj.get('text', {}).get('body', "").strip()
                texto_upper = texto.upper()

                # 1. ¿Estamos esperando un nombre?
                if num_cliente in esperando_nombre:
                    fila = esperando_nombre[num_cliente]
                    registrar_datos_cliente(fila, texto, num_cliente)
                    enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. En un momento Luis te atenderá personalmente. 🍹", num_cliente)
                    del esperando_nombre[num_cliente]
                    return "OK", 200

                # 2. ¿Es un ID de QR válido (ej: G-001-X8P)?
                info = buscar_id_qr(texto)
                if info:
                    v = info.get('Numero_Vaso')
                    m = info.get('Mantra_Asignado')
                    fila = info.get('fila_index')
                    
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{v}.\n\n*Mantra: {m}*", num_cliente)
                    else:
                        esperando_nombre[num_cliente] = fila
                        enviar_wa(f"¡Eres el **Gajo #{v}**! 🍹\n\n*{m}*\n\n¿Cómo te llamas para registrar tu pedido? ✍️", num_cliente)
                    return "OK", 200

                # 3. ¿Parece un código G- pero no es válido?
                if texto_upper.startswith("G-"):
                    enviar_wa("¡Huy! 🕵️‍♂️ Ese código no está en nuestra canasta. O es un error de dedo o vienes del futuro. ⏳", num_cliente)
                    return "OK", 200

                # 4. SILENCIO TÁCTICO: Si ya está registrado, el bot se calla para que Luis hable
                if usuario_ya_registrado(num_cliente):
                    print(f"🤫 Usuario {num_cliente} ya registrado. Bot en silencio.")
                    return "OK", 200

        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
