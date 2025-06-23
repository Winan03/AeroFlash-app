// admin.js - Panel Administrativo AeroFlash - VERSIÓN CORREGIDA

// Variables globales
let vuelosData = {};
let reservasData = {};
let editingFlightId = null;

// Configuración de la API
const API_BASE_URL = '/api';

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM cargado, iniciando carga de reservas...');
    initializeEventListeners();
    // Cargar datos con manejo de errores mejorado
    loadDashboardData();
    loadFlights();
    loadReservations();
});

function initializeReservationsSection() {
    console.log('🚀 Inicializando sección de reservas...');
    
    // Verificar que exista la tabla
    const table = document.querySelector('#reservations-table');
    if (!table) {
        console.error('❌ Tabla de reservas no encontrada en el DOM');
        return false;
    }
    
    // Cargar datos iniciales
    loadReservations();
    
    return true;
}

// Event Listeners
function initializeEventListeners() {
    // Formulario de vuelo
    const flightForm = document.getElementById('flightForm');
    if (flightForm) {
        flightForm.addEventListener('submit', handleFlightSubmit);
    }
    
    // Prevenir que origen y destino sean iguales
    const origenSelect = document.querySelector('select[name="origen"]');
    const destinoSelect = document.querySelector('select[name="destino"]');
    
    if (origenSelect && destinoSelect) {
        origenSelect.addEventListener('change', function() {
            updateDestinationOptions(this.value, destinoSelect);
        });
        
        destinoSelect.addEventListener('change', function() {
            updateOriginOptions(this.value, origenSelect);
        });
    }

    // Event listeners para modals
    const flightModal = document.getElementById('flightModal');
    if (flightModal) {
        flightModal.addEventListener('show.bs.modal', function() {
            if (!editingFlightId) {
                const modalTitle = document.querySelector('#flightModal .modal-title');
                if (modalTitle) modalTitle.textContent = 'Crear Nuevo Vuelo';
                
                const numeroVueloInput = document.getElementById('flightForm')?.numero_vuelo;
                if (numeroVueloInput) numeroVueloInput.readOnly = false;
            }
        });

        flightModal.addEventListener('hidden.bs.modal', function() {
            editingFlightId = null;
            const form = document.getElementById('flightForm');
            if (form) form.reset();
        });
    }
}

// Función auxiliar para manejo de errores de API
async function handleApiResponse(response) {
    if (!response.ok) {
        let errorMessage = `Error ${response.status}: ${response.statusText}`;
        
        try {
            const errorData = await response.text();
            // Intentar parsear como JSON si es posible
            try {
                const jsonError = JSON.parse(errorData);
                errorMessage = jsonError.message || jsonError.error || errorMessage;
            } catch {
                // Si no es JSON, usar el texto completo si es corto
                if (errorData.length < 200) {
                    errorMessage = errorData;
                }
            }
        } catch {
            // Usar mensaje por defecto
        }
        
        throw new Error(errorMessage);
    }
    
    const text = await response.text();
    if (!text.trim()) {
        throw new Error('Respuesta vacía del servidor');
    }
    
    try {
        return JSON.parse(text);
    } catch (e) {
        console.error('Error parsing JSON:', text);
        throw new Error('Respuesta inválida del servidor');
    }
}

// Navegación entre secciones
function showSection(sectionName) {
    // Ocultar todas las secciones
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Mostrar la sección seleccionada
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Actualizar navegación
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Cargar datos específicos de la sección
    if (sectionName === 'reservations') {
        loadReservations();
    } else if (sectionName === 'flights') {
        loadFlights(); // Asegúrate de que esta función exista
    }
}

// Cargar datos del dashboard con mejor manejo de errores
async function loadDashboardData() {
    try {
        console.log('🔄 Cargando datos del dashboard...');
        
        // Mostrar indicador de carga
        showLoadingIndicator();
        
        const response = await fetch(`${API_BASE_URL}/dashboard-stats`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.stats) {
            updateDashboardStats(data.stats);
            
            // Si hay vuelos, mostrarlos también
            if (data.flights && data.flights.length > 0) {
                displayRecentFlights(data.flights);
            }
            
            console.log('📊 Datos del dashboard cargados exitosamente');
            showNotification('Dashboard actualizado correctamente', 'success');
        } else {
            throw new Error(data.error || 'Error al obtener estadísticas');
        }
        
    } catch (error) {
        console.error('❌ Error al cargar datos del dashboard:', error);
        showNotification(`Error al cargar estadísticas: ${error.message}`, 'error');
        
        // Mostrar datos por defecto en caso de error
        updateDashboardStats({
            total_flights: 0,
            total_reservations: 0,
            confirmed_reservations: 0,
            pending_reservations: 0,
            cancelled_reservations: 0,
            total_revenue: 0,
            average_price: 0
        });
    } finally {
        hideLoadingIndicator();
    }
}

function showLoadingIndicator() {
    const indicators = document.querySelectorAll('.stat-value');
    indicators.forEach(indicator => {
        indicator.innerHTML = '<div class="animate-pulse bg-gray-200 h-4 rounded"></div>';
    });
}

function hideLoadingIndicator() {
    // Se oculta automáticamente cuando se actualizan los valores
}

