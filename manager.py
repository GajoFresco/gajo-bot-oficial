import streamlit as st
import pandas as pd
import requests
import time
import gspread
import datetime
from google.oauth2.service_account import Credentials

# ==========================================
# --- 🖼️ CONFIGURACIÓN DE IMÁGENES (RAW LINKS) ---
# ==========================================
# ⚠️ RECUERDA: Mantén aquí tus enlaces "Raw" permanentes de GitHub
URL_FAVICON_ISO = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Isotipo%20para%20Blanco.png"
URL_LOGO_HORIZONTAL = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Logotipo%20para%20Blanco.svg"
URL_AVATAR_CHATBOT = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png"

# ==========================================
# --- 🎨 PALETA DE COLORES CÍTRICA (Ref: Menú) ---
# ==========================================
COLOR_NARANJA_GAJO = "#FF9500"    # Títulos Principales
COLOR_VERDE_CITRICO = "#B5E61D"   # Sidebar y Subtítulos
COLOR_MORADO_ANCESTRAL = "#A88DD4" # Acentos Gajo! (Avatar/Borde)
COLOR_CORAL_TROPICAL = "#DF8768"   # Botones (Fondo)
COLOR_FONDO_OSCURO = "#000000"    # Fondo General App
COLOR_FONDO_CHAT_BLANCO = "#FFFFFF" # Cuadro General Chat (Hoja Blanca)
COLOR_BUB_GAJO_NEGRA = "#000000"   # Burbuja Gajo!
COLOR_BUB_CLIENTE_OSCURA = "#1A1A1A" # Burbuja Cliente
COLOR_TEXTO_LUZ = "#FFFFFF"       # Texto dentro de burbujas

# ==========================================
# --- ⚙️ CONFIGURACIÓN INICIAL ---
# ==========================================
def configurar_pagina():
    st.set_page_config(
        page_title="Gajo! Manager Plus Ultra",
        page_icon=URL_FAVICON_ISO,
        layout="wide",
        initial_sidebar_state="expanded"
    )

