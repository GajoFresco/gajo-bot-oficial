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
# ⚠️ IMPORTANTE: Reemplaza estas URLs por tus enlaces "Raw" permanentes de GitHub
# Para PNGs: Clic derecho en botón "Raw" en GitHub -> Copiar dirección de enlace.
URL_FAVICON_ISO = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_Isotipo%20para%20Blanco.png"
URL_LOGO_HORIZONTAL = "https://github.com/GajoFresco/gajo-bot-oficial/raw/refs/heads/main/Logo_Logotipo%20para%20Blanco.svg"
URL_AVATAR_CHATBOT = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png"
URL_AVATAR_LUIS = "https://raw.githubusercontent.com/GajoFresco/gajo-bot-oficial/main/Logo_ChatBot%20para%20Blanco.png" # Puedes cambiarlo por tu foto si quieres

# ==========================================
# --- 🎨 PALETA DE COLORES (Ref: Menú) ---
# ==========================================
COLOR_PRIMARIO_NARANJA = "#FF9500"
COLOR_SECUNDARIO_VERDE = "#B5E61D"
COLOR_FONDO_OSCURO = "#1A1A1A"
COLOR_TEXTO = "#FFFFFF"

# ==========================================
# --- ⚙️ CONFIGURACIÓN INICIAL ---
# ==========================================
def configurar_pagina():
    st.set_page_config(
        page_title="Gajo! Central de Mensajes",
        page_icon=URL_FAVICON_ISO, # Isotipo como detalle pequeño
        layout="wide",
        initial_sidebar_state="expanded"
    )

