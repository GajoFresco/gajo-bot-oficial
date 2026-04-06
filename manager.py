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

# Paleta Cítrica de Gajo!
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
            .stApp {{ background-color: {COLOR_NEGRO}; color: white; }}
            [data-testid="stSidebar"] {{ 
                background-color: #050505; 
                border-right: 2px solid {COLOR_NARANJA}; 
            }}
            [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: {COLOR_VERDE} !important; }}
            h1, .stSubheader {{ color: {COLOR_NARANJA} !important; }}

            /* Burbujas de Chat Blancas con texto negro para legibilidad */
            [data-testid="stChatMessage"] {{
                background-color: #FFFFFF !important;
                border-radius: 20px !important;
                padding: 15px !important;
                margin-bottom: 15px !important;
            }}
            [data-testid="stChatMessage"] p {{ 
                color: #000000 !important; 
                font-family: 'Segoe UI', sans-serif;
                font-weight: 500;
            }}
            .stButton>button {{
                background-color: {COLOR_CORAL} !important;
                color: white !important;
                border-radius: 25px;
                font-weight: bold;
                width: 100%;
            }}
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# --- 🔧 FUNCIONES TÉCNICAS (CONEXIÓN Y DATOS) ---
# ==========================================

@st.cache_resource
def iniciar_conexion_sheets():
    """Establece la conexión con Google Sheets usando los Secrets de Streamlit."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["SHEET_ID"])
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def cargar_datos(sh):
    """Carga los mensajes y la agenda desde el Google Sheet."""
    if not sh: return pd.DataFrame(), {}
    try:
        # 1. Leer Chat_Logs
        df_logs = pd.DataFrame(sh.worksheet("Chat_Logs").get_all_records())
        
        if not df_logs.empty:
            # CORRECCIÓN IMPORTANTE: Convertir a fecha real para ordenar cronológicamente
            # Sin esto, el chat se ve desordenado
            df_logs['Fecha_DT'] = pd.to_datetime(df_logs['Fecha'], dayfirst=True, errors='coerce')
        
        # 2. Leer Agenda (Nombres de clientes)
        @st.cache_data(ttl=60) # Actualiza la agenda cada minuto
        def obtener_agenda(_sh):
            agenda = {}
            try:
                h1 = _sh.worksheet("Hoja 1").get_all_records()
                h2 = _sh.worksheet("Prospectos").get_all_records()
                for r in h1: 
                    if r.get('Telefono_Cliente'): agenda[str(r['Telefono_Cliente'])] = r.get('Nombre_Cliente', 'Cliente Gajo')
                for r in h2:
                    if r.get('Telefono'): agenda[str(r['Telefono'])] = r.get('Nombre', 'Prospecto')
            except: pass
            return agenda
        
        return df_logs, obtener_agenda(sh)
    except Exception as e:
        st.warning(f"Aún no hay datos o la hoja cambió: {e}")
        return pd.DataFrame(), {}

def registrar_en_log(sh, telefono, nombre, emisor, mensaje):
    """Guarda en Google Sheets lo que Luis escribe desde el Manager."""
    try:
        h = sh.worksheet("Chat_Logs")
        ahora = (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S")
        h.append_row([ahora, str(telefono), nombre, emisor, mensaje])
    except: pass

def enviar_whatsapp(telefono, mensaje_texto):
    """Envía un mensaje de texto vía API de Meta."""
    TOKEN, PHONE_ID = st.secrets["WHATSAPP_TOKEN"], st.secrets["PHONE_ID"]
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": str(telefono),
        "type": "text",
        "text": {"body": mensaje_texto}
    }
    return requests.post(url, headers=headers, json=payload)

# ==========================================
# --- 🖥️ INTERFAZ PRINCIPAL ---
# ==========================================

def main():
    configurar_pagina()
    aplicar_estilo_visual()
    
    # Encabezado con Logo
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.image(URL_LOGO_HORIZONTAL, width=300)
    
    sh = iniciar_conexion_sheets()
    df_logs, agenda = cargar_datos(sh)
    
    # --- BARRA LATERAL (AGENDA) ---
    with st.sidebar:
        st.markdown(f"## 👥 Agenda Gajo!")
        if df_logs.empty:
            st.info("Esperando primer mensaje...")
            tel_sel = None
        else:
            # Obtener lista de teléfonos únicos, del más reciente al más antiguo
            lista_tels = df_logs['Telefono'].unique().tolist()[::-1]
            opciones = [f"{agenda.get(str(t), 'Nuevo Gajo')} ({t})" for t in lista_tels]
            
            sel_contacto = st.selectbox("Selecciona un chat:", opciones)
            # Extraer solo el número de lo seleccionado en el selectbox
            tel_sel = sel_contacto.split("(")[1].replace(")", "").strip()
            nombre_sel = sel_contacto.split(" (")[0]
            
            st.divider()
            st.caption("Gajo! Manager v1.0")

    # --- VENTANA DE CHAT ---
    if tel_sel:
        st.markdown(f"<h3 style='color: {COLOR_NARANJA};'>💬 Conversación: {nombre_sel}</h3>", unsafe_allow_html=True)
        
        # Filtrar mensajes del contacto seleccionado y ORDENAR por la fecha real
        chat_actual = df_logs[df_logs['Telefono'].astype(str) == str(tel_sel)].sort_values(by='Fecha_DT', ascending=True)
        
        # Contenedor con scroll para los mensajes
        container = st.container(height=500)
        with container:
            for _, fila in chat_actual.iterrows():
                # Identificar si el mensaje es de Luis o del Cliente
                es_gajo = "Gajo" in str(fila['Emisor'])
                
                with st.chat_message("assistant" if es_gajo else "user", avatar=URL_AVATAR_CHATBOT if es_gajo else "👤"):
                    st.write(fila['Mensaje'])
                    st.caption(f"{fila['Fecha']} - {fila['Emisor']}")
                
                # Celebración Gajo #100
                if "GAJO #100" in str(fila['Mensaje']).upper():
                    st.balloons()
                    st.success("¡GANADOR DEL GAJO DORADO!")

        # --- INPUT DE RESPUESTA ---
        if resp := st.chat_input("Escribe tu respuesta para Gajo!..."):
            res = enviar_whatsapp(tel_sel, resp)
            if res.status_code == 200:
                registrar_en_log(sh, tel_sel, nombre_sel, "Luis (Gajo)", resp)
                st.rerun() # Refresca para mostrar el mensaje enviado
            else:
                st.error("Error al enviar. Revisa el Token de Meta.")

    # Auto-refresco automático cada 30 segundos para ver mensajes nuevos del cliente
    # Quitamos el sleep de 25 segundos para que no se congele la app
    time.sleep(1) 
    # st.rerun() # Opcional: puedes activar esto si quieres que se actualice solo

if __name__ == "__main__":
    main()
