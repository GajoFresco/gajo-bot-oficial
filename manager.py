import streamlit as st
import pandas as pd
import requests
import os
import time
import gspread
from google.oauth2.service_account import Credentials

# --- ⚙️ CONFIGURACIÓN ---
TOKEN = st.secrets["WHATSAPP_TOKEN"]
PHONE_ID = st.secrets["PHONE_ID"]
SHEET_ID = st.secrets["SHEET_ID"]

# --- 📗 CONEXIÓN A GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹", layout="wide")

# Estilos personalizados para el chat
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 📊 FUNCIONES DE CARGA ---
def cargar_pedidos():
    hoja = client.open_by_key(SHEET_ID).worksheet("Hoja 1")
    return pd.DataFrame(hoja.get_all_records())

def cargar_prospectos():
    try:
        hoja = client.open_by_key(SHEET_ID).worksheet("Prospectos")
        return pd.DataFrame(hoja.get_all_records())
    except:
        return pd.DataFrame()

# --- 🖥️ INTERFAZ PRINCIPAL ---
st.title("🍹 Gajo! Central de Mensajes")

# Pestañas para separar Pedidos de Prospectos
tab1, tab2 = st.tabs(["🛒 Pedidos (QR)", "👥 Prospectos (Manual)"])

# --- TAB 1: PEDIDOS QR ---
with tab1:
    df_pedidos = cargar_pedidos()
    if not df_pedidos.empty:
        # Limpiamos y preparamos datos
        df_pedidos['Etiqueta'] = df_pedidos['Telefono_Cliente'].astype(str) + " (" + df_pedidos['Nombre_Cliente'] + ")"
        
        with st.sidebar:
            st.header("📲 Chat Activo")
            cliente_sel = st.selectbox("Selecciona un pedido:", df_pedidos['Etiqueta'].unique().tolist()[::-1], key="sel_qr")
        
        tel_actual = cliente_sel.split(" (")[0]
        datos_c = df_pedidos[df_pedidos['Telefono_Cliente'].astype(str) == tel_actual].iloc[-1]

        st.subheader(f"Conversación con {datos_c['Nombre_Cliente']}")
        
        # VISUALIZACIÓN DE CHAT ORDINARIO (Burbujas)
        with st.container(border=True):
            # Mensaje del cliente (Lo que está en la Columna I)
            with st.chat_message("user", avatar="👤"):
                st.write(f"**Cliente:** {datos_c['Mensaje_Cliente']}")
                st.caption(f"Enviado: {datos_c.get('Timestamp', '---')}")
            
            # Nota: Si quisieras ver TODO el historial, tendríamos que guardar cada mensaje en una fila nueva.
            # Por ahora, muestra el último mensaje registrado en ese vaso.

        # --- CAJA DE RESPUESTA ---
        respuesta = st.chat_input("Escribe tu respuesta para el pedido...", key="input_qr")
        if respuesta:
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": tel_actual, "type": "text", "text": {"body": respuesta}}
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                st.success("Mensaje enviado")
                st.rerun()

# --- TAB 2: PROSPECTOS ---
with tab2:
    df_pros = cargar_prospectos()
    if not df_pros.empty:
        df_pros['Etiqueta'] = df_pros['Telefono'].astype(str) + " (" + df_pros['Nombre'] + ")"
        
        cliente_p = st.selectbox("Selecciona un prospecto:", df_pros['Etiqueta'].unique().tolist()[::-1], key="sel_p")
        
        tel_p = cliente_p.split(" (")[0]
        # Aquí sí podemos filtrar por historial porque append_row crea filas nuevas
        historial_p = df_pros[df_pros['Telefono'].astype(str) == tel_p]

        st.subheader(f"Atención a {cliente_p}")

        with st.container(border=True):
            for _, fila in historial_p.iterrows():
                with st.chat_message("user", avatar="✨"):
                    st.write(f"{fila['Mensaje']}")
                    st.caption(f"Hora: {fila['Hora']}")

        respuesta_p = st.chat_input("Responder a prospecto...", key="input_p")
        if respuesta_p:
            url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
            headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": tel_p, "type": "text", "text": {"body": respuesta_p}}
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                st.success("Mensaje enviado")
                st.rerun()
    else:
        st.info("No hay prospectos registrados todavía.")

# --- 🔄 AUTO-REFRESH ---
time.sleep(15)
st.rerun()