function displayRecentFlights(flights) {
    const container = document.getElementById('recent-flights-container');
    if (!container) return;
    
    if (flights.length === 0) {
        container.innerHTML = '<p class="text-gray-500">No hay vuelos registrados</p>';
        return;
    }
    
    let flightsHtml = '<h3 class="text-lg font-semibold mb-3">Vuelos Recientes</h3>';
    flightsHtml += '<div class="space-y-2">';
    
    flights.forEach(flight => {
        const statusClass = getFlightStatusClass(flight.fecha);
        flightsHtml += `
            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                    <span class="font-medium">${flight.numero_vuelo || 'N/A'}</span>
                    <span class="text-sm text-gray-600 ml-2">${flight.origen || 'N/A'} → ${flight.destino || 'N/A'}</span>
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium">${flight.fecha || 'N/A'}</div>
                    <div class="text-xs text-gray-500">${flight.horario || 'N/A'}</div>
                    <span class="inline-block px-2 py-1 text-xs rounded-full ${statusClass}">
                        ${getFlightStatusText(flight.fecha)}
                    </span>
                </div>
            </div>
        `;
    });
    
    flightsHtml += '</div>';
    container.innerHTML = flightsHtml;
}

function getFlightStatusClass(flightDate) {
    if (!flightDate) return 'bg-gray-100 text-gray-600';
    
    try {
        const flight = new Date(flightDate.split('/').reverse().join('-'));
        const today = new Date();
        const diffDays = Math.ceil((flight - today) / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) return 'bg-red-100 text-red-600'; // Pasado
        if (diffDays === 0) return 'bg-green-100 text-green-600'; // Hoy
        if (diffDays <= 7) return 'bg-yellow-100 text-yellow-600'; // Próximo
        return 'bg-blue-100 text-blue-600'; // Futuro
    } catch {
        return 'bg-gray-100 text-gray-600';
    }
}

// Obtener texto del estado del vuelo
function getFlightStatusText(flightDate) {
    if (!flightDate) return 'Sin fecha';
    
    try {
        const flight = new Date(flightDate.split('/').reverse().join('-'));
        const today = new Date();
        const diffDays = Math.ceil((flight - today) / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) return 'Pasado';
        if (diffDays === 0) return 'Hoy';
        if (diffDays <= 7) return 'Próximo';
        return 'Programado';
    } catch {
        return 'Sin fecha';
    }
}

// Cargar vuelos con mejor manejo de errores
async function loadFlights() {
    try {
        const response = await fetch(`${API_BASE_URL}/flights`);
        const data = await handleApiResponse(response);
        
        if (data.success) {
            vuelosData = {};
            (data.flights || []).forEach(flight => {
                if (flight.id) {
                    vuelosData[flight.id] = flight;
                }
            });

            renderFlightsTable();
        } else {
            throw new Error(data.message || 'Error al obtener vuelos');
        }
    } catch (error) {
        console.error('Error al cargar vuelos:', error);
        showNotification(`Error al cargar vuelos: ${error.message}`, 'error');
        
        // Mostrar tabla vacía
        vuelosData = {};
        renderFlightsTable();
    }
}

