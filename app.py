from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from services.firebase_service import FirebaseService
from utils.helpers import generate_ticket_code, validate_flight_data, format_date
from utils.mailer import enviar_ticket_email  

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')

# Inicializar Firebase Service
firebase_service = FirebaseService()

# ==================== MIDDLEWARE DE AUTENTICACIÓN ====================

@app.before_request
def require_login():
    """Proteger rutas de administración"""
    # Solo proteger /admin y rutas que empiecen con /admin
    if (request.endpoint == 'admin' or 
        (request.endpoint and request.endpoint.startswith('admin_'))) and \
       not session.get('admin_logged_in'):
        return redirect(url_for('login'))

# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para administradores"""
    if request.method == 'POST':
        usuario = request.form['usuario']
        clave = request.form['clave']
        
        # Verificar credenciales (puedes hacerlo más seguro luego)
        if usuario == 'admin' and clave == 'admin123':
            session['admin_logged_in'] = True
            session['admin_user'] = usuario
            flash('Bienvenido al panel de administración', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Credenciales incorrectas', 'error')
            return render_template('login.html', error='Credenciales incorrectas'), 401
    
    # Si ya está logueado, redirigir al admin
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Cerrar sesión y redirigir al login"""
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('index'))

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
def index():
    """Página principal - Búsqueda y reserva de vuelos"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Panel de administración para gestionar vuelos"""
    admin_user = session.get('admin_user', 'Administrador')
    return render_template('admin.html', admin_user=admin_user)

# ==================== RUTAS DE VUELOS ====================

@app.route('/api/search_flights', methods=['POST'])
def search_flights():
    """Buscar vuelos disponibles"""
    try:
        data = request.get_json()
        origen = data.get('origen', '').lower()
        destino = data.get('destino', '').lower()
        fecha = data.get('fecha')
        
        if not all([origen, destino, fecha]):
            return jsonify({'error': 'Faltan datos requeridos'}), 400
        
        # Buscar vuelos en Firebase
        flights = firebase_service.search_flights(origen, destino, fecha)
        
        return jsonify({
            'success': True,
            'flights': flights,
            'count': len(flights)
        })
        
    except Exception as e:
        print(f"Error buscando vuelos: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/flights', methods=['GET'])
def get_all_flights():
    """Obtener todos los vuelos programados (para admin)"""
    # Esta ruta requiere autenticación admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
        
    try:
        flights = firebase_service.get_all_flights()
        return jsonify({
            'success': True,
            'flights': flights
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/flights', methods=['POST'])
def create_flight():
    """Crear nuevo vuelo programado"""
    # Esta ruta requiere autenticación admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
        
    try:
        data = request.get_json()

        # Validación de campos obligatorios
        required_fields = ['origen', 'destino', 'fecha', 'hora_partida', 'duracion']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} es obligatorio'}), 400

        # ✅ Renombrar el campo para que coincida con Firebase
        data['fecha'] = data.pop('fecha')

        # ✅ Calcular hora de llegada a partir de duración (ej. "2h 30m")
        try:
            hora_salida = datetime.strptime(data['hora_partida'], "%H:%M")
            partes = data['duracion'].lower().replace("h", "").replace("m", "").split()
            horas = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
            hora_llegada = hora_salida + timedelta(hours=horas, minutes=minutos)
            data['hora_llegada'] = hora_llegada.strftime("%H:%M")
        except Exception as e:
            return jsonify({'error': f'Error al calcular hora_llegada: {str(e)}'}), 400

        # ✅ Si no hay número de vuelo, se genera automáticamente
        if not data.get('numero_vuelo'):
            now = datetime.now()
            data['numero_vuelo'] = f"AF{now.strftime('%H%M')}{len(firebase_service.get_all_flights()) + 1}"

        # ✅ Campos por defecto
        data.setdefault('aerolinea', 'AeroFlash')
        data.setdefault('clase', 'Económica')
        data.setdefault('tipo_avion', 'Boeing 737')
        data.setdefault('puerta', 'TBD')
        data.setdefault('activo', True)
        data['precio'] = float(data.get('precio', 0))

        # ✅ Generar asientos según clase
        if not data.get('asientos_disponibles'):
            data['asientos_disponibles'] = firebase_service._generate_available_seats(data['clase'])

        # ✅ Guardar vuelo en Firebase
        flight_id = firebase_service.create_flight(data)

        if flight_id:
            data['id'] = flight_id
            return jsonify({
                'success': True,
                'message': 'Vuelo creado exitosamente',
                'flight': data  # ← se usa en el frontend
            }), 201
        else:
            return jsonify({'error': 'Error al crear el vuelo'}), 500

    except Exception as e:
        print(f"❌ Error creando vuelo: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/flights/<flight_id>', methods=['PUT'])
def update_flight(flight_id):
    """Actualizar vuelo existente"""
    # Esta ruta requiere autenticación admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
        
    try:
        data = request.get_json()
        
        # Validar datos
        validation_result = validate_flight_data(data)
        if not validation_result['valid']:
            return jsonify({'error': validation_result['message']}), 400
        
        success = firebase_service.update_flight(flight_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Vuelo actualizado exitosamente'
            })
        else:
            return jsonify({'error': 'Error al actualizar el vuelo'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/flights/<flight_id>', methods=['DELETE'])
def delete_flight(flight_id):
    """Eliminar vuelo"""
    # Esta ruta requiere autenticación admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
        
    try:
        success = firebase_service.delete_flight(flight_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Vuelo eliminado exitosamente'
            })
        else:
            return jsonify({'error': 'Error al eliminar el vuelo'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== RUTAS DE TICKETS/RESERVAS CORREGIDAS ====================

@app.route('/api/tickets', methods=['GET'])
def get_all_tickets():
    """Obtener todos los tickets/reservas (para el panel admin)"""
    # Verificar autenticación admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401

    try:
        print("🔄 Obteniendo tickets desde Firebase...")
        
        # Obtener datos directos de Firebase
        reservations = firebase_service.get_all_reservations()
        
        if not reservations:
            print("📝 No hay reservas/tickets en la base de datos")
            return jsonify({
                'success': True,
                'tickets': {},
                'count': 0
            })
        
        print(f"✅ Se encontraron {len(reservations)} tickets")
        print(f"🔍 Estructura de datos: {list(reservations.keys())[:3]}...")  # Mostrar primeras 3 claves
        
        return jsonify({
            'success': True,
            'tickets': reservations,
            'count': len(reservations)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo tickets: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'message': str(e)
        }), 500
    
@app.route('/api/reservations', methods=['GET'])
def get_all_reservations():
    """Obtener todas las reservas (endpoint alternativo para compatibilidad)"""
    # Redirigir a la función principal de tickets
    return get_all_tickets()

@app.route('/api/tickets/<ticket_id>', methods=['PUT'])
def update_ticket_status(ticket_id):
    """Actualizar estado de un ticket (para cancelaciones)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
    
    try:
        data = request.get_json()
        
        if not data or 'estado' not in data:
            return jsonify({'error': 'Estado requerido'}), 400
        
        print(f"🔄 Actualizando ticket {ticket_id} con estado: {data['estado']}")
        
        # Usar el método existente de firebase_service
        if data['estado'].lower() == 'cancelado':
            success = firebase_service.cancel_reservation(ticket_id)
        else:
            # Si firebase_service tiene un método para actualizar estado general
            if hasattr(firebase_service, 'update_reservation_status'):
                success = firebase_service.update_reservation_status(ticket_id, data['estado'])
            else:
                # Fallback: obtener la reserva, actualizar y guardar
                reservation = firebase_service.get_reservation(ticket_id)
                if reservation:
                    reservation['estado'] = data['estado']
                    success = firebase_service.update_reservation(ticket_id, reservation)
                else:
                    success = False
        
        if success:
            print(f"✅ Ticket {ticket_id} actualizado exitosamente")
            return jsonify({
                'success': True,
                'message': f'Ticket {ticket_id} actualizado exitosamente'
            })
        else:
            print(f"❌ No se pudo actualizar el ticket {ticket_id}")
            return jsonify({
                'success': False,
                'error': 'No se pudo actualizar el ticket'
            }), 400
            
    except Exception as e:
        print(f"❌ Error actualizando ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500

@app.route('/api/tickets/<ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    """Eliminar/cancelar un ticket específico"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
    
    try:
        print(f"🗑️ Eliminando ticket: {ticket_id}")
        
        # Usar el método de cancelación que ya tienes implementado
        success = firebase_service.cancel_reservation(ticket_id)
        
        if success:
            print(f"✅ Ticket {ticket_id} eliminado exitosamente")
            return jsonify({
                'success': True,
                'message': f'Ticket {ticket_id} eliminado exitosamente'
            })
        else:
            print(f"❌ No se pudo eliminar el ticket {ticket_id}")
            return jsonify({
                'success': False,
                'error': 'No se pudo eliminar el ticket'
            }), 400
            
    except Exception as e:
        print(f"❌ Error eliminando ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor'
        }), 500

@app.route('/api/reservations/<reservation_id>/cancel', methods=['PUT'])
def cancel_reservation(reservation_id):
    """Cancelar una reserva específica"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401
    
    try:
        print(f"🔄 Cancelando reserva: {reservation_id}")
        
        # Usar el método de firebase_service para cancelar
        success = firebase_service.cancel_reservation(reservation_id)
        
        if success:
            print(f"✅ Reserva {reservation_id} cancelada exitosamente")
            return jsonify({
                'success': True,
                'message': f'Reserva {reservation_id} cancelada exitosamente'
            })
        else:
            print(f"❌ No se pudo cancelar la reserva {reservation_id}")
            return jsonify({
                'success': False,
                'error': 'No se pudo cancelar la reserva'
            }), 400
            
    except Exception as e:
        print(f"❌ Error cancelando reserva {reservation_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'message': str(e)
        }), 500

# ==================== RUTAS DE RESERVAS ====================

@app.route('/api/book_flight', methods=['POST'])
def book_flight():
    """Reservar vuelo y generar ticket"""
    try:
        data = request.get_json()
        
        # Validar datos del pasajero
        required_fields = ['nombre_completo', 'dni', 'correo', 'flight_id', 'asiento']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} es requerido'}), 400
        
        flight_id = data['flight_id']
        asiento = data['asiento']
        
        # Verificar disponibilidad del vuelo y asiento
        flight = firebase_service.get_flight_by_id(flight_id)
        if not flight:
            return jsonify({'error': 'Vuelo no encontrado'}), 404
        
        if asiento not in flight.get('asientos_disponibles', []):
            return jsonify({'error': 'Asiento no disponible'}), 400
        
        # Generar código único del ticket
        ticket_code = generate_ticket_code()
        
        # Datos del pasajero
        passenger_data = {
            'nombre_completo': data['nombre_completo'],
            'dni': data['dni'],
            'correo': data['correo'],
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'genero': data.get('genero'),
            'telefono': data.get('telefono')
        }
        
        # Crear reserva completa
        reservation_data = {
            'codigo_ticket': ticket_code,
            'pasajero': passenger_data,
            'vuelo': {
                'numero_vuelo': flight['numero_vuelo'],
                'origen': flight['origen'],
                'destino': flight['destino'],
                'fecha': flight['fecha'],
                'hora_partida': flight['hora_partida'],
                'hora_llegada': flight['hora_llegada'],
                'clase': flight['clase'],
                'aerolinea': flight.get('aerolinea', 'AeroFlash'),
                'puerta': flight.get('puerta', 'TBD'),
                'asiento': asiento
            },
            'fecha_reserva': datetime.now().isoformat(),
            'estado': 'Confirmado',
            'precio': flight.get('precio', 0)
        }
        
        # Guardar reserva y actualizar disponibilidad
        success = firebase_service.create_reservation(ticket_code, reservation_data, flight_id, asiento)
        
        if success:

            # Enviar correo con ticket
            enviar_ticket_email(data['correo'], ticket_code, reservation_data)

            return jsonify({
                'success': True,
                'message': 'Reserva creada exitosamente',
                'ticket_code': ticket_code,
                'redirect_url': url_for('show_ticket', ticket_code=ticket_code)
            })
        else:
            return jsonify({'error': 'Error al procesar la reserva'}), 500
            
    except Exception as e:
        print(f"Error en reserva: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/ticket/<ticket_code>')
def show_ticket(ticket_code):
    try:
        data = firebase_service.get_reservation(ticket_code)
        
        if not data:
            return render_template('ticket_not_found.html', ticket_code=ticket_code)
        
        # Reconstruir estructura anidada esperada por el template
        reservation = {
            "ticket_code": ticket_code,
            "fecha_reserva": data.get("fecha_reserva", "Fecha no disponible"),
            "precio": data.get("precio", 0.0),
            "pasajero": {
                # Usar directamente los campos del objeto pasajero
                "nombre": data.get("pasajero", {}).get("nombre_completo", "N/A"),
                "apellido": "",  # Ya está incluido en nombre_completo
                "documento": data.get("pasajero", {}).get("dni", "N/A"),
                "email": data.get("pasajero", {}).get("correo", "N/A"),
                "telefono": data.get("pasajero", {}).get("telefono", "N/A"),
                "genero": data.get("pasajero", {}).get("genero", "Masculino"),
                "fecha_nacimiento": data.get("pasajero", {}).get("fecha_nacimiento", "N/A")
            },
            "vuelo": {
                # Usar directamente los campos del objeto vuelo
                "origen": data.get("vuelo", {}).get("origen", "N/A"),
                "destino": data.get("vuelo", {}).get("destino", "N/A"),
                "numero_vuelo": data.get("vuelo", {}).get("numero_vuelo", "N/A"),
                "fecha": data.get("vuelo", {}).get("fecha", "N/A"),
                "hora_partida": data.get("vuelo", {}).get("hora_partida", "N/A"),
                "hora_llegada": data.get("vuelo", {}).get("hora_llegada", "N/A"),
                "asiento": data.get("vuelo", {}).get("asiento", "N/A"),
                "aerolinea": data.get("vuelo", {}).get("aerolinea", "AeroFlash"),
                "clase": data.get("vuelo", {}).get("clase", "Primera"),
                "puerta": data.get("vuelo", {}).get("puerta", "C12")
            }
        }
        
        return render_template("ticket.html", reservation=reservation)
    
    except Exception as e:
        print(f"Error al obtener ticket {ticket_code}: {e}")
        return render_template('ticket_error.html', ticket_code=ticket_code)

@app.route('/search-ticket')
def search_ticket_page():
    """Página de búsqueda de tickets con manejo de errores mejorado"""
    return render_template('search.html')

@app.route('/search_ticket', methods=['POST'])
def search_ticket():
    """Buscar ticket por código con manejo de errores mejorado"""
    try:
        data = request.get_json() if request.is_json else request.form
        ticket_code = data.get('ticket_code', '').upper().strip()
        
        if not ticket_code:
            return jsonify({
                'success': False,
                'error': 'Código de ticket requerido',
                'error_type': 'validation'
            }), 400
        
        # Validar formato del código
        if len(ticket_code) < 6 or len(ticket_code) > 10:
            return jsonify({
                'success': False,
                'error': 'El código debe tener entre 6 y 10 caracteres',
                'error_type': 'format'
            }), 400
        
        reservation = firebase_service.get_reservation(ticket_code)
        
        if reservation:
            if request.is_json:
                return jsonify({
                    'success': True,
                    'ticket': reservation,
                    'redirect_url': url_for('show_ticket', ticket_code=ticket_code),
                    'message': 'Ticket encontrado exitosamente'
                })
            else:
                return redirect(url_for('show_ticket', ticket_code=ticket_code))
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Ticket no encontrado',
                    'error_type': 'not_found',
                    'ticket_code': ticket_code,
                    'suggestions': [
                        'Verifica que el código esté escrito correctamente',
                        'Asegúrate de que todas las letras y números sean correctos',
                        'El código debe tener el formato: AF123456'
                    ]
                }), 404
            else:
                flash(f'Ticket {ticket_code} no encontrado', 'error')
                return redirect(url_for('search_ticket_page'))
                
    except Exception as e:
        print(f"Error buscando ticket: {str(e)}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': 'Error interno del servidor',
                'error_type': 'server_error',
                'details': 'Por favor intenta nuevamente o contacta soporte'
            }), 500
        else:
            flash('Error al buscar el ticket. Intenta nuevamente.', 'error')
            return redirect(url_for('search_ticket_page'))

# ==================== APIS ADICIONALES ====================

@app.route('/api/ticket/<ticket_code>')
def get_ticket_api(ticket_code):
    """API para obtener datos del ticket con manejo de errores mejorado"""
    try:
        ticket_code = ticket_code.upper().strip()
        
        if not ticket_code:
            return jsonify({
                'success': False,
                'error': 'Código de ticket inválido'
            }), 400
        
        reservation = firebase_service.get_reservation(ticket_code)
        
        if not reservation:
            return jsonify({
                'success': False,
                'error': 'Ticket no encontrado',
                'ticket_code': ticket_code,
                'error_type': 'not_found'
            }), 404
        
        return jsonify({
            'success': True,
            'ticket': reservation,
            'message': 'Ticket obtenido exitosamente'
        })
        
    except Exception as e:
        print(f"Error API ticket {ticket_code}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'error_type': 'server_error'
        }), 500

@app.route('/api/available_seats/<flight_id>')
def get_seat_availability(flight_id):
    """Obtener todos los asientos y cuáles están ocupados"""
    try:
        flight = firebase_service.get_flight_by_id(flight_id)
        if not flight:
            return jsonify({'success': False, 'error': 'Vuelo no encontrado'}), 404

        # Todos los posibles asientos
        all_seats = flight.get('asientos_disponibles', []) + flight.get('asientos_ocupados', [])
        all_seats = list(set(all_seats))  # Evitar duplicados

        # Asientos ocupados = los que han sido reservados (están en 'asientos_ocupados')
        occupied_seats = flight.get('asientos_ocupados', [])

        # Asientos disponibles = todos menos los ocupados
        available_seats = [s for s in all_seats if s not in occupied_seats]

        return jsonify({
            'success': True,
            'available_seats': flight.get('asientos_disponibles', []),
            'occupied_seats': flight.get('asientos_ocupados', [])
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/dashboard-stats')
def get_dashboard_data():
    """Obtener datos para el dashboard del admin"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Acceso no autorizado'}), 401

    try:
        # Obtener estadísticas básicas
        stats = firebase_service.get_dashboard_stats()
        
        # Si no hay stats o están vacías, inicializar con valores por defecto
        if not stats:
            stats = {
                'total_flights': 0,
                'total_reservations': 0,
                'confirmed_reservations': 0,
                'pending_reservations': 0,
                'cancelled_reservations': 0,
                'total_revenue': 0.0,
                'average_price': 0.0,
                'flights_today': 0,
                'upcoming_flights': 0
            }
        
        # Obtener vuelos adicionales para mostrar en dashboard
        flights = firebase_service.get_all_flights()
        if flights:
            stats['total_flights'] = len(flights)
            
            # Contar vuelos de hoy y próximos
            today = datetime.now().strftime('%d/%m/%Y')
            flights_today = sum(1 for flight in flights if flight.get('fecha') == today)
            stats['flights_today'] = flights_today
            
            # Contar vuelos próximos (próximos 7 días)
            upcoming_count = 0
            for flight in flights:
                flight_date_str = flight.get('fecha', '')
                if flight_date_str:
                    try:
                        flight_date = datetime.strptime(flight_date_str, '%d/%m/%Y')
                        days_diff = (flight_date - datetime.now()).days
                        if 0 <= days_diff <= 7:
                            upcoming_count += 1
                    except ValueError:
                        continue
            stats['upcoming_flights'] = upcoming_count
        
        return jsonify({
            'success': True,
            'stats': stats,
            'flights': flights[:5] if flights else []  # Últimos 5 vuelos para mostrar
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas del dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'stats': {
                'total_flights': 0,
                'total_reservations': 0,
                'confirmed_reservations': 0,
                'pending_reservations': 0,
                'cancelled_reservations': 0,
                'total_revenue': 0.0,
                'average_price': 0.0,
                'flights_today': 0,
                'upcoming_flights': 0
            }
        }), 500

# ==================== MANEJO DE ERRORES ====================

# Manejo de errores globales mejorado
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Recurso no encontrado',
            'error_type': 'not_found'
        }), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'error_type': 'server_error'
        }), 500
    return render_template('500.html'), 500

# ==================== FILTROS JINJA2 ====================

@app.template_filter('format_date')
def format_date_filter(date_string):
    """Filtro para formatear fechas en templates"""
    return format_date(date_string)

@app.template_filter('format_currency')
def format_currency_filter(amount):
    """Filtro para formatear moneda"""
    return f"S/ {amount:,.2f}"

# ==================== CONTEXTO GLOBAL ====================

@app.context_processor
def inject_globals():
    """Inyectar variables globales en todos los templates"""
    return {
        'app_name': 'AeroFlash',
        'current_year': datetime.now().year,
        'current_date': datetime.now().strftime('%Y-%m-%d'),
        'is_admin_logged_in': session.get('admin_logged_in', False),
        'admin_user': session.get('admin_user', '')
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5009))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"🚀 Iniciando AeroFlash en puerto {port}")
    print(f"🔧 Modo debug: {debug}")
    print(f"🔐 Sistema de autenticación activado")
    
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=port
    )