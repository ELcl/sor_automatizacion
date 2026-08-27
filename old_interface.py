import io
import math
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

# Importaciones locales del módulo word
from modules.word import (
    ReporteDocx,
    formatear_fecha,
    formatear_fecha_hora,
    generar_docx_individual,
    obtener_historial_exportaciones,
    registrar_exportaciones,
)

# Configuración de la página
st.set_page_config(
    page_title="Gestor de Avisos y Reportes", page_icon="📑", layout="wide"
)

# Datos de conexión a la Base de Datos
DB_HOST = "172.16.100.241"
DB_NAME = "sor"
DB_USER = "consultor"
DB_PASS = "c0nsult0r"


# ----------------------------------------------------
# FUNCIONES BASE DE DATOS
# ----------------------------------------------------
def extraer_datos_db(fecha_ini, fecha_fin, estado=None):
    """Extrae los registros filtrados por rango de fecha y estado opcional."""
    try:
        conexion = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )

        if estado and estado != "TODOS":
            query = """
                SELECT prgcod, prglbl, prgfhinip AS inicio, prgfhfinp AS fin, prgfhapr, prgdsc AS descripcion, prgmotdsc AS motivo,
                       pernomazt, perpmaprb, perpmcoi, tdmoddsg, prgtotkva, prgtotcon, prgfhaviso, prgasigtra, prgproynro,
                       circod, subcod, tdciucod, perpmresp, prgavipre, prgaviper, prgavialc
                FROM public.sorprogram
                WHERE prgfhinip >= %s 
                  AND prgfhinip <= %s 
                  AND prgavipre = 1
                  AND tdprgest = %s
                ORDER BY prgfhinip ASC;
            """
            params = (f"{fecha_ini} 00:00:00", f"{fecha_fin} 23:59:59", estado)
        else:
            query = """
                SELECT prgcod, prglbl, prgfhinip AS inicio, prgfhfinp AS fin, prgfhapr, prgdsc AS descripcion, prgmotdsc AS motivo,
                       pernomazt, perpmaprb, perpmcoi, tdmoddsg, prgtotkva, prgtotcon, prgfhaviso, prgasigtra, prgproynro,
                       circod, subcod, tdciucod, perpmresp, prgavipre, prgaviper, prgavialc
                FROM public.sorprogram
                WHERE prgfhinip >= %s 
                  AND prgfhinip <= %s 
                  AND prgavipre = 1
                ORDER BY prgfhinip ASC;
            """
            params = (f"{fecha_ini} 00:00:00", f"{fecha_fin} 23:59:59")

        df = pd.read_sql_query(query, conexion, params=params)
        conexion.close()

        df = df.drop_duplicates(subset=["prgcod"])

        if not df.empty:
            codigos = df["prgcod"].tolist()
            historial = obtener_historial_exportaciones(codigos)

            exportado_por_lista = []
            incluir_lista = []

            for cod in codigos:
                registros = historial.get(cod, [])
                if registros:
                    exportado_por_lista.append(", ".join(registros))
                    incluir_lista.append(False)
                else:
                    exportado_por_lista.append("Pendiente")
                    incluir_lista.append(True)

            df["Exportado Por"] = exportado_por_lista
            df["Incluir en Reporte"] = incluir_lista

        return df
    except Exception as e:
        st.error(f"❌ Error de conexión a la Base de Datos: {e}")
        return pd.DataFrame()


def extraer_operaciones_lote(lista_prgcod):
    """Extrae las operaciones para una lista de prgcod."""
    if not lista_prgcod:
        return pd.DataFrame()
    try:
        conexion = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        query = """
            SELECT prgcod, prgopesec, prgopelug, prgopedsc, prgopeeje, prgopehp, prgopehr
            FROM public.sorprgope
            WHERE prgcod IN %s
            ORDER BY prgcod ASC, prgopesec ASC;
        """
        df = pd.read_sql_query(query, conexion, params=(tuple(lista_prgcod),))
        conexion.close()
        return df
    except Exception as e:
        st.error(f"❌ Error al extraer operaciones detalladas: {e}")
        return pd.DataFrame()


# ----------------------------------------------------
# INTERFAZ GRÁFICA DE USUARIO
# ----------------------------------------------------
st.title("📑 Generación de Avisos e Informes Técnicos")
st.markdown(
    "Filtre las programaciones de mantenimiento y genere reportes individuales o consolidados en Word."
)