// Renderizar tabla de vuelos
function renderFlightsTable() {
    const tbody = document.querySelector('#flights-table tbody');
    if (!tbody) {
        console.error('No se encontró la tabla de vuelos');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (Object.keys(vuelosData).length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No hay vuelos registrados</td></tr>';
        return;
    }
    
    Object.entries(vuelosData).forEach(([flightId, flight]) => {
        const row = document.createElement('tr');
        
        // Calcular asientos disponibles de forma segura
        const disponibles = Array.isArray(flight.asientos_disponibles) 
            ? flight.asientos_disponibles.length 
            : 0;

        const total = flight.total_asientos || (flight.asientos_totales ?? 0); // Ajusta según cómo guardas los totales
        const totalAsientos = total || (Array.isArray(flight.asientos_disponibles) ? disponibles : 0); // fallback

        const textoAsientos = `${disponibles} / ${totalAsientos}`;
        
        row.innerHTML = `
            <td>${escapeHtml(flight.numero_vuelo || flightId)}</td>
            <td>${escapeHtml(flight.origen || '')}</td>
            <td>${escapeHtml(flight.destino || '')}</td>
            <td>${formatDate(flight.fecha)}</td>
            <td>${escapeHtml(flight.hora_partida || '')} - ${escapeHtml(flight.hora_llegada || '')}</td>
            <td>S/ ${parseFloat(flight.precio || 0).toFixed(2)}</td>
            <td>${textoAsientos}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editFlight('${escapeHtml(flightId)}')" title="Editar">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteFlight('${escapeHtml(flightId)}')" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Manejar envío del formulario de vuelo - VERSIÓN CORREGIDA CON CAMPO FECHA
async function handleFlightSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    // Validar campos requeridos
    const requiredFields = ['numero_vuelo', 'origen', 'destino', 'fecha', 'hora_salida', 'precio', 'duracion'];
    for (const field of requiredFields) {
        const value = formData.get(field);
        if (!value || value.toString().trim() === '') {
            showNotification(`El campo ${field.replace('_', ' ')} es requerido`, 'error');
            return;
        }
    }
    
    // Validación específica del precio
    const precioValue = formData.get('precio');
    const precioNumerico = parseFloat(precioValue);
    
    if (isNaN(precioNumerico) || precioNumerico <= 0) {
        showNotification('El precio debe ser un número mayor a 0', 'error');
        return;
    }
    
    const duracion = formData.get('duracion') || '1h 30m';

    let rawDate = formData.get('fecha');  // Puede venir como dd/mm/yyyy o yyyy-mm-dd
    let formattedDate = rawDate;

    // Verificar si viene como dd/mm/yyyy
    if (rawDate.includes('/')) {
        const [dd, mm, yyyy] = rawDate.split('/');
        formattedDate = `${yyyy}-${mm}-${dd}`;
    }

    const flightData = {
        numero_vuelo: formData.get('numero_vuelo').trim(),
        aerolinea: formData.get('aerolinea') || 'AeroFlash',
        origen: formData.get('origen').toLowerCase().trim(),
        destino: formData.get('destino').toLowerCase().trim(),
        fecha: formattedDate, // ✅ CAMBIO CLAVE: usar 'fecha' en lugar de 'fecha_vuelo'
        hora_partida: formData.get('hora_salida').trim(),
        duracion: duracion,
        hora_llegada: calculateArrivalTime(formData.get('hora_salida'), duracion),
        clase: formData.get('clase') || 'Economica',
        precio: precioNumerico,
        puerta: generateGate(),
        tipo_avion: formData.get('tipo_avion') || 'Boeing 737',
        asientos_disponibles: generateSeats(formData.get('clase') || 'Economica')
    };
    
    // Validaciones adicionales
    if (flightData.origen === flightData.destino) {
        showNotification('El origen y destino no pueden ser iguales', 'error');
        return;
    }
    
    if (new Date(flightData.fecha) < new Date().setHours(0,0,0,0)) {
        showNotification('La fecha del vuelo no puede ser anterior a hoy', 'error');
        return;
    }
    
    // Log para debugging - REMOVER EN PRODUCCIÓN
    console.log('Datos del vuelo a enviar:', flightData);
    
    try {
        const url = editingFlightId ? 
            `${API_BASE_URL}/flights/${editingFlightId}` : 
            `${API_BASE_URL}/flights`;
        
        const method = editingFlightId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(flightData)
        });
        
        const result = await handleApiResponse(response);
        
        if (result.success) {
            // ✅ Agregar el nuevo vuelo directo a vuelosData
            if (!editingFlightId && result.flight && result.flight.id) {
                vuelosData[result.flight.id] = result.flight;
            }
            showNotification(
                editingFlightId ? 'Vuelo actualizado exitosamente' : 'Vuelo creado exitosamente', 
                'success'
            );
            
            // Cerrar modal y resetear formulario
            const modal = bootstrap.Modal.getInstance(document.getElementById('flightModal'));
            if (modal) modal.hide();
            
            document.getElementById('flightForm').reset();
            editingFlightId = null;
            
            // Recargar datos
            loadFlights();
            loadDashboardData();
        } else {
            throw new Error(result.message || result.error || 'Error al guardar vuelo');
        }
    } catch (error) {
        console.error('Error completo:', error);
        showNotification(`Error al guardar vuelo: ${error.message}`, 'error');
    }
}

// Editar vuelo
function editFlight(flightId) {
    const flight = vuelosData[flightId];
    if (!flight) {
        showNotification('Vuelo no encontrado', 'error');
        return;
    }

    editingFlightId = flightId;

    const form = document.getElementById('flightForm');
    if (!form) return;

    // Asegurar formato correcto de la fecha (yyyy-mm-dd)
    let fechaFormateada = flight.fecha;
    if (fechaFormateada && fechaFormateada.includes('/')) {
        const [dd, mm, yyyy] = fechaFormateada.split('/');
        fechaFormateada = `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
    }

    const fields = {
        'numero_vuelo': flight.numero_vuelo,
        'aerolinea': flight.aerolinea || 'AeroFlash',
        'origen': capitalizeFirst(flight.origen || ''),
        'destino': capitalizeFirst(flight.destino || ''),
        'fecha': fechaFormateada || '',
        'hora_salida': flight.hora_partida || '',
        'duracion': calculateDuration(flight.hora_partida, flight.hora_llegada),
        'clase': flight.clase || 'Economica',
        'precio': flight.precio || '',
        'tipo_avion': flight.tipo_avion || 'Boeing 737'
    };

    Object.entries(fields).forEach(([fieldName, value]) => {
        const field = form[fieldName];
        if (field) {
            field.value = value;
            if (fieldName === 'numero_vuelo') {
                field.readOnly = true;
            }
        }
    });

    const modalTitle = document.querySelector('#flightModal .modal-title');
    if (modalTitle) modalTitle.textContent = 'Editar Vuelo';

    const modal = new bootstrap.Modal(document.getElementById('flightModal'));
    modal.show();
}

// Eliminar vuelo
async function deleteFlight(flightId) {
    if (!confirm(`¿Está seguro de que desea eliminar el vuelo ${flightId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/flights/${flightId}`, {
            method: 'DELETE'
        });
        
        const result = await handleApiResponse(response);
        
        if (result.success) {
            showNotification('Vuelo eliminado exitosamente', 'success');
            loadFlights();
            loadDashboardData();
        } else {
            throw new Error(result.message || 'Error al eliminar vuelo');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(`Error al eliminar vuelo: ${error.message}`, 'error');
    }
}

async function loadReservations() {
    try {
        console.log('🔄 Iniciando carga de reservas...');
        showLoadingState();

        const response = await fetch(`${API_BASE_URL}/tickets`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });

        console.log('📡 Estado de respuesta:', response.status);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('No autorizado. Por favor, inicia sesión como administrador.');
            }
            throw new Error(`Error HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📦 Datos recibidos del servidor:', data);

        if (data.success) {
            const firebaseTickets = data.tickets || {};

            if (Object.keys(firebaseTickets).length === 0) {
                console.log('📝 No hay tickets registrados');
                reservasData = [];
                renderReservationsTable();
                showNotification('No hay reservas registradas en el sistema', 'info');
                return;
            }

            reservasData = Object.entries(firebaseTickets).map(([ticketId, ticket]) => {
                const pasajero = ticket.pasajero || {};
                const vuelo = ticket.vuelo || {};

                return {
                    id: ticketId,
                    ticket_code: ticket.codigo_ticket || ticketId,
                    nombre_pasajero: pasajero.nombre_completo || 'N/A',
                    email: pasajero.correo || 'N/A',
                    telefono: pasajero.telefono || 'N/A',
                    dni: pasajero.dni || 'N/A',
                    numero_vuelo: vuelo.numero_vuelo || 'N/A',
                    fecha: vuelo.fecha || 'N/A',
                    asiento: vuelo.asiento || 'N/A',
                    origen: vuelo.origen || 'N/A',
                    destino: vuelo.destino || 'N/A',
                    hora_partida: vuelo.hora_partida || 'N/A',
                    hora_llegada: vuelo.hora_llegada || 'N/A',
                    aerolinea: vuelo.aerolinea || 'AeroFlash',
                    clase: vuelo.clase || 'Económica',
                    puerta: vuelo.puerta || 'N/A',
                    estado: ticket.estado || 'Confirmado',
                    precio: ticket.precio || 0,
                    fecha_reserva: ticket.fecha_reserva || 'N/A'
                };
            });

            console.log(`🎫 ${reservasData.length} reservas procesadas exitosamente`);
            renderReservationsTable();
            updateReservationsStats();
            showNotification(`${reservasData.length} reservas cargadas exitosamente`, 'success');

            // 🟢 ✅ AÑADIR ESTA LÍNEA para actualizar los asientos disponibles
            await loadFlights();

        } else {
            throw new Error(data.error || data.message || 'Error desconocido al obtener reservas');
        }

    } catch (error) {
        console.error('❌ Error al cargar reservas:', error);
        showNotification(`Error al cargar reservas: ${error.message}`, 'error');
        reservasData = [];
        renderReservationsTable();
    }
}


function updateReservationsStats() {
    const totalReservationsElement = document.getElementById('total-reservations');
    if (totalReservationsElement) {
        totalReservationsElement.textContent = reservasData.length;
    }
    
    const totalRevenueElement = document.getElementById('total-revenue');
    if (totalRevenueElement) {
        const totalRevenue = reservasData.reduce((sum, reserva) => 
            sum + parseFloat(reserva.precio || 0), 0
        );
        totalRevenueElement.textContent = `S/ ${totalRevenue.toFixed(2)}`;
    }
}

function showLoadingState() {
    const tableBody = document.querySelector('#reservations-table tbody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <div class="d-flex justify-content-center align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Cargando...</span>
                        </div>
                        <span>Cargando reservas...</span>
                    </div>
                </td>
            </tr>
        `;
    }
}

async function loadReservationsAlternative() {
    try {
        console.log('🔄 Intentando cargar reservas con endpoint alternativo...');
        
        const response = await fetch(`${API_BASE_URL}/reservations`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const reservations = data.reservations || {};
            
            if (Object.keys(reservations).length === 0) {
                console.log('📝 No hay reservas registradas');
                reservasData = [];
                renderReservationsTable();
                return;
            }
            
            // Convertir reservas a formato esperado
            reservasData = Object.keys(reservations).map(reservationId => {
                const reservation = reservations[reservationId];
                
                return {
                    id: reservationId,
                    reservation_id: reservation.codigo_ticket || reservationId,
                    nombre_pasajero: reservation.pasajero?.nombre_completo || 'N/A',
                    email: reservation.pasajero?.correo || 'N/A',
                    telefono: reservation.pasajero?.telefono || 'N/A',
                    dni: reservation.pasajero?.dni || 'N/A',
                    numero_vuelo: reservation.vuelo?.numero_vuelo || 'N/A',
                    fecha: reservation.vuelo?.fecha || 'N/A',
                    asiento: reservation.vuelo?.asiento || 'N/A',
                    estado: reservation.estado || 'Confirmado',
                    precio: reservation.precio || 0,
                    fecha_reserva: reservation.fecha_reserva || 'N/A',
                    origen: reservation.vuelo?.origen || 'N/A',
                    destino: reservation.vuelo?.destino || 'N/A',
                    aerolinea: reservation.vuelo?.aerolinea || 'AeroFlash',
                    clase: reservation.vuelo?.clase || 'Económica',
                    hora_partida: reservation.vuelo?.hora_partida || 'N/A',
                    hora_llegada: reservation.vuelo?.hora_llegada || 'N/A',
                    puerta: reservation.vuelo?.puerta || 'N/A'
                };
            });
            
            console.log('🎫 Reservas cargadas exitosamente:', reservasData.length);
            renderReservationsTable();
        }
        
    } catch (error) {
        console.error('❌ Error en método alternativo:', error);
        throw error;
    }
}

// ✅ FUNCIÓN PARA RENDERIZAR LA TABLA (asegúrate de que existe)
function renderReservationsTable() {
    // ✅ SELECTOR CORREGIDO - USAR EL ID EXACTO DEL HTML
    const tableBody = document.querySelector('#reservations-table tbody');
    
    if (!tableBody) {
        console.error('❌ No se encontró #reservations-table tbody');
        console.log('🔍 Elementos de tabla encontrados:', 
            document.querySelectorAll('table[id*="reservation"], table[id*="reserva"]'));
        return;
    }
    
    console.log('✅ Elemento tbody encontrado, renderizando tabla...');
    
    if (reservasData.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted py-4">
                    <div class="d-flex flex-column align-items-center">
                        <i class="fas fa-inbox fa-3x mb-3 text-secondary"></i>
                        <h5>No hay reservas registradas</h5>
                        <p class="mb-0">Las reservas aparecerán aquí cuando los usuarios hagan sus reservas.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = reservasData.map(reserva => `
        <tr class="align-middle">
            <td class="fw-bold text-primary">${reserva.ticket_code}</td>
            <td>
                <div>
                    <div class="fw-semibold">${reserva.nombre_pasajero}</div>
                    <small class="text-muted">${reserva.email}</small>
                </div>
            </td>
            <td>
                <div class="fw-semibold">${reserva.numero_vuelo}</div>
                <small class="text-muted">${reserva.origen} → ${reserva.destino}</small>
            </td>
            <td>
                <div>${reserva.fecha}</div>
                <small class="text-muted">${reserva.hora_partida}</small>
            </td>
            <td class="text-center">
                <span class="badge bg-secondary">${reserva.asiento}</span>
            </td>
            <td>
                <span class="badge ${getStatusBadgeClass(reserva.estado)}">
                    ${reserva.estado}
                </span>
            </td>
            <td class="fw-bold">S/ ${parseFloat(reserva.precio || 0).toFixed(2)}</td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary btn-sm" 
                            onclick="viewReservationDetails('${reserva.id}')" 
                            title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger btn-sm" 
                            onclick="cancelReservation('${reserva.id}')" 
                            title="Cancelar reserva">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    console.log(`📊 Tabla renderizada con ${reservasData.length} filas`);
}

// Función para formatear fechas de manera legible
function formatDateTime(dateString) {
    try {
        const date = new Date(dateString);
        
        // Verificar si la fecha es válida
        if (isNaN(date.getTime())) {
            return dateString; // Retornar el string original si no es válida
        }
        
        // Configurar opciones para el formato en español
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        };
        
        // Formatear la fecha en español
        return date.toLocaleDateString('es-ES', options);
    } catch (error) {
        console.error('Error al formatear fecha:', error);
        return dateString; // Retornar el string original en caso de error
    }
}

// Función para formatear solo la fecha (sin hora)
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        
        return date.toLocaleDateString('es-ES', options);
    } catch (error) {
        console.error('Error al formatear fecha:', error);
        return dateString;
    }
}

// Función actualizada para mostrar detalles de reserva
function viewReservationDetails(reservationId) {
    const reserva = reservasData.find(r => r.id === reservationId);
    if (!reserva) {
        showNotification('Reserva no encontrada', 'error');
        return;
    }
    
    // Actualizar el contenido del modal
    document.getElementById('reservation-code').textContent = reserva.ticket_code;
    document.getElementById('passenger-name').textContent = reserva.nombre_pasajero;
    document.getElementById('passenger-dni').textContent = reserva.dni;
    document.getElementById('passenger-email').textContent = reserva.email;
    document.getElementById('passenger-phone').textContent = reserva.telefono;
    
    document.getElementById('flight-origin').textContent = reserva.origen;
    document.getElementById('flight-destination').textContent = reserva.destino;
    document.getElementById('flight-departure').textContent = reserva.hora_partida;
    document.getElementById('flight-arrival').textContent = reserva.hora_llegada;
    document.getElementById('flight-number').textContent = reserva.numero_vuelo;
    
    // Formatear la fecha del vuelo
    document.getElementById('flight-date').textContent = formatDate(reserva.fecha);
    
    document.getElementById('flight-seat').textContent = reserva.asiento;
    document.getElementById('flight-class').textContent = reserva.clase;
    
    document.getElementById('reservation-price').textContent = `S/ ${parseFloat(reserva.precio || 0).toFixed(2)}`;
    
    // Formatear la fecha de reserva con fecha y hora
    document.getElementById('reservation-date').textContent = formatDateTime(reserva.fecha_reserva);
    
    document.getElementById('ticket-code').textContent = reserva.ticket_code;
    
    // Actualizar estado con clase apropiada
    const statusElement = document.getElementById('reservation-status');
    const statusClass = reserva.estado.toLowerCase();
    statusElement.className = `status-badge ${statusClass}`;
    statusElement.innerHTML = `<i class="fas fa-${getStatusIcon(reserva.estado)}"></i> ${reserva.estado}`;
    
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('reservationDetailsModal'));
    modal.show();
}

function getStatusIcon(status) {
    switch(status.toLowerCase()) {
        case 'confirmado': return 'check-circle';
        case 'cancelado': return 'times-circle';
        case 'pendiente': return 'clock';
        default: return 'info-circle';
    }
}

function printTicket(ticketCode) {
    window.open(`/ticket/${ticketCode}`, '_blank');
}

function showReservationModal(reservation) {
    // Crear modal dinámicamente si no existe
    let modal = document.getElementById('reservationDetailModal');
    if (!modal) {
        modal = createReservationModal();
        document.body.appendChild(modal);
    }
    
    // Llenar datos del modal con validación
    const modalContent = modal.querySelector('.modal-body');
    modalContent.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary"><i class="fas fa-ticket-alt"></i> Información de la Reserva</h6>
                <p><strong>Código:</strong> ${escapeHtml(reservation.reservation_id || 'N/A')}</p>
                <p><strong>Estado:</strong> <span class="badge ${getStatusBadgeClass(reservation.estado)}">${escapeHtml(reservation.estado || 'Pendiente')}</span></p>
                <p><strong>Fecha de Reserva:</strong> ${formatDate(reservation.fecha_reserva)}</p>
                <p><strong>Precio Total:</strong> <span class="text-success">S/ ${parseFloat(reservation.precio || 0).toFixed(2)}</span></p>
            </div>
            <div class="col-md-6">
                <h6 class="text-primary"><i class="fas fa-user"></i> Información del Pasajero</h6>
                <p><strong>Nombre:</strong> ${escapeHtml(reservation.nombre_pasajero || 'N/A')}</p>
                <p><strong>DNI:</strong> ${escapeHtml(reservation.dni || 'N/A')}</p>
                <p><strong>Email:</strong> ${escapeHtml(reservation.email || 'N/A')}</p>
                <p><strong>Teléfono:</strong> ${escapeHtml(reservation.telefono || 'N/A')}</p>
            </div>
        </div>
        <hr>
        <div class="row">
            <div class="col-12">
                <h6 class="text-primary"><i class="fas fa-plane"></i> Información del Vuelo</h6>
                <div class="row">
                    <div class="col-md-4">
                        <p><strong>Número de Vuelo:</strong> ${escapeHtml(reservation.numero_vuelo || 'N/A')}</p>
                        <p><strong>Aerolínea:</strong> ${escapeHtml(reservation.aerolinea || 'AeroFlash')}</p>
                        <p><strong>Fecha:</strong> ${formatDate(reservation.fecha)}</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>Origen:</strong> ${capitalizeFirst(reservation.origen || 'N/A')}</p>
                        <p><strong>Destino:</strong> ${capitalizeFirst(reservation.destino || 'N/A')}</p>
                        <p><strong>Clase:</strong> ${escapeHtml(reservation.clase || 'N/A')}</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>Asiento:</strong> ${escapeHtml(reservation.asiento || 'N/A')}</p>
                        <p><strong>Puerta:</strong> ${escapeHtml(reservation.puerta || 'N/A')}</p>
                        <p><strong>Horario:</strong> ${escapeHtml(reservation.hora_partida || 'N/A')} - ${escapeHtml(reservation.hora_llegada || 'N/A')}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Mostrar el modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function createReservationModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'reservationDetailModal';
    modal.setAttribute('tabindex', '-1');
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Detalles de la Reserva</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <!-- Contenido se llena dinámicamente -->
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

// Funciones auxiliares mejoradas
function calculateArrivalTime(departureTime, duration) {
    if (!departureTime || !duration) return '';
    
    try {
        const [depHour, depMin] = departureTime.split(':').map(Number);
        const durationMatch = duration.match(/(\d+)h?\s*(\d+)?m?/);
        
        if (!durationMatch) return '';
        
        const durationHours = parseInt(durationMatch[1]) || 0;
        const durationMinutes = parseInt(durationMatch[2]) || 0;
        
        const totalMinutes = (depHour * 60 + depMin) + (durationHours * 60 + durationMinutes);
        const arrivalHour = Math.floor(totalMinutes / 60) % 24;
        const arrivalMin = totalMinutes % 60;
        
        return `${arrivalHour.toString().padStart(2, '0')}:${arrivalMin.toString().padStart(2, '0')}`;
    } catch (error) {
        console.error('Error calculando hora de llegada:', error);
        return '';
    }
}

function calculateDuration(startTime, endTime) {
    if (!startTime || !endTime) return '1h 30m';
    
    try {
        const [startHour, startMin] = startTime.split(':').map(Number);
        const [endHour, endMin] = endTime.split(':').map(Number);
        
        const startTotalMin = startHour * 60 + startMin;
        const endTotalMin = endHour * 60 + endMin;
        
        let durationMin = endTotalMin - startTotalMin;
        if (durationMin < 0) durationMin += 24 * 60; // Manejar vuelos que cruzan medianoche
        
        const hours = Math.floor(durationMin / 60);
        const minutes = durationMin % 60;
        
        return `${hours}h ${minutes}m`;
    } catch (error) {
        console.error('Error calculando duración:', error);
        return '1h 30m';
    }
}

function generateGate() {
    const letters = ['A', 'B', 'C', 'D'];
    const letter = letters[Math.floor(Math.random() * letters.length)];
    const number = Math.floor(Math.random() * 20) + 1;
    return `${letter}${number}`;
}

function generateSeats(clase) {
    const seats = [];
    let rows, seatsPerRow;
    
    switch(clase) {
        case 'Primera':
            rows = 5;
            seatsPerRow = ['A', 'B'];
            break;
        case 'Ejecutiva':
            rows = 8;
            seatsPerRow = ['A', 'B', 'C', 'D'];
            break;
        default: // Económica
            rows = 25;
            seatsPerRow = ['A', 'B', 'C', 'D', 'E', 'F'];
    }
    
    for (let row = 1; row <= rows; row++) {
        for (let seat of seatsPerRow) {
            seats.push(`${row}${seat}`);
        }
    }
    
    return seats;
}

function updateDestinationOptions(selectedOrigin, destinoSelect) {
    if (!destinoSelect) return;
    
    const currentDestino = destinoSelect.value;
    
    // Habilitar todas las opciones primero
    Array.from(destinoSelect.options).forEach(option => {
        option.disabled = false;
    });
    
    // Deshabilitar la opción seleccionada en origen
    if (selectedOrigin) {
        Array.from(destinoSelect.options).forEach(option => {
            if (option.value === selectedOrigin) {
                option.disabled = true;
                if (option.value === currentDestino) {
                    destinoSelect.value = '';
                }
            }
        });
    }
}

function updateOriginOptions(selectedDestino, origenSelect) {
    if (!origenSelect) return;
    
    const currentOrigen = origenSelect.value;
    
    // Habilitar todas las opciones primero
    Array.from(origenSelect.options).forEach(option => {
        option.disabled = false;
    });
    
    // Deshabilitar la opción seleccionada en destino
    if (selectedDestino) {
        Array.from(origenSelect.options).forEach(option => {
            if (option.value === selectedDestino) {
                option.disabled = true;
                if (option.value === currentOrigen) {
                    origenSelect.value = '';
                }
            }
        });
    }
}

function formatDate(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        
        return date.toLocaleDateString('es-PE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (error) {
        return dateString;
    }
}

function capitalizeFirst(str) {
    if (typeof str !== 'string') return str;
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

// Función auxiliar para colores de estado
function getStatusBadgeClass(estado) {
    const statusLower = estado.toLowerCase();
    switch(statusLower) {
        case 'confirmado':
        case 'confirmada':
            return 'bg-success';
        case 'cancelado':
        case 'cancelada':
            return 'bg-danger';
        case 'pendiente':
            return 'bg-warning text-dark';
        case 'en proceso':
            return 'bg-info text-dark';
        default:
            return 'bg-secondary';
    }
}


function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Función de utilidad para mostrar notificaciones
function showNotification(message, type = 'info') {
    // Crear elemento de notificación si no existe
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.className = 'fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full';
        document.body.appendChild(notification);
    }
    
    // Configurar estilos según el tipo
    const typeClasses = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };
    
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 ${typeClasses[type] || typeClasses.info}`;
    notification.textContent = message;
    notification.style.transform = 'translateX(0)';
    
    // Ocultar después de 3 segundos
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
    }, 3000);
}

// Función de logout
function logout() {
    if (confirm('¿Deseas cerrar sesión?')) {
        window.location.href = '/logout';
    }
}

// Función para ver detalles de reserva
function viewReservation(reservationIndex) {
    if (!Array.isArray(reservasData) || reservationIndex < 0 || reservationIndex >= reservasData.length) {
        showNotification('Reserva no encontrada', 'error');
        return;
    }
    
    const reservation = reservasData[reservationIndex];
    showReservationModal(reservation);
}

// Función para cancelar reserva
async function cancelReservation(reservationId) {
    const reserva = reservasData.find(r => r.id === reservationId);
    if (!reserva) {
        showNotification('Reserva no encontrada', 'error');
        return;
    }
    
    if (!confirm(`¿Estás seguro de que deseas cancelar la reserva ${reserva.ticket_code}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/cancel_reservation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reservation_id: reservationId
            })
        });
        
        if (response.ok) {
            showNotification('Reserva cancelada exitosamente', 'success');
            loadReservations(); // Recargar la lista
        } else {
            throw new Error('Error al cancelar la reserva');
        }
        
    } catch (error) {
        console.error('Error cancelando reserva:', error);
        showNotification('Error al cancelar la reserva', 'error');
    }
}

// Cargar datos del dashboard
async function loadDashboardData() {
    try {
        console.log('🔄 Cargando datos del dashboard...');
        
        const response = await fetch(`${API_BASE_URL}/dashboard-stats`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.stats) {
            updateDashboardStats(data.stats);
            console.log('📊 Datos del dashboard cargados exitosamente');
        } else {
            throw new Error(data.error || 'Error al obtener estadísticas');
        }
        
    } catch (error) {
        console.error('❌ Error al cargar datos del dashboard:', error);
        showNotification(`Error al cargar estadísticas: ${error.message}`, 'error');
    }
}

// Actualizar estadísticas del dashboard
function updateDashboardStats(stats) {
    // Actualizar contadores principales
    updateStatCard('total-flights', stats.total_flights || 0);
    updateStatCard('total-reservations', stats.total_reservations || 0);
    updateStatCard('confirmed-reservations', stats.confirmed_reservations || 0);
    updateStatCard('pending-reservations', stats.pending_reservations || 0);
    updateStatCard('cancelled-reservations', stats.cancelled_reservations || 0);
    updateStatCard('total-revenue', `S/ ${(stats.total_revenue || 0).toFixed(2)}`);
    updateStatCard('average-price', `S/ ${(stats.average_price || 0).toFixed(2)}`);
    updateStatCard('flights-today', stats.flights_today || 0);
    updateStatCard('upcoming-flights', stats.upcoming_flights || 0);
    
    // Actualizar elementos específicos del dashboard si existen
    const elements = {
        'total-vuelos': stats.total_flights || 0,
        'total-reservas': stats.total_reservations || 0,
        'vuelos-proximos': stats.upcoming_flights || 0,
        'ingresos-total': `S/ ${(stats.total_revenue || 0).toFixed(2)}`
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    console.log('📈 Estadísticas actualizadas:', stats);
}

function startDashboardAutoRefresh() {
    setInterval(() => {
        console.log('🔄 Auto-actualizando dashboard...');
        loadDashboardData();
    }, 5 * 60 * 1000); // 5 minutos
}

// Actualizar una tarjeta de estadística
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
        
        // Añadir animación sutil
        element.style.transform = 'scale(1.05)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }
}


async function checkApiEndpoints() {
    const endpoints = [
        `${API_BASE_URL}/tickets`,
        `${API_BASE_URL}/flights`,
        `${API_BASE_URL}/dashboard-stats`
    ];
    
    console.log('🔍 Verificando endpoints de la API...');
    
    for (const endpoint of endpoints) {
        try {
            const response = await fetch(endpoint, {
                method: 'HEAD' // Solo verificar si existe
            });
            console.log(`✅ ${endpoint}: ${response.status}`);
        } catch (error) {
            console.log(`❌ ${endpoint}: Error - ${error.message}`);
        }
    }
}

// Cargar reportes (placeholder para futuras implementaciones)
function loadReports() {
    console.log('Cargando reportes...');
    // TODO: Implementar gráficos con Chart.js
    showNotification('Función de reportes en desarrollo', 'info');
}

// Búsqueda en tiempo real para reservas
function searchReservations() {
    const searchInput = document.getElementById('search-reservations');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    if (!searchTerm) {
        renderReservationsTable();
        return;
    }
    
    const filteredReservations = reservasData.filter(reservation => {
        return (
            reservation.reservation_id?.toLowerCase().includes(searchTerm) ||
            reservation.nombre_pasajero?.toLowerCase().includes(searchTerm) ||
            reservation.numero_vuelo?.toLowerCase().includes(searchTerm) ||
            reservation.dni?.toLowerCase().includes(searchTerm) ||
            reservation.email?.toLowerCase().includes(searchTerm)
        );
    });
    
    renderFilteredReservationsTable(filteredReservations);
}

// Renderizar tabla con reservas filtradas
function renderFilteredReservationsTable(filteredData) {
    const tbody = document.querySelector('#reservations-table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!Array.isArray(filteredData) || filteredData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No se encontraron reservas</td></tr>';
        return;
    }
    
    filteredData.forEach((reservation, index) => {
        const originalIndex = reservasData.findIndex(r => r.id === reservation.id);
        const row = document.createElement('tr');
        
        // Agregar clase según estado
        const statusClass = reservation.estado?.toLowerCase() === 'cancelado' ? 'table-danger' : '';
        if (statusClass) row.className = statusClass;
        
        row.innerHTML = `
            <td>${escapeHtml(reservation.reservation_id || 'N/A')}</td>
            <td>${escapeHtml(reservation.nombre_pasajero || 'N/A')}</td>
            <td>${escapeHtml(reservation.numero_vuelo || 'N/A')}</td>
            <td>${formatDate(reservation.fecha)}</td>
            <td>${escapeHtml(reservation.asiento || 'N/A')}</td>
            <td>
                <span class="badge ${getStatusBadgeClass(reservation.estado)}">
                    ${escapeHtml(reservation.estado || 'Pendiente')}
                </span>
            </td>
            <td>S/ ${parseFloat(reservation.precio || 0).toFixed(2)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-info" onclick="viewReservation(${originalIndex})" title="Ver detalles">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${reservation.estado?.toLowerCase() !== 'cancelado' ? 
                        `<button class="btn btn-sm btn-outline-danger" onclick="cancelReservation('${escapeHtml(reservation.id)}')" title="Cancelar">
                            <i class="fas fa-times"></i>
                        </button>` : 
                        '<span class="text-muted small">Cancelado</span>'
                    }
                </div>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM cargado, inicializando panel admin...');
    
    // Cargar reservas si estamos en la sección de reservas
    const currentSection = document.querySelector('.content-section.active');
    if (currentSection && currentSection.id === 'reservations') {
        loadReservations();
    }
    
    // Agregar botón de recarga manual para debug
    const refreshButton = document.createElement('button');
    refreshButton.className = 'btn btn-outline-primary btn-sm ms-2';
    refreshButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Recargar';
    refreshButton.onclick = loadReservations;
    
    const reservationsHeader = document.querySelector('#reservations h2');
    if (reservationsHeader) {
        reservationsHeader.appendChild(refreshButton);
    }
});

function diagnosticReservations() {
    console.log('🔍 DIAGNÓSTICO COMPLETO:');
    console.log('- API_BASE_URL:', API_BASE_URL);
    console.log('- reservasData length:', reservasData.length);
    console.log('- Tabla encontrada:', !!document.querySelector('#reservations-table tbody'));
    console.log('- Función loadReservations:', typeof loadReservations);
    console.log('- Bootstrap Modal disponible:', typeof bootstrap !== 'undefined');
    
    // Probar selector de tabla
    const tableSelectors = [
        '#reservations-table tbody',
        '#reservationsTable tbody', 
        '.table tbody',
        'table tbody'
    ];
    
    tableSelectors.forEach(selector => {
        const element = document.querySelector(selector);
        console.log(`- Selector "${selector}":`, !!element);
    });
}

// Inicializar dashboard cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('admin') || window.location.pathname.includes('dashboard')) {
        loadDashboardData();
        startDashboardAutoRefresh();
        checkApiEndpoints();
    }
});

// Hacer función disponible globalmente para debug
window.diagnosticReservations = diagnosticReservations;
window.loadReservations = loadReservations;