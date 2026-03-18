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

# Memoria temporal para recordar quién está en proceso de registro
# { "numero_telefono": "ID_DEL_QR" }
esperando_nombre = {}

def conectar_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file('creds.json', scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def buscar_id_qr(mensaje):
    try:
        hoja = conectar_sheet()
        datos = hoja.get_all_records()
        msg = mensaje.upper().strip()
        
        for i, item in enumerate(datos, start=2): # start=2 por el encabezado
            raw_id = str(item.get("ID_Unico_QR", ""))
            id_db = raw_id.split("Gajo%20")[-1].upper().strip() if "Gajo%20" in raw_id else raw_id.upper().strip()
            
            if id_db in msg:
                item['fila_index'] = i # Guardamos la fila para saber dónde escribir luego
                return item
        return None
    except Exception as e:
        print(f"❌ Error buscando ID: {e}")
        return None

def registrar_datos_cliente(fila, nombre, telefono):
    try:
        hoja = conectar_sheet()
        # Columna E (5) es Nombre, Columna F (6) es Telefono
        hoja.update_cell(fila, 5, nombre)
        hoja.update_cell(fila, 6, telefono)
        # Opcional: Cambiar estatus a 'Ocupado'
        hoja.update_cell(fila, 4, "Registrado")
        print(f"✅ Datos guardados en fila {fila}")
    except Exception as e:
        print(f"❌ Error guardando datos: {e}")

def enviar_wa(mensaje, numero):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensaje}}
    requests.post(url, headers=headers, json=payload)

def enviar_menu(numero):
    if not MENU_IMAGE_URL: return
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero, "type": "image", "image": {"link": MENU_IMAGE_URL}}
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
                texto = msg_obj['text']['body'].strip()

                # CASO A: El cliente está respondiendo su nombre
                if num_cliente in esperando_nombre:
                    fila_a_editar = esperando_nombre[num_cliente]
                    registrar_datos_cliente(fila_a_editar, texto, num_cliente)
                    
                    respuesta = f"¡Mucho gusto, {texto}! ✨ Ya registré tu Gajo. Aquí tienes nuestro menú de autor. ¿Qué se te antoja hoy? 🍹"
                    enviar_wa(respuesta, num_cliente)
                    enviar_menu(num_cliente)
                    
                    del esperando_nombre[num_cliente] # Limpiamos la memoria

                # CASO B: Es un escaneo de QR (ID)
                else:
                    info = buscar_id_qr(texto)
                    if info:
                        v, m, fila = info.get('Numero_Vaso'), info.get('Mantra_Asignado'), info.get('fila_index')
                        
                        # Si ya tiene nombre, no preguntamos de nuevo
                        if info.get('Nombre_Cliente'):
                            saludo = f"¡Hola de nuevo, {info.get('Nombre_Cliente')}! 🍹\nEres el Gajo #{v}.\n\n*Mantra: {m}*"
                            enviar_wa(saludo, num_cliente)
                            enviar_menu(num_cliente)
                        else:
                            # Iniciamos proceso de registro
                            esperando_nombre[num_cliente] = fila
                            bienvenida = f"¿Qué Gajo eres hoy? 🍹✨\n¡Eres el **Gajo #{v}**!\n\n*Mantra: {m}*\n\nPara enviarte frescura a domicilio, ¿cómo te llamas? ✍️"
                            enviar_wa(bienvenida, num_cliente)
                    else:
                        enviar_wa("¡Huy! 🕵️‍♂️ Ese Gajo no está en la canasta o vienes del futuro. ⏳", num_cliente)

        except Exception as e:
            print(f"❌ Error: {e}")
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
