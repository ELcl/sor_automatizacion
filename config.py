import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

class Config:
    # SMTP / Mailpit
    SMTP_HOST = os.getenv("SMTP_HOST", "127.0.0.1")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 1025))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "notificaciones@delapaz.bo")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "DELAPAZ Notificaciones")

    # PostgreSQL Local
    DB_LOCAL_HOST = os.getenv("DB_LOCAL_HOST", "localhost")
    DB_LOCAL_PORT = int(os.getenv("DB_LOCAL_PORT", 5432))
    DB_LOCAL_NAME = os.getenv("DB_LOCAL_NAME", "postgres")
    DB_LOCAL_USER = os.getenv("DB_LOCAL_USER", "postgres")
    DB_LOCAL_PASS = os.getenv("DB_LOCAL_PASS", "")

    # PostgreSQL Remoto GIS
    DB_HOST = os.getenv("DB_HOST", "172.16.100.241")
    DB_NAME = os.getenv("DB_NAME", "sorbd_gis")
    DB_USER = os.getenv("DB_USER", "user_com")
    DB_PASS = os.getenv("DB_PASS", "admin_12345")