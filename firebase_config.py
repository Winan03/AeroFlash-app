import pyrebase
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Firebase
config = {
    "apiKey": os.getenv('FIREBASE_API_KEY'),
    "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
    "databaseURL": os.getenv('FIREBASE_DATABASE_URL'),
    "projectId": os.getenv('FIREBASE_PROJECT_ID'),
    "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.getenv('FIREBASE_APP_ID')
}

# Inicializar Firebase
firebase = pyrebase.initialize_app(config)

# Obtener referencia a la base de datos
db = firebase.database()

# Función para verificar conexión
def test_connection():
    try:
        test_data = {"test": "connection"}
        result = db.child("test").set(test_data)
        if result:
            print("✅ Conexión a Firebase exitosa")
            # Limpiar dato de prueba
            db.child("test").remove()
            return True
        return False
    except Exception as e:
        print(f"❌ Error de conexión a Firebase: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()