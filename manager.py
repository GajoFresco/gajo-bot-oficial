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

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹", layout="wide")

# --- 📝 FUNCIONES DE ENVÍO Y REGISTRO ---
def anotar_log(telefono, nombre, emisor, mensaje):
    try:
        h = client.open_by_key(SHEET_ID).worksheet("Chat_Logs")
        # --- AJUSTE DE HORA MÉXICO (-6 HORAS) ---
        ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except Exception as e:
        st.error(f"Error al anotar log: {e}")

def enviar_archivo_wa(telefono, archivo):
    # Subir a Meta
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': (archivo.name, archivo.getvalue(), archivo.type)}
    data = {'messaging_product': 'whatsapp'}
    res_media = requests.post(url_media, headers=headers, files=files, data=data)
    
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        url_msg = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        tipo = "image" if "image" in archivo.type else "document"
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": tipo, tipo: {"id": media_id}}
        return requests.post(url_msg, headers=headers, json=payload)
    return res_media

# --- 📊 CARGA DE DATOS ---
st.title("🍹 Gajo! Central de Mensajes")

# Crear Agenda (Nombres)
@st.cache_data(ttl=60)
def obtener_agenda():
    try:
        h1 = client.open_by_key(SHEET_ID).worksheet("Hoja 1").get_all_records()
        h2 = client.open_by_key(SHEET_ID).worksheet("Prospectos").get_all_records()
        agenda = {}
        for r in h1: 
            if r.get('Telefono_Cliente'): agenda[str(r['Telefono_Cliente'])] = r.get('Nombre_Cliente', 'Sin Nombre')
        for r in h2:
            if r.get('Telefono'): agenda[str(r['Telefono'])] = r.get('Nombre', 'Sin Nombre')
        return agenda
    except: return {}

agenda_nombres = obtener_agenda()

try:
    df_logs = pd.DataFrame(client.open_by_key(SHEET_ID).worksheet("Chat_Logs").get_all_records())
except:
    df_logs = pd.DataFrame()

if not df_logs.empty:
    with st.sidebar:
        st.header("👥 Conversaciones")
        # Obtenemos los teléfonos únicos, el más reciente arriba
        lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
        
        # Lista con formato "Nombre (Teléfono)"
        opciones = [f"{agenda_nombres.get(str(t), 'Desconocido')} ({t})" for t in lista_tels]
        sel_contacto = st.selectbox("Selecciona un chat:", opciones)
        
        # Extraemos teléfono y nombre de la selección
        tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
        nombre_sel = sel_contacto.split(" (")[0]

        st.divider()
        st.subheader("📁 Enviar Menú/Foto")
        archivo = st.file_uploader("Sube Imagen o PDF:", type=['png', 'jpg', 'pdf'])
        if archivo and st.button("🚀 Enviar Archivo"):
            with st.spinner("Enviando multimedia..."):
                res = enviar_archivo_wa(tel_sel, archivo)
                if res.status_code == 200:
                    anotar_log(tel_sel, nombre_sel, "Luis (Gajo)", f"Envió archivo: {archivo.name}")
                    st.success("¡Enviado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("No se pudo enviar el archivo.")

    # --- 📱 VISUALIZACIÓN DEL CHAT ---
    chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)]
    st.subheader(f"Conversación con: {nombre_sel}")
    st.caption(f"Número: {tel_sel}")
    
    container = st.container(height=500, border=True)
    with container:
        for _, fila in chat_actual.iterrows():
            # Luis es 'assistant', el cliente es 'user'
            is_luis = "Gajo" in str(fila['Emisor'])
            role = "assistant" if is_luis else "user"
            
            with st.chat_message(role, avatar="🍹" if is_luis else "👤"):
                st.write(fila['Mensaje'])
                st.caption(f"{fila['Fecha']} - {fila['Emisor']}")

    # --- ✉️ ENTRADA DE TEXTO ---
    if resp := st.chat_input("Escribe tu respuesta aquí..."):
        url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {TOKEN}"}
        payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
        
        if requests.post(url, headers=headers, json=payload).status_code == 200:
            anotar_log(tel_sel, nombre_sel, "Luis (Gajo)", resp)
            st.rerun()
        else:
            st.error("Error al enviar el mensaje de texto.")
else:
    st.info("No hay mensajes registrados en Chat_Logs todavía. 🍋")

# Auto-refresco para ver mensajes nuevos del cliente
time.sleep(20)
st.rerun()
