import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def enviar_ticket_email(destinatario, ticket_code, reserva):
    try:
        remitente = os.getenv('SENDER_EMAIL')
        password = os.getenv('SENDER_PASSWORD')
        asunto = f'✈️ Confirmación de Vuelo - {ticket_code} | AeroFlash Airlines'

        mensaje = MIMEMultipart('alternative')
        mensaje['From'] = f'AeroFlash Airlines <{remitente}>'
        mensaje['To'] = destinatario
        mensaje['Subject'] = asunto

        # Texto plano como respaldo
        texto_plano = f"""
        Hola {reserva['pasajero']['nombre_completo']},

        Tu reserva para el vuelo {reserva['vuelo']['numero_vuelo']} ha sido confirmada.

        Detalles del vuelo:
        • Origen: {reserva['vuelo']['origen']}
        • Destino: {reserva['vuelo']['destino']}
        • Fecha: {reserva['vuelo']['fecha']}
        • Hora de salida: {reserva['vuelo']['hora_partida']}
        • Asiento: {reserva['vuelo']['asiento']}
        • Clase: {reserva['vuelo']['clase']}

        Código de Ticket: {ticket_code}

        Información importante:
        • Llegada recomendada: 2 horas antes para vuelos nacionales
        • Documentos requeridos: DNI o Pasaporte vigente
        • Check-in online disponible 24 horas antes del vuelo

        ¡Gracias por elegir AeroFlash Airlines!

        Atentamente,
        El equipo de AeroFlash Airlines
        """

        # HTML con diseño profesional
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Confirmación de Vuelo</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background-color: #f4f7fa;
                }}
                
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }}
                
                .header .subtitle {{
                    font-size: 16px;
                    opacity: 0.9;
                }}
                
                .confirmation-badge {{
                    background-color: #10b981;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-size: 14px;
                    font-weight: 600;
                    margin: 20px auto;
                    display: inline-block;
                }}
                
                .content {{
                    padding: 30px;
                }}
                
                .greeting {{
                    font-size: 18px;
                    margin-bottom: 20px;
                    color: #2d3748;
                }}
                
                .flight-card {{
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 12px;
                    margin: 25px 0;
                    position: relative;
                    overflow: hidden;
                }}
                
                .flight-card::before {{
                    content: '✈️';
                    position: absolute;
                    top: 15px;
                    right: 20px;
                    font-size: 24px;
                    opacity: 0.3;
                }}
                
                .route {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                
                .city {{
                    font-size: 24px;
                    font-weight: bold;
                }}
                
                .arrow {{
                    font-size: 20px;
                    margin: 0 15px;
                }}
                
                .flight-date {{
                    font-size: 18px;
                    margin-bottom: 10px;
                }}
                
                .flight-number {{
                    font-size: 16px;
                    opacity: 0.9;
                }}
                
                .details-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin: 25px 0;
                }}
                
                .detail-item {{
                    background-color: #f8fafc;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                
                .detail-label {{
                    font-size: 12px;
                    color: #64748b;
                    font-weight: 600;
                    text-transform: uppercase;
                    margin-bottom: 5px;
                }}
                
                .detail-value {{
                    font-size: 16px;
                    color: #1e293b;
                    font-weight: 600;
                }}
                
                .ticket-code {{
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    margin: 25px 0;
                }}
                
                .ticket-code h3 {{
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                
                .code {{
                    font-size: 24px;
                    font-weight: bold;
                    letter-spacing: 2px;
                }}
                
                .important-info {{
                    background-color: #fef3c7;
                    border: 1px solid #f59e0b;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 25px 0;
                }}
                
                .important-info h4 {{
                    color: #92400e;
                    margin-bottom: 15px;
                    font-size: 16px;
                }}
                
                .important-info ul {{
                    list-style: none;
                    padding: 0;
                }}
                
                .important-info li {{
                    color: #78350f;
                    margin-bottom: 8px;
                    padding-left: 20px;
                    position: relative;
                }}
                
                .important-info li::before {{
                    content: '•';
                    color: #f59e0b;
                    font-weight: bold;
                    position: absolute;
                    left: 0;
                }}
                
                .footer {{
                    background-color: #1f2937;
                    color: white;
                    padding: 25px;
                    text-align: center;
                }}
                
                .footer h3 {{
                    margin-bottom: 15px;
                    color: #60a5fa;
                }}
                
                .contact-info {{
                    font-size: 14px;
                    margin-bottom: 15px;
                }}
                
                .social-links {{
                    margin-top: 15px;
                }}
                
                .btn {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 25px;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 600;
                    margin: 15px 10px;
                    transition: transform 0.2s;
                }}
                
                .btn:hover {{
                    transform: translateY(-2px);
                }}
                
                @media (max-width: 600px) {{
                    .details-grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .route {{
                        flex-direction: column;
                        text-align: center;
                    }}
                    
                    .city {{
                        font-size: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <!-- Header -->
                <div class="header">
                    <h1>🛫 AeroFlash Airlines</h1>
                    <p class="subtitle">Tu vuelo ha sido confirmado</p>
                    <div class="confirmation-badge">✅ CONFIRMADO</div>
                </div>
                
                <!-- Content -->
                <div class="content">
                    <p class="greeting">Hola <strong>{reserva['pasajero']['nombre_completo']}</strong>,</p>
                    
                    <p>¡Excelentes noticias! Tu reserva ha sido confirmada exitosamente. Aquí tienes todos los detalles de tu vuelo:</p>
                    
                    <!-- Flight Card -->
                    <div class="flight-card">
                        <div class="route">
                            <div class="city">{reserva['vuelo']['origen']}</div>
                            <div class="arrow">→</div>
                            <div class="city">{reserva['vuelo']['destino']}</div>
                        </div>
                        <div class="flight-date">📅 {reserva['vuelo']['fecha']}</div>
                        <div class="flight-number">Vuelo {reserva['vuelo']['numero_vuelo']}</div>
                    </div>
                    
                    <!-- Details Grid -->
                    <div class="details-grid">
                        <div class="detail-item">
                            <div class="detail-label">Hora de Salida</div>
                            <div class="detail-value">🕐 {reserva['vuelo']['hora_partida']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Hora de Llegada</div>
                            <div class="detail-value">🕐 {reserva['vuelo']['hora_llegada']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Asiento</div>
                            <div class="detail-value">💺 {reserva['vuelo']['asiento']}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Clase</div>
                            <div class="detail-value">⭐ {reserva['vuelo']['clase']}</div>
                        </div>
                    </div>
                    
                    <!-- Ticket Code -->
                    <div class="ticket-code">
                        <h3>🎫 Tu Código de Ticket</h3>
                        <div class="code">{ticket_code}</div>
                    </div>
                    
                    <!-- Important Information -->
                    <div class="important-info">
                        <h4>📋 Información Importante</h4>
                        <ul>
                            <li>Llegada recomendada: 2 horas antes para vuelos nacionales</li>
                            <li>Documentos requeridos: DNI o Pasaporte vigente</li>
                            <li>Equipaje de mano: Máximo 8kg</li>
                            <li>Check-in online disponible 24 horas antes del vuelo</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="#" class="btn">Ver Ticket Completo</a>
                        <a href="#" class="btn">Check-in Online</a>
                    </div>
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <h3>¡Gracias por elegir AeroFlash Airlines!</h3>
                    <div class="contact-info">
                        📞 +51 1 234-5678 | ✉️ info@aeroflash.com<br>
                        🌐 www.aeroflash.com
                    </div>
                    <p style="font-size: 12px; opacity: 0.8; margin-top: 15px;">
                        © 2025 AeroFlash Airlines. Todos los derechos reservados.<br>
                        Este email contiene información confidencial de tu reserva.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Crear partes del mensaje
        parte_texto = MIMEText(texto_plano, 'plain', 'utf-8')
        parte_html = MIMEText(html_content, 'html', 'utf-8')

        # Adjuntar ambas partes
        mensaje.attach(parte_texto)
        mensaje.attach(parte_html)

        # Enviar email
        servidor = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.sendmail(remitente, destinatario, mensaje.as_string())
        servidor.quit()
        
        print(f"📨 Correo enviado correctamente a {destinatario}")
        return True

    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False