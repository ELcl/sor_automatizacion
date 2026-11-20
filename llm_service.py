import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def get_gemini_client():
    """Inicializa el cliente oficial de Gemini con la API Key del entorno."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env")
    return genai.Client(api_key=api_key)


def obtener_datos_operativos_db(dias=180):
    """
    Consulta las tablas reales de la base de datos (sorprogram y sorprgope)
    para obtener las métricas de solicitudes, operaciones físicas y la tendencia,
    filtradas por el rango de días especificado.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "sorbd_gis"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS")
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1. KPIs Generales filtrados por rango de días
        query_kpis = """
            SELECT 
                COUNT(DISTINCT p.prgcod) as total_cortes,
                COUNT(o.prgopesec) as total_operaciones,
                COALESCE(
                    SUM(EXTRACT(EPOCH FROM (p.prgfhfinp - p.prgfhinip)) / 3600.0), 0
                ) as duracion_total_hrs,
                COALESCE(
                    AVG(EXTRACT(EPOCH FROM (p.prgfhfinp - p.prgfhinip)) / 60.0), 0
                ) as duracion_promedio_min,
                MODE() WITHIN GROUP (ORDER BY p.prgdsc) as descripcion_recurrente
            FROM sorprogram p
            LEFT JOIN sorprgope o ON p.prgcod = o.prgcod
            WHERE p.prgfhinip IS NOT NULL
              AND p.prgfhinip >= NOW() - (%s || ' days')::INTERVAL;
        """
        cursor.execute(query_kpis, (dias,))
        resumen_kpis = dict(cursor.fetchone() or {})

        # 2. Tendencia diaria/mensual para el gráfico
        query_tendencia = """
            SELECT 
                p.prgfhinip::date AS fecha,
                COUNT(DISTINCT p.prgcod) AS cantidad_programas,
                COUNT(o.prgopesec) AS cantidad_operaciones
            FROM sorprogram p
            LEFT JOIN sorprgope o ON p.prgcod = o.prgcod
            WHERE p.prgfhinip IS NOT NULL
              AND p.prgfhinip >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY p.prgfhinip::date
            ORDER BY fecha ASC;
        """
        cursor.execute(query_tendencia, (dias,))
        tendencia = [dict(row) for row in cursor.fetchall()]

        # 3. Operaciones / Programas más significativos en el período
        query_criticos = """
            SELECT 
                p.prgcod,
                COALESCE(p.prgcodcir, 'Sin circuito') as circuito,
                p.prgdsc as descripcion_programa,
                ROUND((EXTRACT(EPOCH FROM (p.prgfhfinp - p.prgfhinip)) / 60.0)::numeric, 1) as duracion_min,
                COUNT(o.prgopesec) as cantidad_operaciones,
                STRING_AGG(DISTINCT o.prgopedsc, ' | ') as detalle_operaciones
            FROM sorprogram p
            JOIN sorprgope o ON p.prgcod = o.prgcod
            WHERE p.prgfhinip IS NOT NULL
              AND p.prgfhinip >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY p.prgcod, p.prgcodcir, p.prgdsc, p.prgfhfinp, p.prgfhinip
            ORDER BY duracion_min DESC, cantidad_operaciones DESC
            LIMIT 5;
        """
        cursor.execute(query_criticos, (dias,))
        cortes_criticos = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return resumen_kpis, tendencia, cortes_criticos

    except Exception as e:
        print(f"⚠️ Error al consultar PostgreSQL: {e}")
        return {}, [], []


def generar_diagnostico_operativo(resumen_kpis: dict, cortes_criticos: list) -> str:
    """Genera el reporte técnico de diagnóstico usando Chat en lugar de generate_content."""
    client = get_gemini_client()
    fecha_actual = datetime.now().strftime("%d de %B de %Y")

    system_instruction = f"""
    Eres un Ingeniero Experto en Diagnóstico de Redes de Distribución Eléctrica y Gestión de Operaciones (SOR).
    Tu objetivo es analizar métricas de solicitudes de corte/mantenimiento y sus operaciones físicas asociadas,
    evaluar duraciones, circuitos afectados y emitir recomendaciones operativas concisas.
    Usa un tono técnico, directo y profesional.
    Si incluyes un encabezado con fecha, utiliza la fecha actual proporcionada: {fecha_actual}.
    """

    prompt = f"""
    Fecha del reporte: {fecha_actual}

    Analiza la siguiente información de la base de datos operativa (sorprogram y sorprgope):

    --- RESUMEN DE KPIS GENERALES ---
    - Total de Solicitudes/Programas: {resumen_kpis.get('total_cortes', 0)}
    - Total de Operaciones Físicas Realizadas: {resumen_kpis.get('total_operaciones', 0)}
    - Duración Total Acumulada: {resumen_kpis.get('duracion_total_hrs', 0):.2f} horas
    - Duración Promedio por Evento: {resumen_kpis.get('duracion_promedio_min', 0):.2f} minutos
    - Descripción / Motivo Frecuente: {resumen_kpis.get('descripcion_recurrente', 'N/A')}

    --- SOLICITUDES Y OPERACIONES MÁS SIGNIFICATIVAS ---
    {cortes_criticos}

    --- INSTRUCCIONES DEL REPORTE ---
    Por favor genera un reporte de diagnóstico estructurado en formato Markdown con las siguientes secciones:
    1. **Evaluación de Severidad e Impacto**: Dictamen del comportamiento de las solicitudes y volumen de operaciones por circuito.
    2. **Análisis de Operaciones y Causas**: Diagnóstico sobre los circuitos más afectados y las maniobras registradas en sorprgope.
    3. **Recomendaciones Operativas**: 3 acciones concretas para optimizar la programación de trabajos y reducir tiempos de maniobra.
    """

    modelos_prioritarios = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    for model_name in modelos_prioritarios:
        try:
            chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )
            response = chat.send_message(prompt)
            return response.text

        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                continue
            else:
                return f"❌ Error al generar el diagnóstico con IA: {str(e)}"

    return "❌ Modelos no disponibles momentáneamente. Reintente en unos segundos."