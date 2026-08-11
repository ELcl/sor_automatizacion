import bcrypt

# El NUEVO hash que está guardado en la base de datos para root
hash_db = "$2b$12$E80h8M/14.Gv.YlhU2E4C.0V25yqI7J7Q7aT1v1Fk3A7A9H5U3x1e"
password_plana = "r00t_2026"

# Verificación directa
es_valido = bcrypt.checkpw(password_plana.encode('utf-8'), hash_db.encode('utf-8'))
print("¿Coincide?:", es_valido)