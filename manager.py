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
URL_LOGO_HORIZONTAL = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Logotipo%20para%20Blanco.svg"
URL_AVATAR_CHATBOT = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png"

# Paleta Cítrica
COLOR_NARANJA = "#FF9500"
COLOR_VERDE = "#B5E61D"
COLOR_MORADO = "#A88DD4"
COLOR_CORAL = "#DF8768"
COLOR_NEGRO = "#000000"

# ==========================================
# --- ⚙️ CONFIGURACIÓN INICIAL ---
# ==========================================
def configurar_pagina():
    st.set_page_config(
        page_title="Gajo! Manager",
        page_icon=URL_FAVICON_ISO,
        layout="wide",
        initial_sidebar_state="auto"
    )

def aplicar_estilo_visual():
    st.markdown(f"""
        <style>
            /* Fondo de la App */
            .stApp {{ background-color: {COLOR_NEGRO}; color: white; }}
            
            /* Sidebar Estilo Gajo */
            [data-testid="stSidebar"] {{ 
                background-color: #050505; 
                border-right: 2px solid {COLOR_NARANJA}; 
            }}
            [data-testid="stSidebar"] h2 {{ color: {COLOR_VERDE} !important; }}
            [data-testid="stSidebar"] h3 {{ color: {COLOR_VERDE} !important; }}

            /* Títulos */
            h1, .stSubheader {{ color: {COLOR_NARANJA} !important; }}

            /* --- 💬 BURBUJAS BLANCAS (Contraste Máximo) --- */
            [data-testid="stChatMessage"] {{
                background-color: #FFFFFF !important;
                border-radius: 20px !important;
                padding: 15px !important;
                margin-bottom: 15px !important;
                box-shadow: 0 4px 6px rgba(255,255,255,0.1);
            }}
            /* Texto Negro dentro de burbujas */
            [data-testid="stChatMessage"] p {{ 
                color: #000000 !important; 
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: 500;
            }}
            /* Captions en gris oscuro */
            [data-testid="stChatMessage"] caption {{ color: #555555 !important; }}
            
            /* Avatares con borde morado */
            [data-testid="stChatMessageAvatar"] img {{ 
                border: 2px solid {COLOR_MORADO}; 
                border-radius: 50%;
            }}

            /* --- 📁 BOTÓN CORAL --- */
            .stButton>button {{
                background-color: {COLOR_CORAL} !important;
                color: white !important;
                border-radius: 25px;
                border: none;
                font-weight: bold;
                width: 100%;
            }}

            /* MOSTRAR EL MENÚ EN MÓVIL (Corregido) */
            /* Solo ocultamos el logo de Streamlit y el footer, dejamos el header para el botón */
            #MainMenu {{ visibility: hidden; }}
            footer {{ visibility: hidden; }}
            header {{ background-color: rgba(0,0,0,0); }}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# --- 🔧 FUNCIONES TÉCNICAS ---
# ==========================================
@st.cache_resource
def iniciar_conexion_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["SHEET_ID"])
    except: return None

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
                    if r.get('Telefono_Cliente'): agenda[str(r['Telefono_Cliente'])] = r.get('Nombre_Cliente', 'Cliente Gajo')
                for r in h2:
                    if r.get('Telefono'): agenda[str(r['Telefono'])] = r.get('Nombre', 'Prospecto')
            except: pass
            return agenda
        agenda = obtener_agenda_nombres(sh)
        return df_logs, agenda
    except: return pd.DataFrame(), {}

def registrar_en_log(sh, telefono, nombre, emisor, mensaje):
    try:
        h = sh.worksheet("Chat_Logs")
        ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def enviar_archivo(telefono, archivo):
    TOKEN, PHONE_ID = st.secrets["WHATSAPP_TOKEN"], st.secrets["PHONE_ID"]
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    res_media = requests.post(url_media, headers={"Authorization": f"Bearer {TOKEN}"}, 
                             files={'file': (archivo.name, archivo.getvalue(), archivo.type)}, 
                             data={'messaging_product': 'whatsapp'})
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        tipo = "image" if "image" in archivo.type else "document"
        return requests.post(f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages", 
                            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
                            json={"messaging_product": "whatsapp", "to": str(telefono), "type": tipo, tipo: {"id": media_id}})
    return res_media

# ==========================================
# --- 🖥️ INTERFAZ ---
# ==========================================
def main():
    configurar_pagina()
    aplicar_estilo_visual()
    
    # Logo Centrado
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.image(URL_LOGO_HORIZONTAL, width=300)
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    with st.sidebar:
        st.markdown(f"## 👥 Agenda")
        if df_logs.empty:
            st.info("Sin mensajes...")
            tel_sel, nombre_sel = None, None
        else:
            lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
            opciones = [f"{agenda.get(str(t), 'Nuevo Gajo')} ({t})" for t in lista_tels]
            sel_contacto = st.selectbox("Selecciona un chat:", opciones)
            tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
            nombre_sel = sel_contacto.split(" (")[0]
            
            st.divider()
            st.markdown(f"### 📁 Enviar Menú")
            archivo = st.file_uploader("Sube imagen o PDF:", type=['png', 'jpg', 'jpeg', 'pdf'])
            if archivo and st.button("🚀 ENVIAR"):
                res = enviar_archivo(tel_sel, archivo)
                if res.status_code == 200:
                    registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", f"📎 Envió: {archivo.name}")
                    st.success("¡Enviado!")
                    time.sleep(1)
                    st.rerun()

    if tel_sel:
        st.subheader(f"💬 Chat con: {nombre_sel}")
        chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha')
        
        container = st.container(height=500)
        with container:
            for _, fila in chat_actual.iterrows():
                es_gajo = "Gajo" in str(fila['Emisor'])
                with st.chat_message("assistant" if es_gajo else "user", avatar=URL_AVATAR_CHATBOT if es_gajo else "👤"):
                    st.write(fila['Mensaje'])
                    st.caption(f"{fila['Fecha']} - {fila['Emisor']}")
        
        if resp := st.chat_input("Escribe tu respuesta aquí..."):
            TOKEN, PHONE_ID = st.secrets["WHATSAPP_TOKEN"], st.secrets["PHONE_ID"]
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
            if requests.post(url, headers={"Authorization": f"Bearer {TOKEN}"}, json=payload).status_code == 200:
                registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
                st.rerun()

    time.sleep(25)
    st.rerun()

if __name__ == "__main__":
    main()
