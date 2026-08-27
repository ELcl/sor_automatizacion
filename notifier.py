import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config

def enviar_correo_notificacion(destinatario, asunto, cuerpo_html):
    """
    Envía un correo electrónico estilizado usando la configuración de Config.
    Retorna True si el envío fue exitoso, o False si ocurrió un error.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
    msg["To"] = destinatario

    # Adjuntar versión HTML
    parte_html = MIMEText(cuerpo_html, "html", "utf-8")
    msg.attach(parte_html)

    try:
        # Para Mailpit (local) no se requiere TLS ni autenticación previa
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
            if Config.SMTP_USER and Config.SMTP_PASSWORD:
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_FROM_EMAIL, destinatario, msg.as_string())
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, f"Error al enviar correo vía SMTP: {str(e)}"