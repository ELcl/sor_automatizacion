import os
import re
import sys
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from docxtpl import DocxTemplate

# ==========================================
# CONFIGURACIÓN DE CREDENCIALES (RÉPLICA)
# ==========================================
DB_HOST = "172.16.100.241"
DB_NAME = "sorbd_gis"
DB_USER = "user_com"
DB_PASS = "admin_12345"

# Traducción explícita de fechas para entornos Windows
DIAS_ESPANOL = {
    "MONDAY": "LUNES", "TUESDAY": "MARTES", "WEDNESDAY": "MIÉRCOLES",
    "THURSDAY": "JUEVES", "FRIDAY": "VIERNES", "SATURDAY": "SÁBADO", "SUNDAY": "DOMINGO"
}
MESES_ESPANOL = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL", 5: "MAYO", 6: "JUNIO",
    7: "JULIO", 8: "AGOSTO", 9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

def parsear_argumentos():
    fecha_base = datetime.now()
    dias_antelacion = 2

    if len(sys.argv) == 2:
        try:
            dias_antelacion = int(sys.argv[1])
        except ValueError:
            print("❌ Error: El argumento de días debe ser un número entero.")
            sys.exit(1)
    elif len(sys.argv) == 3:
        try:
            fecha_base = datetime.strptime(sys.argv[1], "%d%m%y")
            dias_antelacion = int(sys.argv[2])
        except ValueError:
            print("❌ Error: Formato de fecha incorrecto. Use: python app.py DDMMYY [días]")
            sys.exit(1)

    fecha_objective = fecha_base + timedelta(days=dias_antelacion)
    return fecha_base, fecha_objective

def extraer_datos_por_fecha(fecha_target):
    """Extrae los registros de la réplica filtrando estrictamente por prgavipre = 1."""
    conexion = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, connect_timeout=10
    )

    fecha_inicio_dia = fecha_target.strftime("%Y-%m-%d 00:00:00")
    fecha_fin_dia = fecha_target.strftime("%Y-%m-%d 23:59:59")

    print(f"🔍 Filtrando en PostgreSQL cortes oficiales (Prensa) desde {fecha_inicio_dia} hasta {fecha_fin_dia}...")

    query = """
        SELECT
            prgfhinip AS inicio,
            prgfhfinp AS fin,
            prgdsc AS descripcion,
            prgmotdsc AS motivo
        FROM public.sorprogram
        WHERE prgfhinip >= %s
          AND prgfhinip <= %s
          AND prgavipre = 1
        ORDER BY prgfhinip ASC;
    """

    df = pd.read_sql_query(query, conexion, params=(fecha_inicio_dia, fecha_fin_dia))
    conexion.close()

    df = df.drop_duplicates()
    return df

def normalizar_texto_zonas(desc_original):
    """
    MODIFICADO: Remueve ÚNICAMENTE el paréntesis del sistema al inicio de la cadena.
    El anclaje '^' previene la eliminación de paréntesis de las comunidades posteriores.
    """
    # Remueve el primer paréntesis del sistema al inicio (ej: "(AROMA) ") sin tocar los demás
    texto_sin_sistema = re.sub(r'^\(.*?\)\s*', '', desc_original).strip()
    texto_sin_sistema = re.sub(r'^[.,\s\-:;]+', '', texto_sin_sistema).strip()
    return texto_sin_sistema

def homologar_sistema(texto_parentesis):
    """
    Regla de negocio estricta para mapear las variaciones a los 4 sistemas oficiales.
    """
    txt = texto_parentesis.upper().strip()

    if "MAYOR" in txt or "YMAYOR" in txt:
        return "SISTEMA MAYOR"
    elif "NORTE" in txt or "NRT" in txt:
        return "SISTEMA NORTE"
    elif "AROMA" in txt or "ARM" in txt:
        return "SISTEMA AROMA"
    elif "NUEVO" in txt or "NVO" in txt:
        return "SISTEMA NUEVO"

    return "SISTEMA GENERAL"

