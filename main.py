# --- 🌐 EL WEBHOOK REFORZADO ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # 1. Responder a la verificación de Meta (Esto ya funciona)
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == WEBHOOK_TOKEN:
            return request.args.get("hub.challenge")
        return "Error de token", 403

    # 2. Procesar mensajes reales
    if request.method == 'POST':
        data = request.get_json()
        try:
            # Verificamos que sea un mensaje de WhatsApp
            if data.get('entry') and data['entry'][0].get('changes') and data['entry'][0]['changes'][0]['value'].get('messages'):
                msg_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
                num_cliente = msg_obj['from']
                
                # Manejar si el mensaje es texto
                if 'text' in msg_obj:
                    mensaje_cliente = msg_obj['text']['body'].strip()
                    info = obtener_datos_vaso(mensaje_cliente)

                    if info:
                        vaso = info['Numero_Vaso']
                        clave = info['Codigo_Secreto']
                        if vaso in [43, 100]:
                            respuesta = f"¡Felicidades! 🎉 Eres el cliente #{vaso}.\n¡GANASTE UN TOPPING EXTRA! 🍓\nClave: {clave}\n\n¿Qué coctel te preparamos?"
                        else:
                            respuesta = f"¡Hola! 🍹 Estás disfrutando el Gajo #{vaso}.\nGracias por preferirnos.\n\nRecuerda que pidiendo por aquí el precio es especial. ✨"
                    else:
                        respuesta = "¡Hola! 🍹 Bienvenido a Gajo!. Escanea el QR de tu vaso para ver si tienes premio o para ordenar de nuevo."
                    
                    enviar_wa(respuesta, num_cliente)

        except Exception as e:
            print(f"❌ Error procesando mensaje: {e}")
        
        # SIEMPRE responder 200 a Meta para que no se desconecte
        return "EVENT_RECEIVED", 200

    # 3. Fallback para cualquier otra petición (HEAD, etc.)
    return "OK", 200
