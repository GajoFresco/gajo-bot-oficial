import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time

# --- ⚙️ CONFIGURACIÓN ---
TOKEN = st.secrets["WHATSAPP_TOKEN"]
PHONE_ID = st.secrets["PHONE_ID"]
SHEET_ID = st.secrets["SHEET_ID"]

# Conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
hoja = client.open_by_key(SHEET_ID).sheet1

st.set_page_config(page_title="Gajo! Manager", page_icon="🍹")

# --- 🔄 AUTO-REFRESH ---
# Esto hace que la página se refresque sola cada 10 segundos
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

# --- 📊 LECTURA DE DATOS REALES ---
def cargar_datos():
    datos = hoja.get_all_records()
    return pd.DataFrame(datos)

df = cargar_datos()

st.title("🍹 Gajo! Central de Mensajes")

if not df.empty:
    # Creamos una lista de "Teléfono (Nombre)" para el menú
    # Ajusta los nombres de las columnas si en tu Excel son distintos
    df['Etiqueta'] = df['Telefono_Cliente'].astype(str) + " (" + df['Nombre_Cliente'] + ")"
    
    with st.sidebar:
        st.header("Clientes Recientes")
        opciones = df['Etiqueta'].unique().tolist()
        cliente_sel_etiqueta = st.selectbox("Selecciona un chat", opciones)
        
        if st.button("🔄 Actualizar ahora"):
            st.rerun()

    # Filtrar datos del cliente seleccionado
    tel_seleccionado = cliente_sel_etiqueta.split(" (")[0]
    datos_cliente = df[df['Telefono_Cliente'].astype(str) == tel_seleccionado].iloc[-1]

    st.subheader(f"Chat con: {cliente_sel_etiqueta}")

    # Historial (Mostramos lo que el cliente escribió)
    historial = f"Cliente dice: {datos_cliente['Mensaje_Cliente']}"
    st.text_area("Último mensaje recibido:", value=historial, height=100, disabled=True)

    # --- ✉️ ENVIAR RESPUESTA ---
    respuesta = st.text_input("Escribe tu respuesta para el cliente:")

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
                # Opcional: Podríamos anotar tu respuesta en el Excel aquí
            else:
                st.error(f"Error al enviar: {res.text}")
else:
    st.warning("Aún no hay clientes en el Excel. ¡Manda un mensaje de prueba!")

# Script sencillo para refrescar la página
st.empty()
time.sleep(10)
st.rerun()
