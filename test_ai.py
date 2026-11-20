import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Cargar clave desde el .env
api_key = os.getenv("GEMINI_API_KEY")

try:
    print("⏳ Probando conexión con la API Key...")
    client = genai.Client(api_key=api_key)

    # Modelo actualizado a un identificador válido
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Responde únicamente: Conexión exitosa."
    )

    print("\n✅ RESPUESTA DE GEMINI:")
    print(response.text)

except Exception as e:
    print("\n❌ Error detectado:")
    print(e)