def aplicar_estilo_visual():
    """Inyecta CSS para Alto Lujo (Black & White) con acentos cítricos"""
    st.markdown(f"""
        <style>
            /* Fondo General de la App (Total Negro) */
            .stApp {{
                background-color: {COLOR_FONDO_OSCURO};
                color: {COLOR_TEXTO_LUZ};
            }}
            
            /* Sidebar: Dark con acentos Verde Cítrico */
            [data-testid="stSidebar"] {{
                background-color: #0d0d0d;
                border-right: 2px solid {COLOR_NARANJA_GAJO};
            }}
            
            /* Títulos y Subtítulos Principales (Naranja) */
            h1, .stSubheader, [data-testid="stSidebar"] h1 {{
                color: {COLOR_NARANJA_GAJO} !important;
                font-family: 'Montserrat', sans-serif;
            }}
            
            /* Sidebar Subheaders y Texto (Verde Cítrico) */
            [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {{
                color: {COLOR_VERDE_CITRICO} !important;
                font-family: 'Segoe UI', sans-serif;
            }}

            /* Inputs y Selectbox con borde naranja */
            .stSelectbox div[data-baseweb="select"] {{
                border-color: {COLOR_NARANJA_GAJO};
            }}

            /* Input de Chat con borde Naranja */
            .stChatInputContainer {{
                border-top: 1px solid {COLOR_NARANJA_GAJO};
                background-color: #000000;
                margin-top: 20px;
            }}

            /* --- 🛡️ EL CUADRO GENERAL DEL CHAT BLANCO (Alto Lujo) --- */
            [data-testid="stVerticalBlock"] > div > div > [data-testid="stChatMessageContainer"] {{
                background-color: {COLOR_FONDO_CHAT_BLANCO} !important;
                border-radius: 20px;
                padding: 25px !important;
                margin-bottom: 25px;
                box-shadow: inset 0 4px 15px rgba(0,0,0,0.1);
                border: 2px solid #E0E0E0;
            }}

            /* --- 💬 BURBUJAS DE CHAT OSCURAS SOBRE BLANCO --- */
            
            /* Gajo! (Tú): Negro Puro con acento Morado Ancestral */
            [data-testid="stChatMessageAssistant"] {{
                background-color: {COLOR_BUB_GAJO_NEGRA} !important;
                border-radius: 20px 20px 20px 5px !important;
                border: 2px solid {COLOR_MORADO_ANCESTRAL} !important; /* Borde morado */
                color: {COLOR_TEXTO_LUZ} !important;
                margin-bottom: 15px;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
            }}

            /* Cliente: Gris Muy Oscuro */
            [data-testid="stChatMessageUser"] {{
                background-color: {COLOR_BUB_CLIENTE_OSCURA} !important;
                border-radius: 20px 20px 5px 20px !important;
                color: {COLOR_TEXTO_LUZ} !important;
                margin-bottom: 15px;
                box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
            }}

            /* Texto dentro de las burbujas nítido */
            [data-testid="stChatMessageAssistant"] p, [data-testid="stChatMessageUser"] p {{
                color: {COLOR_TEXTO_LUZ} !important;
                font-size: 16px;
                font-family: 'Segoe UI', sans-serif;
            }}
            
            /* Captions (hora y emisor) en gris claro para que se lean */
            [data-testid="stChatMessage"] caption {{
                color: #AAAAAA !important;
            }}
            
            /* Gajo! Caption con acento morado */
            [data-testid="stChatMessageAssistant"] caption {{
                color: {COLOR_MORADO_ANCESTRAL} !important;
            }}

            /* --- 👤 AVATARES --- */
            [data-testid="stChatMessageAvatar"] img {{
                border-radius: 50%;
                border: 2px solid {COLOR_MORADO_ANCESTRAL};
                background-color: white;
                padding: 1px;
            }}

            /* --- 📁 SECCIÓN DE ARCHIVOS (Botón Coral) --- */
            .stButton>button {{
                background-color: {COLOR_CORAL_TROPICAL} !important;
                color: #FFFFFF !important;
                border-radius: 20px;
                font-weight: bold;
                border: none;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .stButton>button:hover {{
                transform: scale(1.03);
                box-shadow: 0 4px 15px rgba(223, 135, 104, 0.4);
            }}

            /* Ocultar elementos de Streamlit */
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
                    if r.get('Telefono_Cliente'): agenda[str(r['Telefono_Cliente'])] = r.get('Nombre_Cliente', 'Gajo Sin Nombre')
                for r in h2:
                    if r.get('Telefono'): agenda[str(r['Telefono'])] = r.get('Nombre', 'Prospecto')
            except: pass
            return agenda
        agenda = obtener_agenda_nombres(sh)
        return df_logs, agenda
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return pd.DataFrame(), {}

# ==========================================
# --- 📝 FUNCIONES WA ---
# ==========================================
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
# --- 🖥️ UI (CABECERA Y sidebar) ---
# ==========================================
def main():
    configurar_pagina()
    aplicar_estilo_visual()
    
    # --- 1. CABECERA: Logo Centrado y Escalado (300px) ---
    st.image(URL_LOGO_HORIZONTAL, width=300)
    st.markdown(f"<h3 style='text-align: center; color: {COLOR_TEXTO_LUZ} !important; margin-top: -15px;'>Central de Mensajes Inteligente</h3>", unsafe_allow_html=True)
    st.divider()
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    # --- 2. sidebar CON ACENTOS VERDE CÍTRICO ---
    with st.sidebar:
        # Título Verde
        st.markdown(f"<h2 style='color: {COLOR_VERDE_CITRICO} !important; display: flex; align-items: center;'><span style='margin-right: 10px;'>👥</span> Conversaciones</h2>", unsafe_allow_html=True)
        
        if df_logs.empty:
            st.info("Esperando primeros mensajes...")
            tel_sel, nombre_sel = None, None
        else:
            lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
            opciones = [f"{agenda.get(str(t), 'Nuevo Gajo')} ({t})" for t in lista_tels]
            sel_contacto = st.selectbox("Selecciona un chat:", opciones)
            tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
            nombre_sel = sel_contacto.split(" (")[0]
            
            # --- 3. SECCIÓN ARCHIVOS (Boton Coral) ---
            st.divider()
            st.markdown(f"<h3 style='color: {COLOR_VERDE_CITRICO} !important; display: flex; align-items: center;'><span style='margin-right: 10px;'>📁</span> Enviar Menú / Foto</h3>", unsafe_allow_html=True)
            archivo = st.file_uploader("Elige Imagen o PDF:", type=['png', 'jpg', 'jpeg', 'pdf'])
            if archivo and st.button("🚀 Enviar Archivo Seleccionado"):
                with st.spinner("Subiendo y enviando multimedia..."):
                    res = enviar_archivo(tel_sel, archivo)
                    if res.status_code == 200:
                        registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", f"📎 Archivo: {archivo.name}")
                        st.success("¡Enviado!")
                        time.sleep(1)
                        st.rerun()

    # --- 4. ÁREA DE CHAT (BLANCA) ---
    if tel_sel:
        st.markdown(f"<subheader style='color: {COLOR_NARANJA_GAJO}; font-size: 20px; font-weight: bold; display: flex; align-items: center;'><span style='margin-right: 10px;'>💬</span> Chat con: {nombre_sel}</subheader>", unsafe_allow_html=True)
        st.caption(f"📱 Número: {tel_sel}")
        st.divider()
        
        chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha')
        
        # El contenedor que se volverá blanco por CSS
        container = st.container(height=550, border=True)
        with container:
            for _, fila in chat_actual.iterrows():
                es_gajo = "Gajo" in str(fila['Emisor'])
                # Avatar ChatBot con borde Morado Ancestral
                with st.chat_message("assistant" if es_gajo else "user", avatar=URL_AVATAR_CHATBOT if es_gajo else "👤"):
                    st.write(fila['Mensaje'])
                    st.caption(f"{fila['Fecha']} - {fila['Emisor']}")
        
        # Input de Chat (borde naranja)
        if resp := st.chat_input("Escribe tu respuesta aquí..."):
            TOKEN = st.secrets["WHATSAPP_TOKEN"]
            PHONE_ID = st.secrets["PHONE_ID"]
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
            if requests.post(url, headers=headers, json=payload).status_code == 200:
                registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
                st.rerun()

    # Auto-refresco
    time.sleep(25)
    st.rerun()

if __name__ == "__main__":
    main()