def procesar_y_agrupar(df):
    df['inicio'] = pd.to_datetime(df['inicio'])
    df['fin'] = pd.to_datetime(df['fin'])

    ORDEN_SISTEMAS = [
        "SISTEMA MAYOR",
        "SISTEMA AROMA",
        "SISTEMA NUEVO",
        "SISTEMA NORTE"
    ]

    reporte_agrupado_raw = {}

    for _, fila in df.iterrows():
        dia_semana_en = fila['inicio'].strftime('%A').upper()
        dia_semana_es = DIAS_ESPANOL.get(dia_semana_en, dia_semana_en)
        num_dia = fila['inicio'].day
        mes_es = MESES_ESPANOL.get(fila['inicio'].month, 6)
        anho = fila['inicio'].year
        dia_str = f"{dia_semana_es} {num_dia} DE {mes_es} DE {anho}"

        desc_original = str(fila['descripcion']).strip()
        
        # MODIFICADO: Buscamos el sistema estrictamente basándonos en el primer paréntesis del inicio
        sistema_match = re.match(r'^\((.*?)\)', desc_original)

        if sistema_match:
            contenido_parentesis = sistema_match.group(1)
            sistema = homologar_sistema(contenido_parentesis)
        else:
            sistema = "SISTEMA GENERAL"

        # Limpieza segura de zonas afectadas en prgdsc (No destruye paréntesis internos)
        detalle_zonas_procesado = normalizar_texto_zonas(desc_original)

        hora_ini_str = fila['inicio'].strftime('%H:%M')
        hora_fin_str = fila['fin'].strftime('%H:%M')
        motivo_str = str(fila['motivo']).strip().upper() if fila['motivo'] else "MANTENIMIENTO PREVENTIVO"

        if dia_str not in reporte_agrupado_raw:
            reporte_agrupado_raw[dia_str] = {}
        if sistema not in reporte_agrupado_raw[dia_str]:
            reporte_agrupado_raw[dia_str][sistema] = []

        existe_duplicado_hora = False
        for corte_existente in reporte_agrupado_raw[dia_str][sistema]:
            if (corte_existente['hora_inicio'] == hora_ini_str and
                corte_existente['hora_fin'] == hora_fin_str):
                # Se podría concatenar el texto aquí si las zonas difieren,
                # pero mantenemos tu control original de desduplicación temporal.
                existe_duplicado_hora = True
                break

        if not existe_duplicado_hora:
            corte_info = {
                'motivo': motivo_str,
                'hora_inicio': hora_ini_str,
                'hora_fin': hora_fin_str,
                'detalle_zonas': detalle_zonas_procesado
            }
            reporte_agrupado_raw[dia_str][sistema].append(corte_info)

    reporte_ordenado = {}
    for dia_str, sistemas_dict in reporte_agrupado_raw.items():
        sistemas_ordenados = sorted(
            sistemas_dict.keys(),
            key=lambda x: ORDEN_SISTEMAS.index(x) if x in ORDEN_SISTEMAS else len(ORDEN_SISTEMAS)
        )
        reporte_ordenado[dia_str] = {sis: sistemas_dict[sis] for sis in sistemas_ordenados}

    return reporte_ordenado

def generar_reporte_unico(reporte_data, fecha_target):
    carpeta_salida = "reportes"
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    if not reporte_data:
        print(f"⚠️ Alerta: No se encontraron registros de prensa para la fecha solicitada.")
        return

    doc = DocxTemplate("plantilla_cortes.docx")
    contexto = {'reporte_agrupado': reporte_data}
    doc.render(contexto)

    str_fecha_archivo = fecha_target.strftime("%Y%m%d")
    ruta_final = os.path.join(carpeta_salida, f"Aviso_Cortes_{str_fecha_archivo}.docx")
    doc.save(ruta_final)
    print(f"\n💾 ¡REPORTE GENERADO PERFECTAMENTE!")
    print(f"📍 Guardado en: {ruta_final}")

def main():
    print("🚀 === PIPELINE DELAPAZ: HOMOLOGACIÓN DE 4 SISTEMAS ACTIVA ===")
    fecha_base, fecha_objective = parsear_argumentos()

    df_crudo = extraer_datos_por_fecha(fecha_objective)
    print(f"✅ Registros únicos recuperados de la DB: {len(df_crudo)}")

    reporte_estructurado = procesar_y_agrupar(df_crudo)
    generar_reporte_unico(reporte_estructurado, fecha_objective)
    print("🏁 === PROCESO CONCLUIDO CON ÉXITO ===")

if __name__ == "__main__":
    main()