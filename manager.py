import streamlit as st
import pandas as pd
import requests
import time
import gspread
import datetime
from google.oauth2.service_account import Credentials

# ==========================================
# --- 🖼️ CONFIGURACIÓN DE IMÁGENES ---
# ==========================================
URL_FAVICON_ISO = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Isotipo%20para%20Blanco.png"
URL_LOGO_HORIZONTAL = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/raw/refs/heads/main/Logo_Logotipo%20para%20Blanco.svg"
URL_AVATAR_CHATBOT = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png"

COLOR_PRIMARIO_NARANJA = "#FF9500"
COLOR_SECUNDARIO_VERDE = "#B5E61D"
COLOR_FONDO_OSCURO = "#1A1A1A"
COLOR_TEXTO = "#FFFFFF"

# ==========================================
# --- ⚙️ CONFIGURACIÓN INICIAL ---
# ==========================================
def configurar_pagina():
    st.set_page_config(
        page_title="Gajo! Manager",
        page_icon=URL_FAVICON_ISO,
        layout="wide",
        initial_sidebar_state="expanded" # Intenta mantenerlo abierto
    )

def aplicar_estilo_visual():
    st.markdown(f"""
        <style>
            .stApp {{ background-color: {COLOR_FONDO_OSCURO}; color: {COLOR_TEXTO}; }}
            [data-testid="stSidebar"] {{ background-color: #000000; border-right: 1px solid {COLOR_PRIMARIO_NARANJA}; }}
            h1, h2, h3, .stSubheader {{ color: {COLOR_PRIMARIO_NARANJA} !important; font-family: 'Montserrat', sans-serif; }}
            
            /* BOTONES */
            .stButton>button {{ background-color: {COLOR_SECUNDARIO_VERDE} !important; color: #000000 !important; border-radius: 20px; font-weight: bold; border: none; }}
            
            /* BURBUJAS BLANCAS CON TEXTO NEGRO */
            [data-testid="stChatMessage"] {{ 
                border-radius: 15px; 
                background-color: #FFFFFF !important; 
                padding: 15px;
                margin-bottom: 10px;
            }}
            [data-testid="stChatMessage"] p {{ color: #000000 !important; font-size: 16px; }}
            [data-testid="stChatMessage"] caption {{ color: #555555 !important; }}
            
            /* AVATARES */
            [data-testid="stChatMessageAvatar"] img {{ border-radius: 50%; border: 2px solid {COLOR_PRIMARIO_NARANJA}; }}
            
            #MainMenu, footer, header {{ visibility: hidden; }}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# --- 🔧 FUNCIONES DE CONEXIÓN ---
# ==========================================
@st.cache_resource
def iniciar_conexion_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["SHEET_ID"])
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def cargar_datos(sh):
    if not sh: return pd.DataFrame(), {}
    try:
        df_logs = pd.DataFrame(sh.worksheet("Chat_Logs").get_all_records())
        @st.cache_data(ttl=60)
        def obtener_agenda_nombres(_sheet_obj):
            agenda = {}
            try:
                h1 = _sheet_obj.worksheet("Hoja 1").get_all_records()
                h2 = _sheet_obj.worksheet("Prospectos").get_all_records()
                for r in h1: 
                    if r.get('Telefono_Cliente'): agenda[str(r['Telefono_Cliente'])] = r.get('Nombre_Cliente', 'Gajo Cliente')
                for r in h2:
                    if r.get('Telefono'): agenda[str(r['Telefono'])] = r.get('Nombre', 'Prospecto')
            except: pass
            return agenda
        agenda = obtener_agenda_nombres(sh)
        return df_logs, agenda
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return pd.DataFrame(), {}

def registrar_en_log(sh, telefono, nombre, emisor, mensaje):
    try:
        h = sh.worksheet("Chat_Logs")
        ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def enviar_archivo(telefono, archivo):
    TOKEN = st.secrets["WHATSAPP_TOKEN"]
    PHONE_ID = st.secrets["PHONE_ID"]
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers_media = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': (archivo.name, archivo.getvalue(), archivo.type)}
    data_media = {'messaging_product': 'whatsapp'}
    res_media = requests.post(url_media, headers=headers_media, files=files, data=data_media)
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        url_msg = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers_msg = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        tipo = "image" if "image" in archivo.type else "document"
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": tipo, tipo: {"id": media_id}}
        return requests.post(url_msg, headers=headers_msg, json=payload)
    return res_media

# ==========================================
# --- 🖥️ UI ---
# ==========================================
def main():
    configurar_pagina()
    aplicar_estilo_visual()
    
    # CABECERA: Logo escalado y centrado
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.image(URL_LOGO_HORIZONTAL, width=300)
        st.markdown("<h3 style='text-align: center; margin-top: -20px;'>Central de Mensajes</h3>", unsafe_allow_html=True)
    st.divider()
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    with st.sidebar:
        st.markdown(f"<h2 style='color: {COLOR_SECUNDARIO_VERDE} !important;'>👥 Conversaciones</h2>", unsafe_allow_html=True)
        if df_logs.empty:
            st.info("Esperando primeros mensajes...")
            tel_sel, nombre_sel = None, None
        else:
            lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
            opciones = [f"{agenda.get(str(t), 'Nuevo Gajo')} ({t})" for t in lista_tels]
            sel_contacto = st.selectbox("Selecciona un chat:", opciones)
            tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
            nombre_sel = sel_contacto.split(" (")[0]
            st.divider()
            st.markdown(f"<h3 style='color: {COLOR_SECUNDARIO_VERDE} !important;'>📁 Enviar Menú / Foto</h3>", unsafe_allow_html=True)
            archivo = st.file_uploader("Elige Imagen o PDF:", type=['png', 'jpg', 'jpeg', 'pdf'])
            if archivo and st.button("🚀 Enviar Archivo"):
                res = enviar_archivo(tel_sel, archivo)
                if res.status_code == 200:
                    registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", f"📎 Archivo: {archivo.name}")
                    st.success("¡Enviado!")
                    time.sleep(1)
                    st.rerun()

    if tel_sel:
        st.subheader(f"💬 Chat con: {nombre_sel}")
        chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha')
        container = st.container(height=500, border=True)
        with container:
            for _, fila in chat_actual.iterrows():
                es_gajo = "Gajo" in str(fila['Emisor'])
                with st.chat_message("assistant" if es_gajo else "user", avatar=URL_AVATAR_CHATBOT if es_gajo else "👤"):
                    st.write(fila['Mensaje'])
                    st.caption(f"{fila['Fecha']} - {fila['Emisor']}")
        
        if resp := st.chat_input("Escribe tu respuesta..."):
            TOKEN = st.secrets["WHATSAPP_TOKEN"]
            PHONE_ID = st.secrets["PHONE_ID"]
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
            if requests.post(url, headers=headers, json=payload).status_code == 200:
                registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
                st.rerun()

    time.sleep(25)
    st.rerun()

if __name__ == "__main__":
    main()
