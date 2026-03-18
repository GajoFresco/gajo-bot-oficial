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

def obtener_datos_vitaminados(mensaje_recibido):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file('creds.json', scopes=scope)
        client = gspread.authorize(creds)
        hoja = client.open_by_key(SHEET_ID).sheet1
        datos = hoja.get_all_records()
        
        # Limpiamos el mensaje para buscar solo el ID (ej: G-001-X8P)
        for item in datos:
            # Sacamos el ID de la columna A (que en tu foto es un link largo)
            # Vamos a buscar si el ID está contenido en el mensaje del cliente
            id_esperado = str(item.get("ID_Unico_QR")).split("Gajo%20")[-1] # Extrae el ID del link
            
            if id_esperado in mensaje_recibido:
                return item
        return None
    except Exception as e:
        print(f"❌ Error en Sheets: {e}")
        return None

# --- LÓGICA DE RESPUESTA EN EL WEBHOOK ---
# (Dentro del bloque 'if info:')
v = info.get('Numero_Vaso')
c = info.get('Codigo_Secreto')
m = info.get('Mantra_Asignado') # Usamos el nombre exacto de tu columna H

header = "¿Qué Gajo eres hoy? 🍹✨ ¡Descúbrelo aquí!\n\n"

# Si el código secreto existe y es el premiado (puedes ajustarlo por ID o por Vaso)
if v in [43, 100]: 
    respuesta = f"{header}¡Felicidades! 🎉 Eres un **Gajo Premiado (#{v})**.\n\nTu código de regalo es: **{c}** 🎁\nReenvía este código para tu bebida gratis.\n\nFrescura a domicilio ¡pide ahora! 🍓"
else:
    respuesta = f"{header}¡Eres el **Gajo #{v}**!\n\n*Mantra del día: {m}*\n\nFrescura a domicilio ¡pide ahora! 🍓"
