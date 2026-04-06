import streamlit as st
import pandas as pd
import requests
import time
import gspread
import datetime
from google.oauth2.service_account import Credentials

# ==========================================
# --- 🖼️ CONFIGURACIÓN DE IMÁGENES Y ESTILO ---
# ==========================================
URL_FAVICON_ISO = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Isotipo%20para%20Blanco.png"
URL_LOGO_HORIZONTAL = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Logotipo%20para%20Blanco.svg"
URL_AVATAR_CHATBOT = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png"

COLOR_NARANJA = "#FF9500"
COLOR_VERDE = "#B5E61D"
COLOR_MORADO = "#A88DD4"
COLOR_CORAL = "#DF8768"
COLOR_NEGRO = "#000000"

def configurar_pagina():
    st.set_page_config(page_title="Gajo! Manager", page_icon=URL_FAVICON_ISO, layout="wide")
    st.markdown(f"""
        <style>
            .stApp {{ background-color: {COLOR_NEGRO}; color: white; }}
            [data-testid="stSidebar"] {{ background-color: #050505; border-right: 2px solid {COLOR_NARANJA}; }}
            [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: {COLOR_VERDE} !important; }}
            h1, h3 {{ color: {COLOR_NARANJA} !important; }}
            [data-testid="stChatMessage"] {{ background-color: #FFFFFF !important; border-radius: 20px !important; padding: 15px !important; }}
            [data-testid="stChatMessage"] p {{ color: #000000 !important; font-weight: 500; }}
            .stButton>button {{ background-color: {COLOR_CORAL} !important; color: white !important; border-radius: 25px; width: 100%; }}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# --- 🔧 FUNCIONES TÉCNICAS (RESTABLECIDAS) ---
# ==========================================

@st.cache_resource
def iniciar_conexion_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds).open_by_key(st.secrets["SHEET_ID"])
    except: return None

def cargar_datos(sh):
    if not sh: return pd.DataFrame(), {}
    try:
        # Cargamos sin caché excesiva para ver lo nuevo
        df_logs = pd.DataFrame(sh.worksheet("Chat_Logs").get_all_records())
        if not df_logs.empty:
            df_logs['Fecha_DT'] = pd.to_datetime(df_logs['Fecha'], dayfirst=True, errors='coerce')
        
        @st.cache_data(ttl=30) # La agenda se actualiza cada 30 seg
        def obtener_agenda(_sh):
            agenda = {}
            try:
                for h_name in ["Hoja 1", "Prospectos"]:
                    rows = _sh.worksheet(h_name).get_all_records()
                    for r in rows:
                        tel = r.get('Telefono_Cliente') or r.get('Telefono')
                        nom = r.get('Nombre_Cliente') or r.get('Nombre')
                        if tel: agenda[str(tel)] = nom or "Cliente Gajo"
            except: pass
            return agenda
        return df_logs, obtener_agenda(sh)
    except: return pd.DataFrame(), {}

def registrar_en_log(sh, telefono, nombre, emisor, mensaje):
    try:
        h = sh.worksheet("Chat_Logs")
        ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def enviar_archivo(telefono, archivo):
    """Función para enviar imágenes o PDFs (Restablecida)"""
    TOKEN, PHONE_ID = st.secrets["WHATSAPP_TOKEN"], st.secrets["PHONE_ID"]
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': (archivo.name, archivo.getvalue(), archivo.type)}
    data = {'messaging_product': 'whatsapp'}
    
    res_media = requests.post(url_media, headers=headers, files=files, data=data)
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        tipo = "image" if "image" in archivo.type else "document"
        url_msg = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": tipo, tipo: {"id": media_id}}
        return requests.post(url_msg, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}, json=payload)
    return res_media

# ==========================================
# --- 🖥️ INTERFAZ ---
# ==========================================

def main():
    configurar_pagina()
    st.image(URL_LOGO_HORIZONTAL, width=250)
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    with st.sidebar:
        st.markdown(f"## 👥 Agenda")
        if df_logs.empty:
            st.info("Sin mensajes...")
            tel_sel = None
        else:
            lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
            opciones = [f"{agenda.get(str(t), 'Nuevo Gajo')} ({t})" for t in lista_tels]
            sel_contacto = st.selectbox("Selecciona un chat:", opciones)
            tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
            nombre_sel = sel_contacto.split(" (")[0]
            
            st.divider()
            # SECCIÓN DE ADJUNTOS RESTABLECIDA
            st.markdown(f"### 📎 Enviar Archivo")
            archivo = st.file_uploader("Imagen o PDF:", type=['png', 'jpg', 'jpeg', 'pdf'])
            if archivo and st.button("🚀 ENVIAR ADJUNTO"):
                res = enviar_archivo(tel_sel, archivo)
                if res.status_code == 200:
                    registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", f"📎 Adjunto: {archivo.name}")
                    st.success("¡Enviado!")
                    time.sleep(1)
                    st.rerun()

    if tel_sel:
        st.markdown(f"### 💬 Chat: {nombre_sel}")
        chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha_DT')
        
        container = st.container(height=450)
        with container:
            for _, fila in chat_actual.iterrows():
                es_gajo = "Gajo" in str(fila['Emisor'])
                with st.chat_message("assistant" if es_gajo else "user", avatar=URL_AVATAR_CHATBOT if es_gajo else "👤"):
                    st.write(fila['Mensaje'])
                    st.caption(f"{fila['Fecha']} - {fila['Emisor']}")

        if resp := st.chat_input("Escribe tu respuesta..."):
            TOKEN, PHONE_ID = st.secrets["WHATSAPP_TOKEN"], st.secrets["PHONE_ID"]
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
            if requests.post(url, headers={"Authorization": f"Bearer {TOKEN}"}, json=payload).status_code == 200:
                registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
                st.rerun()

    # --- 🔄 LÓGICA DE ACTUALIZACIÓN AUTOMÁTICA ---
    # Esto refresca la app cada 30 segundos para traer mensajes nuevos de WA
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()
