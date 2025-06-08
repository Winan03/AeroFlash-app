import firebase_admin
from firebase_admin import credentials, db
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

class FirebaseService:
    def __init__(self):
        """Inicializa la conexión con Firebase, compatible con entorno local y producción (Render)."""
        try:
            if not firebase_admin._apps:
                cred = self._load_credentials()
                firebase_admin.initialize_app(cred, {
                    'databaseURL': self._get_database_url()
                })
            self.db = db
            print("✅ Firebase inicializado correctamente")
        except Exception as e:
            print(f"❌ Error al inicializar Firebase: {e}")
            raise

    def _load_credentials(self):
        """Carga las credenciales desde un archivo local o desde variables de entorno (Render)."""
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', './firebase-credentials.json')

        if os.path.exists(cred_path):
            print("📁 Usando archivo de credenciales local")
            return credentials.Certificate(cred_path)
        else:
            print("🌐 Usando variables de entorno para credenciales")
            cred_dict = {
                "type": "service_account",
                "project_id": os.getenv('FIREBASE_PROJECT_ID', 'sistema-predictivo-aereo'),
                "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.getenv('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL')
            }
            return credentials.Certificate(cred_dict)

    def _get_database_url(self):
        """Obtiene la URL de la base de datos de Firebase."""
        return os.getenv(
            'FIREBASE_DATABASE_URL',
            'https://sistema-predictivo-aereo-default-rtdb.firebaseio.com/'
        )

    # ==================== OPERACIONES DE VUELOS ====================

    def get_all_flights(self):
        """Obtener todos los vuelos - CORREGIDO para Realtime Database"""
        try:
            # Usar Realtime Database en lugar de Firestore
            flights_ref = self.db.reference('vuelos_programados')
            flights_data = flights_ref.get()
            
            if not flights_data:
                print("📝 No hay vuelos en Firebase")
                return []
            
            flights_list = []
            for flight_id, flight_data in flights_data.items():
                if isinstance(flight_data, dict):
                    flight_data['id'] = flight_id
                    flights_list.append(flight_data)
            
            # Ordenar por fecha
            flights_list.sort(key=lambda x: x.get('fecha', ''), reverse=True)
            print(f"✅ Se obtuvieron {len(flights_list)} vuelos")
            return flights_list
            
        except Exception as e:
            print(f"❌ Error obteniendo vuelos: {str(e)}")
            return []
        
    def get_flight_by_id(self, flight_id: str) -> Optional[Dict]:
        """Obtener vuelo por ID"""
        try:
            ref = self.db.reference(f'vuelos_programados/{flight_id}')
            flight_data = ref.get()
            
            if flight_data and isinstance(flight_data, dict):
                flight_data['id'] = flight_id
            
            return flight_data
            
        except Exception as e:
            print(f"Error obteniendo vuelo {flight_id}: {str(e)}")
            return None

    def get_all_reservations(self) -> Dict:
        """Obtener todas las reservas (tickets) guardadas en Firebase - FORMATO CORRECTO"""
        try:
            ref = self.db.reference('tickets')
            reservations_data = ref.get()
            
            if not reservations_data:
                print("📝 No hay reservas en Firebase")
                return {}
            
            print(f"🔍 Datos brutos de Firebase: {reservations_data}")
            
            # ✅ DEVOLVER LOS DATOS TAL COMO ESTÁN EN FIREBASE
            # El frontend se encargará de la transformación
            return reservations_data
            
        except Exception as e:
            print(f"❌ Error obteniendo reservas: {str(e)}")
            return {}

    def cancel_reservation(self, reservation_id: str) -> bool:
        try:
            ref = self.db.reference(f"tickets/{reservation_id}")
            if ref.get():
                ref.update({"estado": "Cancelada"})
                return True
            return False
        except Exception as e:
            print(f"Error cancelando reserva: {str(e)}")
            return False

    # ==================== ESTADÍSTICAS CORREGIDAS ====================

    def get_dashboard_stats(self):
        """Obtener estadísticas para el dashboard - CORREGIDO"""
        try:
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
            
            # ✅ CORREGIDO: Usar Realtime Database en lugar de Firestore
            
            # Obtener vuelos
            flights_ref = self.db.reference('vuelos_programados')
            flights_data = flights_ref.get()
            
            if flights_data:
                flights_list = []
                for flight_id, flight_data in flights_data.items():
                    if isinstance(flight_data, dict):
                        flight_data['id'] = flight_id
                        flights_list.append(flight_data)
                
                stats['total_flights'] = len(flights_list)
                
                # Calcular vuelos de hoy y próximos
                today = datetime.now().strftime('%d/%m/%Y')
                stats['flights_today'] = sum(1 for f in flights_list if f.get('fecha') == today)
                
                # Contar vuelos próximos (próximos 7 días)
                upcoming_count = 0
                for flight in flights_list:
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
            
            # Obtener reservas
            reservations_ref = self.db.reference('tickets')
            reservations_data = reservations_ref.get()
            
            if reservations_data:
                reservations_list = []
                for reservation_id, reservation_data in reservations_data.items():
                    if isinstance(reservation_data, dict):
                        reservation_data['id'] = reservation_id
                        reservations_list.append(reservation_data)
                
                stats['total_reservations'] = len(reservations_list)
                
                # Procesar reservas para obtener estadísticas detalladas
                total_revenue = 0
                for reservation in reservations_list:
                    status = reservation.get('estado', 'pendiente').lower()
                    
                    if status == 'confirmado':
                        stats['confirmed_reservations'] += 1
                    elif status == 'cancelado' or status == 'cancelada':
                        stats['cancelled_reservations'] += 1
                    else:
                        stats['pending_reservations'] += 1
                    
                    # Sumar ingresos solo de reservas confirmadas
                    if status == 'confirmado':
                        try:
                            price = float(reservation.get('precio', 0))
                            total_revenue += price
                        except (ValueError, TypeError):
                            continue
                
                stats['total_revenue'] = round(total_revenue, 2)
                
                # Calcular precio promedio
                if stats['confirmed_reservations'] > 0:
                    stats['average_price'] = round(total_revenue / stats['confirmed_reservations'], 2)
            
            print(f"📊 Estadísticas calculadas: {stats}")
            return stats
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {str(e)}")
            return {
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

    def _calculate_basic_stats(self, flights: List[Dict], reservations: List[Dict]) -> Dict:
        """Calcular estadísticas básicas"""
        try:
            active_flights = [f for f in flights if f.get('activo', True)]
            confirmed_reservations = [r for r in reservations if r.get('estado') == 'Confirmado']
            
            return {
                'total_flights': len(flights),
                'active_flights': len(active_flights),
                'total_reservations': len(reservations),
                'confirmed_reservations': len(confirmed_reservations),
                'pending_reservations': len([r for r in reservations if r.get('estado') == 'Pendiente']),
                'cancelled_reservations': len([r for r in reservations if r.get('estado') == 'Cancelado'])
            }
        except Exception as e:
            print(f"Error calculando estadísticas básicas: {str(e)}")
            return {}

    def _calculate_flight_stats(self, flights: List[Dict]) -> Dict:
        """Calcular estadísticas específicas de vuelos"""
        try:
            today = datetime.now().date()
            upcoming_flights = []
            flights_by_route = defaultdict(int)
            flights_by_date = defaultdict(int)
            
            for flight in flights:
                if not flight.get('activo', True):
                    continue
                    
                # Vuelos próximos
                try:
                    flight_date_str = flight.get('fecha', '')
                    if flight_date_str:
                        flight_date = datetime.strptime(flight_date_str, '%Y-%m-%d').date()
                        if flight_date >= today:
                            upcoming_flights.append(flight)
                            
                        # Estadísticas por fecha
                        flights_by_date[flight_date_str] += 1
                except ValueError:
                    continue
                
                # Estadísticas por ruta
                origen = flight.get('origen', 'N/A')
                destino = flight.get('destino', 'N/A')
                route = f"{origen} → {destino}"
                flights_by_route[route] += 1
            
            # Top 5 rutas más populares
            top_routes = sorted(flights_by_route.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'upcoming_flights': len(upcoming_flights),
                'flights_today': flights_by_date.get(today.strftime('%Y-%m-%d'), 0),
                'flights_this_week': self._count_flights_this_week(flights),
                'flights_by_route': dict(flights_by_route),
                'top_routes': top_routes,
                'total_routes': len(flights_by_route)
            }
        except Exception as e:
            print(f"Error calculando estadísticas de vuelos: {str(e)}")
            return {}

    def _calculate_reservation_stats(self, reservations: List[Dict]) -> Dict:
        """Calcular estadísticas específicas de reservas"""
        try:
            reservations_by_status = defaultdict(int)
            reservations_by_date = defaultdict(int)
            recent_reservations = []
            
            today = datetime.now().date()
            
            for reservation in reservations:
                status = reservation.get('estado', 'N/A')
                reservations_by_status[status] += 1
                
                # Reservas recientes (últimos 7 días)
                try:
                    created_date_str = reservation.get('fecha_creacion', '')
                    if created_date_str:
                        created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00')).date()
                        reservations_by_date[created_date.strftime('%Y-%m-%d')] += 1
                        
                        if (today - created_date).days <= 7:
                            recent_reservations.append(reservation)
                except (ValueError, TypeError):
                    continue
            
            return {
                'reservations_by_status': dict(reservations_by_status),
                'recent_reservations_count': len(recent_reservations),
                'reservations_today': reservations_by_date.get(today.strftime('%Y-%m-%d'), 0),
                'reservations_this_week': sum(1 for r in recent_reservations),
                'conversion_rate': self._calculate_conversion_rate(reservations)
            }
        except Exception as e:
            print(f"Error calculando estadísticas de reservas: {str(e)}")
            return {}

    def _calculate_financial_stats(self, reservations: List[Dict]) -> Dict:
        """Calcular estadísticas financieras"""
        try:
            total_revenue = 0
            confirmed_revenue = 0
            pending_revenue = 0
            revenue_by_month = defaultdict(float)
            
            for reservation in reservations:
                precio = reservation.get('precio', 0)
                if isinstance(precio, (int, float)):
                    total_revenue += precio
                    
                    status = reservation.get('estado', '')
                    if status == 'Confirmado':
                        confirmed_revenue += precio
                    elif status == 'Pendiente':
                        pending_revenue += precio
                    
                    # Revenue por mes
                    try:
                        fecha_str = reservation.get('fecha_creacion', '')
                        if fecha_str:
                            fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                            month_key = fecha.strftime('%Y-%m')
                            if status == 'Confirmado':
                                revenue_by_month[month_key] += precio
                    except (ValueError, TypeError):
                        continue
            
            return {
                'total_revenue': round(total_revenue, 2),
                'confirmed_revenue': round(confirmed_revenue, 2),
                'pending_revenue': round(pending_revenue, 2),
                'average_ticket_price': round(confirmed_revenue / max(len([r for r in reservations if r.get('estado') == 'Confirmado']), 1), 2),
                'revenue_by_month': dict(revenue_by_month)
            }
        except Exception as e:
            print(f"Error calculando estadísticas financieras: {str(e)}")
            return {}

    def _calculate_occupancy_stats(self, flights: List[Dict], reservations: List[Dict]) -> Dict:
        """Calcular estadísticas de ocupación"""
        try:
            total_seats = 0
            occupied_seats = 0
            occupancy_by_flight = {}
            
            # Mapear reservas por número de vuelo
            reservations_by_flight = defaultdict(list)
            for reservation in reservations:
                if reservation.get('estado') == 'Confirmado':
                    flight_number = reservation.get('vuelo', {}).get('numero_vuelo')
                    if flight_number:
                        reservations_by_flight[flight_number].append(reservation)
            
            for flight in flights:
                if not flight.get('activo', True):
                    continue
                    
                flight_number = flight.get('numero_vuelo')
                available_seats = flight.get('asientos_disponibles', [])
                
                # Calcular asientos totales basado en clase
                flight_total_seats = self._get_total_seats_by_class(flight.get('clase', 'Económica'))
                flight_occupied_seats = len(reservations_by_flight.get(flight_number, []))
                
                total_seats += flight_total_seats
                occupied_seats += flight_occupied_seats
                
                if flight_total_seats > 0:
                    flight_occupancy = (flight_occupied_seats / flight_total_seats) * 100
                    occupancy_by_flight[flight_number] = round(flight_occupancy, 2)
            
            overall_occupancy = (occupied_seats / max(total_seats, 1)) * 100
            
            return {
                'occupancy_rate': round(overall_occupancy, 2),
                'total_seats': total_seats,
                'occupied_seats': occupied_seats,
                'available_seats': total_seats - occupied_seats,
                'occupancy_by_flight': occupancy_by_flight,
                'high_occupancy_flights': len([occ for occ in occupancy_by_flight.values() if occ >= 80]),
                'low_occupancy_flights': len([occ for occ in occupancy_by_flight.values() if occ < 50])
            }
        except Exception as e:
            print(f"Error calculando estadísticas de ocupación: {str(e)}")
            return {}

    def _calculate_trend_stats(self, flights: List[Dict], reservations: List[Dict]) -> Dict:
        """Calcular estadísticas de tendencias (últimos 30 días)"""
        try:
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            recent_flights = []
            recent_reservations = []
            daily_reservations = defaultdict(int)
            
            for flight in flights:
                try:
                    created_str = flight.get('fecha_creacion', '')
                    if created_str:
                        created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        if created_date >= thirty_days_ago:
                            recent_flights.append(flight)
                except (ValueError, TypeError):
                    continue
            
            for reservation in reservations:
                try:
                    created_str = reservation.get('fecha_creacion', '')
                    if created_str:
                        created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        if created_date >= thirty_days_ago:
                            recent_reservations.append(reservation)
                            day_key = created_date.strftime('%Y-%m-%d')
                            daily_reservations[day_key] += 1
                except (ValueError, TypeError):
                    continue
            
            return {
                'flights_last_30_days': len(recent_flights),
                'reservations_last_30_days': len(recent_reservations),
                'daily_reservations_trend': dict(daily_reservations),
                'growth_rate': self._calculate_growth_rate(recent_reservations)
            }
        except Exception as e:
            print(f"Error calculando estadísticas de tendencias: {str(e)}")
            return {}

    # ==================== MÉTODOS AUXILIARES ====================

    def _count_flights_this_week(self, flights: List[Dict]) -> int:
        """Contar vuelos de esta semana"""
        try:
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            count = 0
            for flight in flights:
                try:
                    flight_date_str = flight.get('fecha', '')
                    if flight_date_str:
                        flight_date = datetime.strptime(flight_date_str, '%Y-%m-%d').date()
                        if start_of_week <= flight_date <= end_of_week:
                            count += 1
                except ValueError:
                    continue
            
            return count
        except Exception:
            return 0

    def _calculate_conversion_rate(self, reservations: List[Dict]) -> float:
        """Calcular tasa de conversión de reservas"""
        try:
            if not reservations:
                return 0.0
            
            confirmed = len([r for r in reservations if r.get('estado') == 'Confirmado'])
            total = len(reservations)
            
            return round((confirmed / total) * 100, 2) if total > 0 else 0.0
        except Exception:
            return 0.0

    def _get_total_seats_by_class(self, flight_class: str) -> int:
        """Obtener número total de asientos por clase"""
        class_seats = {
            'primera': 16,    # 4 filas × 4 asientos
            'ejecutiva': 32,  # 8 filas × 4 asientos
            'económica': 120  # 20 filas × 6 asientos
        }
        return class_seats.get(flight_class.lower(), 120)

    def _calculate_growth_rate(self, recent_reservations: List[Dict]) -> float:
        """Calcular tasa de crecimiento semanal"""
        try:
            if len(recent_reservations) < 14:
                return 0.0
            
            # Dividir en dos semanas
            two_weeks_ago = datetime.now() - timedelta(days=14)
            one_week_ago = datetime.now() - timedelta(days=7)
            
            first_week = 0
            second_week = 0
            
            for reservation in recent_reservations:
                try:
                    created_str = reservation.get('fecha_creacion', '')
                    if created_str:
                        created_date = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        if two_weeks_ago <= created_date < one_week_ago:
                            first_week += 1
                        elif created_date >= one_week_ago:
                            second_week += 1
                except (ValueError, TypeError):
                    continue
            
            if first_week == 0:
                return 100.0 if second_week > 0 else 0.0
            
            growth_rate = ((second_week - first_week) / first_week) * 100
            return round(growth_rate, 2)
        except Exception:
            return 0.0

    def get_detailed_flight_stats(self, flight_id: str) -> Dict:
        """Obtener estadísticas detalladas de un vuelo específico"""
        try:
            flight = self.get_flight_by_id(flight_id)
            if not flight:
                return {'error': 'Vuelo no encontrado'}
            
            # Obtener reservas para este vuelo
            reservations_data = self.get_all_reservations()
            flight_reservations = []
            
            if reservations_data:
                for reservation_id, reservation_data in reservations_data.items():
                    if isinstance(reservation_data, dict):
                        vuelo_info = reservation_data.get('vuelo', {})
                        if vuelo_info.get('numero_vuelo') == flight.get('numero_vuelo'):
                            reservation_data['id'] = reservation_id
                            flight_reservations.append(reservation_data)
            
            # Calcular estadísticas específicas
            total_seats = self._get_total_seats_by_class(flight.get('clase', 'Económica'))
            occupied_seats = len([r for r in flight_reservations if r.get('estado') == 'Confirmado'])
            revenue = sum(r.get('precio', 0) for r in flight_reservations if r.get('estado') == 'Confirmado')
            
            return {
                'flight_info': flight,
                'total_seats': total_seats,
                'occupied_seats': occupied_seats,
                'available_seats': total_seats - occupied_seats,
                'occupancy_rate': round((occupied_seats / total_seats) * 100, 2),
                'total_reservations': len(flight_reservations),
                'confirmed_reservations': len([r for r in flight_reservations if r.get('estado') == 'Confirmado']),
                'pending_reservations': len([r for r in flight_reservations if r.get('estado') == 'Pendiente']),
                'revenue': round(revenue, 2),
                'average_price': round(revenue / max(occupied_seats, 1), 2),
                'reservations': flight_reservations
            }
            
        except Exception as e:
            return {'error': str(e)}

    def create_flight(self, flight_data: Dict) -> Optional[Dict]:
        try:
            ref = self.db.reference('vuelos_programados')
            new_ref = ref.push(flight_data)
            return {"id": new_ref.key, **flight_data}
        except Exception as e:
            print(f"Error creando vuelo: {str(e)}")
            return None

    def search_flights(self, origen: str, destino: str, fecha: str) -> list:
        """Buscar vuelos por origen, destino y fecha"""
        try:
            ref = self.db.reference('vuelos_programados')
            snapshot = ref.order_by_child('fecha').equal_to(fecha).get()
            
            # Filtrar por origen y destino también
            vuelos_filtrados = []
            if snapshot:
                for flight_id, vuelo in snapshot.items():
                    if vuelo.get('origen') == origen and vuelo.get('destino') == destino:
                        vuelo['id'] = flight_id
                        vuelos_filtrados.append(vuelo)

            return vuelos_filtrados
        except Exception as e:
            print(f"Error en búsqueda de vuelos: {str(e)}")
            return []

    def update_flight(self, flight_id: str, data: Dict[str, Any]) -> bool:
        """Actualizar un vuelo existente"""
        try:
            ref = self.db.reference(f'vuelos_programados/{flight_id}')
            ref.update(data)
            return True
        except Exception as e:
            print(f"Error actualizando vuelo {flight_id}: {str(e)}")
            return False

    def delete_flight(self, flight_id: str) -> bool:
        """Eliminar un vuelo"""
        try:
            ref = self.db.reference(f'vuelos_programados/{flight_id}')
            ref.delete()
            return True
        except Exception as e:
            print(f"Error eliminando vuelo {flight_id}: {str(e)}")
            return False

    def create_reservation(self, codigo_ticket: str, reservation_data: dict, flight_id: str, asiento: str) -> bool:
        """Crear ticket y actualizar asientos disponibles del vuelo"""
        try:
            # Guardar la reserva (ticket)
            ref_ticket = self.db.reference(f'tickets/{codigo_ticket}')
            ref_ticket.set(reservation_data)

            # Eliminar asiento reservado de la lista disponible
            ref_asientos = self.db.reference(f'vuelos_programados/{flight_id}/asientos_disponibles')
            asientos_actuales = ref_asientos.get()

            if asiento in asientos_actuales:
                asientos_actuales.remove(asiento)
                ref_asientos.set(asientos_actuales)
            else:
                print(f"⚠️ El asiento {asiento} no estaba disponible")

            print(f"✅ Reserva creada: {codigo_ticket}")
            return True

        except Exception as e:
            print(f"❌ Error creando reserva en FirebaseService: {str(e)}")
            return False

    def get_reservation(self, ticket_code: str) -> Optional[Dict]:
        try:
            ref = self.db.reference(f'tickets/{ticket_code}')
            return ref.get()
        except Exception as e:
            print(f"Error al obtener reserva: {str(e)}")
            return None

    def health_check(self) -> Dict:
        """Verificar estado de la conexión con Firebase"""
        try:
            ref = self.db.reference('health_check')
            ref.set({
                'timestamp': datetime.now().isoformat(),
                'status': 'OK'
            })
            
            test_data = ref.get()
            
            return {
                'status': 'OK',
                'timestamp': datetime.now().isoformat(),
                'database_url': os.getenv('FIREBASE_DATABASE_URL', 'Not configured'),
                'connection': 'Active',
                'read_test': 'Passed' if test_data else 'Failed',
                'write_test': 'Passed'
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'connection': 'Failed'
            }