import pg8000.native

try:
    conn = pg8000.native.Connection(
        host="172.16.100.241",
        database="TU_NOMBRE_BD",
        user="TU_USUARIO",
        password="TU_PASSWORD",
        port=5432,
        timeout=10
    )
    print("✅ ¡Conexión exitosa con pg8000!")
    conn.close()
except Exception as e:
    print(f"❌ Error exacto: {e}")