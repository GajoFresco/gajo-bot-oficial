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

# --- 📝 FUNCIONES DE ENVÍO Y LOG ---
def anotar_log(telefono, nombre, emisor, mensaje):
    try:
        h = client.open_by_key(SHEET_ID).worksheet("Chat_Logs")
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def enviar_texto_wa(telefono, texto):
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto}}
    return requests.post(url, headers=headers, json=payload)

def enviar_archivo_wa(telefono, archivo):
    # 1. Subir el archivo a Meta para obtener un ID
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': (archivo.name, archivo.getvalue(), archivo.type)}
    data = {'messaging_product': 'whatsapp'}
    
    res_media = requests.post(url_media, headers=headers, files=files, data=data)
    
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        # 2. Enviar el mensaje usando el media_id
        url_msg = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        tipo = "image" if "image" in archivo.type else "document"
        payload = {
            "messaging_product": "whatsapp", "to": str(telefono), "type": tipo,
            tipo: {"id": media_id}
        }
        return requests.post(url_msg, headers=headers, json=payload)
    return res_media

# --- 📊 CARGA DE DATOS ---
st.title("🍹 Gajo! Central de Mensajes")

try:
    h_logs = client.open_by_key(SHEET_ID).worksheet("Chat_Logs")
    df_logs = pd.DataFrame(h_logs.get_all_records())
except:
    df_logs = pd.DataFrame()

if not df_logs.empty:
    # --- CREAR AGENDA DE NOMBRES ---
    # Sacamos el último nombre conocido para cada teléfono
    agenda = df_logs[df_logs['Nombre'] != 'Cliente'].drop_duplicates('Telefono', keep='last')
    nombres_map = dict(zip(agenda['Telefono'].astype(str), agenda['Nombre']))

    with st.sidebar:
        st.header("👥 Conversaciones")
        lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
        
        # Formateamos la lista para mostrar "Nombre (Teléfono)"
        opciones_sidebar = []
        for t in lista_tels:
            nombre = nombres_map.get(str(t), "Cliente Nuevo")
            opciones_sidebar.append(f"{nombre} ({t})")
            
        sel_contacto = st.selectbox("Selecciona un chat:", opciones_sidebar)
        tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
        nombre_sel = sel_contacto.split(" (")[0]

        st.divider()
        st.subheader("📁 Enviar Archivo Local")
        archivo_subido = st.file_uploader("Imagen o PDF del menú:", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if archivo_subido and st.button("🚀 Enviar Archivo Seleccionado"):
            with st.spinner("Subiendo y enviando..."):
                res = enviar_archivo_wa(tel_sel, archivo_subido)
                if res.status_code == 200:
                    anotar_log(tel_sel, nombre_sel, "Luis (Gajo)", f"Envió archivo: {archivo_subido.name}")
                    st.success("¡Archivo enviado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Error al subir archivo a Meta.")

        if st.button("🔄 Refrescar Pantalla"): st.rerun()

    # --- 📱 VISUALIZACIÓN DEL CHAT ---
    chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)]
    
    st.subheader(f"Chat con: {nombre_sel}")
    st.caption(f"Número: {tel_sel}")

    chat_container = st.container(height=450, border=True)
    with chat_container:
        for _, fila in chat_actual.iterrows():
            is_luis = "Gajo" in str(fila['Emisor'])
            with st.chat_message("assistant" if is_luis else "user", avatar="🍹" if is_luis else "👤"):
                st.write(fila['Mensaje'])
                st.caption(f"{fila['Fecha']}")

    # --- ✉️ RESPUESTA RÁPIDA ---
    if respuesta := st.chat_input("Escribe tu respuesta aquí..."):
        if enviar_texto_wa(tel_sel, respuesta).status_code == 200:
            anotar_log(tel_sel, nombre_sel, "Luis (Gajo)", respuesta)
            st.rerun()

else:
    st.info("Esperando primer mensaje... 🍋")

time.sleep(20)
st.rerun()
