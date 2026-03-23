import streamlit as st
import pandas as pd
import requests
import time
import gspread
import datetime
from google.oauth2.service_account import Credentials

# --- ⚙️ CONFIGURACIÓN ---
TOKEN = st.secrets["WHATSAPP_TOKEN"]
PHONE_ID = st.secrets["PHONE_ID"]
SHEET_ID = st.secrets["SHEET_ID"]
# Cambia estos links por tus URLs reales
MENU_IMG_URL = "https://tu-link-de-imagen.jpg" 
MENU_PDF_URL = "https://tu-link-de-menu.pdf"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹", layout="wide")

# --- 📝 FUNCIONES DE APOYO ---
def anotar_respuesta_en_log(telefono, nombre, mensaje):
    h = client.open_by_key(SHEET_ID).worksheet("Chat_Logs")
    ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    h.append_row([ahora, str(telefono), nombre, "Luis (Gajo)", mensaje])

def enviar_mensaje_wa(telefono, payload):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    return requests.post(url, headers=headers, json=payload)

# --- 📊 CARGA DE DATOS ---
st.title("🍹 Gajo! Central de Mensajes")

try:
    h_logs = client.open_by_key(SHEET_ID).worksheet("Chat_Logs")
    df_logs = pd.DataFrame(h_logs.get_all_records())
except:
    df_logs = pd.DataFrame()

if not df_logs.empty:
    with st.sidebar:
        st.header("💬 Conversaciones")
        # Mostramos los teléfonos que han escrito, el más reciente arriba
        lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
        tel_sel = st.selectbox("Selecciona un chat:", lista_tels)
        
        st.divider()
        st.subheader("📁 Enviar Multimedia")
        if st.button("🖼️ Enviar Menú (Imagen)"):
            payload = {
                "messaging_product": "whatsapp", "to": str(tel_sel), "type": "image",
                "image": {"link": MENU_IMG_URL, "caption": "¡Aquí tienes nuestro menú! 🍹"}
            }
            if enviar_mensaje_wa(tel_sel, payload).status_code == 200:
                anotar_respuesta_en_log(tel_sel, "Cliente", "Envió Menú (Imagen)")
                st.success("Imagen enviada")
        
        if st.button("📄 Enviar Menú (PDF)"):
            payload = {
                "messaging_product": "whatsapp", "to": str(tel_sel), "type": "document",
                "document": {"link": MENU_PDF_URL, "filename": "Menu_Gajo_Fresco.pdf", "caption": "Menú en formato PDF 📄"}
            }
            if enviar_mensaje_wa(tel_sel, payload).status_code == 200:
                anotar_respuesta_en_log(tel_sel, "Cliente", "Envió Menú (PDF)")
                st.success("PDF enviado")

        st.divider()
        if st.button("🔄 Refrescar ahora"): st.rerun()

    # --- 📱 VISUALIZACIÓN DEL CHAT ---
    chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha')
    ultimo_nombre = chat_actual[chat_actual['Nombre'] != 'Cliente']['Nombre'].iloc[-1] if not chat_actual[chat_actual['Nombre'] != 'Cliente'].empty else "Cliente"

    st.subheader(f"Chat con: {ultimo_nombre} ({tel_sel})")

    chat_container = st.container(height=500, border=True)
    with chat_container:
        for _, fila in chat_actual.iterrows():
            role = "assistant" if "Gajo" in str(fila['Emisor']) else "user"
            avatar = "🍹" if role == "assistant" else "👤"
            with st.chat_message(role, avatar=avatar):
                st.write(fila['Mensaje'])
                st.caption(f"{fila['Fecha']} - {fila['Emisor']}")

    # --- ✉️ CAJA DE RESPUESTA ---
    if respuesta := st.chat_input("Escribe tu respuesta aquí..."):
        payload = {"messaging_product": "whatsapp", "to": str(tel_sel), "type": "text", "text": {"body": respuesta}}
        res = enviar_mensaje_wa(tel_sel, payload)
        if res.status_code == 200:
            anotar_respuesta_en_log(tel_sel, ultimo_nombre, respuesta)
            st.rerun()
        else:
            st.error(f"Error: {res.text}")

else:
    st.info("Esperando que caiga el primer Gajo... 🍋")

# Auto-refresh cada 15 segundos
time.sleep(15)
st.rerun()
