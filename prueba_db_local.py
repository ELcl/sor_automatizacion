import psycopg2

try:
    conexion = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="",
        port=5432,
    )
    print("✅ ¡Conexión exitosa a la BD local!")
    conexion.close()
except Exception as e:
    print(f"❌ Error de conexión: {e}")