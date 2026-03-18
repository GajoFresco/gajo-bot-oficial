import streamlit as st
import pandas as pd
import requests
import os
import time
from gspread_pandas import Spread, Client

# --- ⚙️ CONFIGURACIÓN ---
# Usamos las mismas variables que ya tienes en Render
TOKEN = os.environ.get('WHATSAPP_TOKEN')
PHONE_ID = os.environ.get('PHONE_ID')
SHEET_ID = os.environ.get('SHEET_ID')

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹")

st.title("🍹 Gajo! Central de Mensajes")
st.write("Aquí controlas todo sin entrar a Facebook.")

# --- 🔄 AUTO-REFRESH (Cada 10 segundos para "tiempo real") ---
# Nota: Esto hará que la página se refresque solita para ver mensajes nuevos
# count = st.empty() # Espacio para contador si quisieras

# --- 📊 LECTURA DE MENSAJES ---
def cargar_datos():
    # Usamos tu Sheet para ver qué han escrito los clientes
    # Aquí deberías conectar con gspread como ya sabes
    pass 

# SIMULACIÓN DE INTERFAZ (Para que veas cómo quedaría)
with st.sidebar:
    st.header("Clientes Recientes")
    # Aquí saldría la lista de números que te han escrito
    cliente_sel = st.selectbox("Selecciona un chat", ["5215512345678 (Juan)", "5215598765432 (Maria)"])

st.subheader(f"Chat con: {cliente_sel}")

# Aquí mostraríamos el historial de la Columna G del Excel
st.text_area("Historial", value="Cliente: Hola, quiero un G-001\nBot: ¡Hola! ¿Cómo te llamas?", height=200, disabled=True)

# --- ✉️ CAJA DE RESPUESTA ---
respuesta = st.text_input("Escribe tu respuesta para el cliente:")

if st.button("🚀 Enviar a WhatsApp"):
    if respuesta:
        url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": cliente_sel.split(" ")[0], # Sacamos solo el número
            "type": "text",
            "text": {"body": respuesta}
        }
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            st.success("¡Mensaje enviado con éxito!")
            # OPCIONAL: Guardar tu propia respuesta en el Excel para tener el historial
        else:
            st.error(f"Error: {res.text}")