# Inicializar Estados
if "usuario_nombre" not in st.session_state:
    st.session_state["usuario_nombre"] = "Operador"

if "datos_extraidos" not in st.session_state:
    st.session_state["datos_extraidos"] = pd.DataFrame()

# Sidebar de Parámetros
with st.sidebar:
    st.header("⚙️ Parámetros de Consulta")

    st.session_state["usuario_nombre"] = st.text_input(
        "Nombre del Operador/Técnico:",
        value=st.session_state["usuario_nombre"],
    )

    st.subheader("Rango de Fechas")
    f_ini = st.date_input("Fecha Inicial", datetime.today())
    f_fin = st.date_input("Fecha Final", datetime.today())

    f_ini_str = f_ini.strftime("%Y-%m-%d")
    f_fin_str = f_fin.strftime("%Y-%m-%d")

    estado_opcion = st.selectbox(
        "Estado del Programa",
        options=["TODOS", "APROBADO", "PROGRAMADO", "PENDIENTE"],
    )

    st.markdown("---")
    if st.button("🔎 Buscar Programaciones", type="primary"):
        with st.spinner("Conectando a la base de datos..."):
            st.session_state["datos_extraidos"] = extraer_datos_db(
                f_ini_str, f_fin_str, estado_opcion
            )

# Cuerpo Principal
df_actual = st.session_state["datos_extraidos"]

if not df_actual.empty:
    st.subheader("📋 Registros Encontrados")

    # Modificación dinámica de la selección de checkboxes
    df_editor = st.data_editor(
        df_actual,
        column_config={
            "Incluir en Reporte": st.column_config.CheckboxColumn(
                "Incluir", help="Marque para exportar en lote"
            ),
            "Exportado Por": st.column_config.TextColumn(
                "Estado de Exportación"
            ),
        },
        disabled=[
            c for c in df_actual.columns if c not in ["Incluir en Reporte"]
        ],
        hide_index=True,
        use_container_width=True,
    )

    # Filtrar seleccionados
    seleccionados = df_editor[df_editor["Incluir en Reporte"] == True]

    st.info(
        f"Registros seleccionados para generación de lote: **{len(seleccionados)}** de **{len(df_actual)}**."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Generación de Reportes Individuales")
        prgcod_sel = st.selectbox(
            "Seleccione un Código para Exportar Individualmente:",
            df_actual["prgcod"].unique(),
        )

        if st.button("📥 Generar Word Individual"):
            fila = df_actual[df_actual["prgcod"] == prgcod_sel].iloc[0]
            df_ops = extraer_operaciones_lote([prgcod_sel])

            docx_bytes = generar_docx_individual(
                fila, df_ops, st.session_state["usuario_nombre"]
            )
            registrar_exportaciones(
                [prgcod_sel], st.session_state["usuario_nombre"]
            )

            st.download_button(
                label=f"💾 Descargar Aviso ({prgcod_sel}).docx",
                data=docx_bytes,
                file_name=f"Aviso_{prgcod_sel}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    with col2:
        st.subheader("📦 Generación de Reporte Consolidado")
        if not seleccionados.empty:
            if st.button("🚀 Procesar Reporte Lote Consolidado"):
                with st.spinner("Procesando documento consolidado..."):
                    codigos_lote = seleccionados["prgcod"].tolist()
                    df_ops_lote = extraer_operaciones_lote(codigos_lote)

                    reporte = ReporteDocx()
                    for idx, row in seleccionados.iterrows():
                        ops_row = df_ops_lote[
                            df_ops_lote["prgcod"] == row["prgcod"]
                        ]
                        reporte.agregar_programa(
                            row, ops_row, st.session_state["usuario_nombre"]
                        )

                    buffer = io.BytesIO()
                    reporte.guardar(buffer)
                    buffer.seek(0)

                    registrar_exportaciones(
                        codigos_lote, st.session_state["usuario_nombre"]
                    )

                    st.download_button(
                        label="💾 Descargar Consolidado (.docx)",
                        data=buffer,
                        file_name=f"Consolidado_Avisos_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
        else:
            st.warning("Seleccione al menos un registro para generar en lote.")

else:
    st.info(
        "Utilice el panel lateral para seleccionar un rango de fechas y hacer clic en **Buscar Programaciones**."
    )