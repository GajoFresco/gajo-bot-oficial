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

# Diccionario temporal para el flujo de registro
# Puede guardar: un número de fila (para QR) o la palabra "PROSPECTO"
esperando_nombre = {}

# --- 📗 FUNCIONES DE BASE DE DATOS ---

def conectar_sheet(nombre_hoja="Hoja 1"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(nombre_hoja)
    except Exception as e:
        print(f"❌ Error conectando a hoja {nombre_hoja}: {e}")
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
            if str(item.get("Telefono_Cliente")) == str(telefono) or str(item.get("Telefono")) == str(telefono):
                return i
        return None
    except:
        return None

def registrar_prospecto_nuevo(nombre, telefono):
    try:
        hoja = conectar_sheet("Prospectos")
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        # Estructura: ID_Manual, Nombre, Telefono, Mensaje, Hora
        hoja.append_row(["MANUAL", nombre, telefono, "Registro inicial sin QR", ahora])
        print(f"✅ Nuevo prospecto guardado: {nombre}")
    except Exception as e:
        print(f"❌ Error en registrar_prospecto_nuevo: {e}")

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
        print(f"🚨 ALERTA DE DATOS ENTRANTES: {data}")

        try:
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                texto = msg_obj.get('text', {}).get('body', "").strip()
                texto_upper = texto.upper()
                ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                # 1. ¿ESTAMOS ESPERANDO UN NOMBRE?
                if num_cliente in esperando_nombre:
                    valor = esperando_nombre[num_cliente]
                    
                    if valor == "PROSPECTO":
                        # Caso: Almas perdidas (sin QR)
                        registrar_prospecto_nuevo(texto, num_cliente)
                        enviar_wa(f"¡Listo, {texto}! Ya te tengo en mi lista. 📝 En un momento Luis se pondrá en contacto contigo. 🍹", num_cliente)
                    else:
                        # Caso: Cliente con QR esperando registro
                        hoja_qr = conectar_sheet("Hoja 1")
                        hoja_qr.update_cell(valor, 5, texto)       # Col E: Nombre
                        hoja_qr.update_cell(valor, 6, num_cliente) # Col F: Tel
                        hoja_qr.update_cell(valor, 9, f"Nombre registrado: {texto}")
                        hoja_qr.update_cell(valor, 10, ahora)
                        enviar_wa(f"¡Mucho gusto, {texto}! ✨ Ya te registré. En un momento Luis te atenderá personalmente. 🍹", num_cliente)
                    
                    del esperando_nombre[num_cliente]
                    return "OK", 200

                # 2. ¿ES UN CÓDIGO QR VÁLIDO?
                info = buscar_id_qr(texto)
                if info:
                    fila = info.get('fila_index')
                    hoja_qr = conectar_sheet("Hoja 1")
                    hoja_qr.update_cell(fila, 9, f"Escaneó QR: {texto}")
                    hoja_qr.update_cell(fila, 10, ahora)
                    
                    if info.get('Nombre_Cliente'):
                        enviar_wa(f"¡Hola de nuevo! 🍹 Eres el Gajo #{info.get('Numero_Vaso')}.\n\n*Mantra: {info.get('Mantra_Asignado')}*", num_cliente)
                    else:
                        esperando_nombre[num_cliente] = fila
                        enviar_wa(f"¡Eres el **Gajo #{info.get('Numero_Vaso')}**! 🍹\n\n¿Cómo te llamas para registrar tu pedido? ✍️", num_cliente)
                    return "OK", 200

                # 3. SILENCIO TÁCTICO (¿Ya está en Hoja 1 o en Prospectos?)
                fila_qr = buscar_fila_por_telefono(num_cliente, "Hoja 1")
                fila_prospecto = buscar_fila_por_telefono(num_cliente, "Prospectos")
                
                if fila_qr:
                    hoja_qr = conectar_sheet("Hoja 1")
                    hoja_qr.update_cell(fila_qr, 9, texto)
                    hoja_qr.update_cell(fila_qr, 10, ahora)
                    print(f"🤫 Cliente QR {num_cliente} anotado. Bot en silencio.")
                    return "OK", 200
                
                if fila_prospecto:
                    hoja_pros = conectar_sheet("Prospectos")
                    hoja_pros.update_cell(fila_prospecto, 4, texto) # Col D: Mensaje
                    hoja_pros.update_cell(fila_prospecto, 5, ahora) # Col E: Hora
                    print(f"🤫 Prospecto {num_cliente} anotado. Bot en silencio.")
                    return "OK", 200

                # 4. ¿CÓDIGO G- ERRÓNEO?
                if texto_upper.startswith("G-"):
                    enviar_wa("¡Huy! 🕵️‍♂️ Ese código no está en nuestra canasta. Revisa bien tu vaso. 🍹", num_cliente)
                    return "OK", 200

                # 5. BIENVENIDA A DESCONOCIDOS (Iniciar registro manual)
                esperando_nombre[num_cliente] = "PROSPECTO"
                bienvenida = (
                    "¡Hola! 🍹 Bienvenido a **Gajo Fresco**.\n\n"
                    "No encontré un pedido activo con tu número. ¿Cómo te llamas? "
                    "Me gustaría registrarte para que Luis te atienda personalmente. ✨"
                )
                enviar_wa(bienvenida, num_cliente)
                return "OK", 200

        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
            
        return "EVENT_RECEIVED", 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