def aplicar_estilo_visual():
    """Inyecta CSS personalizado para branding Plus Ultra"""
    st.markdown(f"""
        <style>
            /* Fondo Principal */
            .stApp {{
                background-color: {COLOR_FONDO_OSCURO};
                color: {COLOR_TEXTO};
            }}
            
            /* Sidebar */
            [data-testid="stSidebar"] {{
                background-color: #000000;
                border-right: 1px solid {COLOR_PRIMARIO_NARANJA};
            }}
            
            /* Títulos y Subtítulos */
            h1, h2, h3, .stSubheader {{
                color: {COLOR_PRIMARIO_NARANJA} !important;
                font-family: 'Montserrat', sans-serif;
            }}
            
            /* Botones Primarios (Enviar Archivo) */
            .stButton>button {{
                background-color: {COLOR_SECUNDARIO_VERDE} !important;
                color: #000000 !important;
                border-radius: 20px;
                border: none;
                font-weight: bold;
                transition: all 0.3s;
            }}
            .stButton>button:hover {{
                background-color: {COLOR_TEXTO} !important;
                transform: scale(1.05);
            }}

            /* Inputs y Selectbox */
            .stSelectbox div[data-baseweb="select"] {{
                border-color: {COLOR_PRIMARIO_NARANJA};
            }}

            /* Estilo de Chat Input */
            .stChatInputContainer {{
                border-top: 1px solid {COLOR_PRIMARIO_NARANJA};
                background-color: #000000;
            }}

            /* Contenedor de Chat (Burbujas Flotantes) */
            [data-testid="stChatMessage"] {{
                border-radius: 15px;
                padding: 1rem;
                margin-bottom: 10px;
                background-color: #262626; /* Fondo burbuja por defecto */
            }}
            
            /* Ajuste Avatares circulares */
            [data-testid="stChatMessageAvatar"] img {{
                border-radius: 50%;
                border: 2px solid {COLOR_PRIMARIO_NARANJA};
            }}

            /* Ocultar barra de Streamlit */
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header {{visibility: hidden;}}
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
        st.error(f"❌ Error de conexión a Google Sheets: {e}")
        return None

def cargar_datos(sh):
    if not sh: return pd.DataFrame(), {}
    
    try:
        # 1. Cargar logs
        df_logs = pd.DataFrame(sh.worksheet("Chat_Logs").get_all_records())
        
        # 2. Cargar Agendas para nombres
        @st.cache_data(ttl=60)
        def obtener_agenda_nombres(sheet_obj):
            agenda = {}
            try:
                h1 = sheet_obj.worksheet("Hoja 1").get_all_records()
                h2 = sheet_obj.worksheet("Prospectos").get_all_records()
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
# --- 📝 FUNCIONES OPERATIVAS WA ---
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
    
    # 1. Subir Media
    url_media = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers_media = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': (archivo.name, archivo.getvalue(), archivo.type)}
    data_media = {'messaging_product': 'whatsapp'}
    res_media = requests.post(url_media, headers=headers_media, files=files, data=data_media)
    
    if res_media.status_code == 200:
        media_id = res_media.json()['id']
        # 2. Enviar Mensaje
        url_msg = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers_msg = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        tipo = "image" if "image" in archivo.type else "document"
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": tipo, tipo: {"id": media_id}}
        return requests.post(url_msg, headers=headers_msg, json=payload)
    return res_media

# ==========================================
# --- 🖥️ RENDERIZADO DE LA UI ---
# ==========================================
def renderizar_cabecera():
    # Logo Horizontal como Cabecera Principal (reemplaza st.title)
    st.image(URL_LOGO_HORIZONTAL, use_container_width=True)
    st.markdown(f"<h3 style='text-align: center; color: {COLOR_TEXTO} !important;'>Central de Mensajes Inteligente</h3>", unsafe_allow_html=True)
    st.divider()

def renderizar_sidebar(df_logs, agenda):
    with st.sidebar:
        st.markdown(f"<h2 style='color: {COLOR_SECUNDARIO_VERDE} !important;'>👥 Conversaciones</h2>", unsafe_allow_html=True)
        
        if df_logs.empty:
            st.info("Esperando primeros mensajes...")
            return None, None
            
        # Obtener teléfonos únicos recientes
        lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
        
        # Formatear opciones: "Nombre (Teléfono)"
        opciones = []
        for t in lista_tels:
            nombre = agenda.get(str(t), "Nuevo Gajo")
            opciones.append(f"{nombre} ({t})")
            
        sel_contacto = st.selectbox("Selecciona un chat:", opciones)
        
        # Extraer datos de la selección
        tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
        nombre_sel = sel_contacto.split(" (")[0]

        # --- Sección Multimedia ---
        st.divider()
        st.markdown(f"<h3 style='color: {COLOR_SECUNDARIO_VERDE} !important;'>📁 Enviar Menú / Foto</h3>", unsafe_allow_html=True)
        archivo = st.file_uploader("Elige Imagen o PDF:", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        return tel_sel, nombre_sel, archivo

def renderizar_chat(df_logs, tel_sel, nombre_sel):
    st.subheader(f"💬 Chat con: {nombre_sel}")
    st.caption(f"📱 Número: {tel_sel}")
    st.divider()
    
    # Filtrar chat actual y ordenar cronológicamente
    chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha')
    
    # Contenedor con scroll
    container = st.container(height=500, border=True)
    with container:
        for _, fila in chat_actual.iterrows():
            # Identificar emisor para rol y avatar
            es_gajo = "Gajo" in str(fila['Emisor'])
            rol = "assistant" if es_gajo else "user"
            
            # Usar Avatar ChatBot para Gajo!, ícono usuario para cliente
            avatar_url = URL_AVATAR_CHATBOT if es_gajo else "👤"
            
            with st.chat_message(rol, avatar=avatar_url):
                st.write(fila['Mensaje'])
                st.caption(f"{fila['Fecha']} - {fila['Emisor']}")

def renderizar_input_texto(sh, tel_sel, nombre_sel):
    if resp := st.chat_input("Escribe tu respuesta aquí..."):
        TOKEN = st.secrets["WHATSAPP_TOKEN"]
        PHONE_ID = st.secrets["PHONE_ID"]
        url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": tel_sel, "type": "text", "text": {"body": resp}}
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
            st.rerun()
        else:
            st.error(f"❌ Error enviando mensaje: {response.text}")

# ==========================================
# --- 🎬 FLUJO PRINCIPAL (MAIN) ---
# ==========================================
def main():
    configurar_pagina()
    aplicar_estilo_visual()
    renderizar_cabecera()
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    # Sidebar y obtener selección
    resultado_sidebar = renderizar_sidebar(df_logs, agenda)
    
    if resultado_sidebar and resultado_sidebar[0]:
        tel_sel, nombre_sel, archivo = resultado_sidebar
        
        # Manejo de envío de archivos
        if archivo and st.button("🚀 Enviar Archivo Seleccionado"):
            with st.spinner("Subiendo y enviando multimedia..."):
                res = enviar_archivo(tel_sel, archivo)
                if res.status_code == 200:
                    registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", f"📎 Archivo enviado: {archivo.name}")
                    st.success(f"✅ {archivo.name} enviado correctamente.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error enviando archivo: {res.text}")

        # Renderizar Chat e Input
        renderizar_chat(df_logs, tel_sel, nombre_sel)
        renderizar_input_texto(sh, tel_sel, nombre_sel)
        
    elif df_logs.empty:
        st.info("La central está lista. Los mensajes aparecerán aquí cuando los clientes escriban.")

    # Auto-refresco cada 25 segundos
    time.sleep(25)
    st.rerun()

if __name__ == "__main__":
    main()
