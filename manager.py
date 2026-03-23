import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["WHATSAPP_TOKEN"]
PHONE_ID = st.secrets["PHONE_ID"]
SHEET_ID = st.secrets["SHEET_ID"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
hoja = client.open_by_key(SHEET_ID).sheet1

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹", layout="wide")

def cargar_datos():
    # Cargamos todo el Excel
    datos = hoja.get_all_records()
    return pd.DataFrame(datos)

df = cargar_datos()

st.title("🍹 Gajo! Central de Mensajes")

if not df.empty:
    # Identificamos las columnas por posición para evitar errores de nombre
    # Asumimos: Col E (4) es Nombre, Col F (5) es Teléfono, Col I (8) es Mensaje
    cols = df.columns.tolist()
    
    # Limpieza de datos
    df['Nombre_Cliente'] = df.iloc[:, 4].replace('', 'Nuevo Cliente') # Columna E
    df['Telefono_Cliente'] = df.iloc[:, 5].astype(str)               # Columna F
    
    # Etiqueta para el menú
    df['Etiqueta'] = df['Telefono_Cliente'] + " (" + df['Nombre_Cliente'] + ")"
    
    with st.sidebar:
        st.header("📋 Pedidos Activos")
        # Invertimos para ver los últimos registros primero
        opciones = df[df['Estatus'] == 'Registrado']['Etiqueta'].unique().tolist()[::-1]
        if not opciones:
            st.write("No hay pedidos registrados aún.")
            cliente_sel_etiqueta = None
        else:
            cliente_sel_etiqueta = st.selectbox("Selecciona un chat", opciones)
        
        st.divider()
        if st.button("🔄 Actualizar"):
            st.rerun()

    if cliente_sel_etiqueta:
        tel_seleccionado = str(cliente_sel_etiqueta.split(" (")[0])
        
        # Filtramos la fila de este cliente
        datos_cliente = df[df['Telefono_Cliente'] == tel_seleccionado].iloc[-1]

        st.subheader(f"Chat con: {cliente_sel_etiqueta}")

        # --- MOSTRAR EL MENSAJE ESPECÍFICO ---
        # Buscamos en la Columna I (índice 8 en 0-based)
        mensaje_actual = datos_cliente.iloc[8] # Columna I
        
        with st.chat_message("user"):
            st.write(f"**Cliente dice:** {mensaje_actual}")
            if len(datos_cliente) > 9: # Si existe la columna J
                st.caption(f"Hora: {datos_cliente.iloc[9]}")

        # --- ENVIAR RESPUESTA ---
        st.write("---")
        respuesta = st.text_input("Tu respuesta:", placeholder="Ej: ¡Va para allá! 🛵")
        
        if st.button("🚀 Enviar a WhatsApp"):
            if respuesta:
                url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
                headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
                payload = {
                    "messaging_product": "whatsapp",
                    "to": tel_seleccionado,
                    "type": "text",
                    "text": {"body": respuesta}
                }
                res = requests.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    st.success("¡Mensaje enviado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Error al enviar")
else:
    st.info("Esperando que caiga el primer Gajo... 🍋")

# Auto-refresh cada 20 segundos para no saturar Google
time.sleep(20)
st.rerun()
