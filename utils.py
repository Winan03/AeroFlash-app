import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def generate_ticket_code():
    """Generar código único para el ticket"""
    # Formato: AF + 4 números aleatorios + 2 letras aleatorias
    numbers = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    return f"AF{numbers}{letters}"

def format_date(date_str):
    """Formatear fecha para mostrar"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d de %B de %Y')
    except:
        return date_str

def format_time(time_str):
    """Formatear hora para mostrar"""
    try:
        time_obj = datetime.strptime(time_str, '%H:%M')
        return time_obj.strftime('%I:%M %p')
    except:
        return time_str

def send_ticket_email(email, passenger_name, ticket_data):
    """Enviar ticket por correo electrónico"""
    try:
        # Configuración del servidor SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if not sender_email or not sender_password:
            print("⚠️ Credenciales de email no configuradas")
            return False
            
        # Crear mensaje
        message = MIMEMultipart("alternative")
        message["Subject"] = f"🎫 Tu Ticket de Vuelo - {ticket_data['codigo_ticket']}"
        message["From"] = sender_email
        message["To"] = email
        
        # Contenido HTML del correo
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }}
                .ticket-code {{ font-size: 28px; font-weight: bold; letter-spacing: 3px; margin: 10px 0; }}
                .content {{ padding: 30px 20px; }}
                .section {{ margin-bottom: 25px; }}
                .section-title {{ color: #333; font-size: 18px; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
                .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .label {{ font-weight: bold; color: #555; }}
                .value {{ color: #333; }}
                .flight-route {{ text-align: center; margin: 20px 0; padding: 20px; background: #f8f9ff; border-radius: 10px; }}
                .route {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; }}
                .barcode {{ text-align: center; margin: 20px 0; }}
                .barcode-lines {{ font-family: 'Courier New', monospace; font-size: 20px; color: #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✈️ AeroFlash Airlines</h1>
                    <div class="ticket-code">{ticket_data['codigo_ticket']}</div>
                    <p>Ticket de Vuelo Confirmado</p>
                </div>
                
                <div class="content">
                    <div class="section">
                        <div class="section-title">👤 Información del Pasajero</div>
                        <div class="info-row">
                            <span class="label">Nombre:</span>
                            <span class="value">{ticket_data['pasajero']['nombre_completo']}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">DNI:</span>
                            <span class="value">{ticket_data['pasajero']['dni']}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Género:</span>
                            <span class="value">{ticket_data['pasajero']['genero']}</span>
                        </div>
                    </div>
                    
                    <div class="flight-route">
                        <div class="route">{ticket_data['vuelo']['origen']} → {ticket_data['vuelo']['destino']}</div>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">✈️ Detalles del Vuelo</div>
                        <div class="info-row">
                            <span class="label">Vuelo:</span>
                            <span class="value">{ticket_data['vuelo'].get('numero_vuelo', 'AA1234')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Fecha:</span>
                            <span class="value">{format_date(ticket_data['vuelo']['fecha'])}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Partida:</span>
                            <span class="value">{format_time(ticket_data['vuelo']['hora_partida'])}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Llegada:</span>
                            <span class="value">{format_time(ticket_data['vuelo']['hora_llegada'])}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Clase:</span>
                            <span class="value">{ticket_data['vuelo'].get('clase', 'Económica')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Asiento:</span>
                            <span class="value">{ticket_data['vuelo'].get('asiento', '12A')}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">Puerta:</span>
                            <span class="value">{ticket_data['vuelo'].get('puerta', 'B5')}</span>
                        </div>
                    </div>
                    
                    <div class="barcode">
                        <div class="barcode-lines">||||| ||| |||| | ||| |||| |||||</div>
                        <p>Código de Barras: {ticket_data['codigo_ticket']}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>⚠️ Importante:</strong> Presenta este ticket en el aeropuerto junto con tu documento de identidad.</p>
                    <p>Llegada recomendada: 2 horas antes del vuelo para vuelos nacionales.</p>
                    <p>© 2025 AeroFlash Airlines - Todos los derechos reservados</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Crear parte HTML
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Enviar correo
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
            
        print(f"✅ Correo enviado exitosamente a {email}")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar correo: {str(e)}")
        return False

def validate_email(email):
    """Validar formato de correo electrónico"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_dni(dni):
    """Validar formato de DNI (8 dígitos)"""
    return dni.isdigit() and len(dni) == 8

def mask_credit_card(card_number):
    """Enmascarar número de tarjeta de crédito"""
    if len(card_number) >= 4:
        return "*" * (len(card_number) - 4) + card_number[-4:]
    return card_number