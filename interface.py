import locale
import os

os.environ["LANG"] = "es_ES.UTF-8"

from datetime import datetime, timedelta
from io import BytesIO
import re

import bcrypt
from docxtpl import DocxTemplate
import pandas as pd
import psycopg2
import streamlit as st

# ==========================================
# CONFIGURACIÓN DE CREDENCIALES
# ==========================================
DB_HOST = "172.16.100.241"
DB_NAME = "sorbd_gis"
DB_USER = "user_com"
DB_PASS = "admin_12345"

# Configuración de Base de Datos Local
DB_LOCAL_HOST = "localhost"
DB_LOCAL_NAME = "postgres"
DB_LOCAL_USER = "postgres"
DB_LOCAL_PASS = ""
DB_LOCAL_PORT = 5432

DIAS_ESPANOL = {
    "MONDAY": "LUNES",
    "TUESDAY": "MARTES",
    "WEDNESDAY": "MIÉRCOLES",
    "THURSDAY": "JUEVES",
    "FRIDAY": "VIERNES",
    "SATURDAY": "SÁBADO",
    "SUNDAY": "DOMINGO",
}

MESES_ESPANOL = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

# ORDEN REQUERIDO PARA SISTEMAS Y CIUDADES
ORDEN_SISTEMAS = [
    "CIUDAD DE LA PAZ",
    "CIUDAD DE EL ALTO",
    "CIUDAD DE ACHOCALLA",
    "CIUDAD DE VIACHA",
    "SISTEMA AROMA",
    "SISTEMA NUEVO",
    "SISTEMA NORTE",
]

# MAPEO DE CÓDIGOS DE CIUDAD (tdciucod) A NOMBRES FORMALES
MAPEO_CIUDADES = {
    "LP": "CIUDAD DE LA PAZ",
    "EA": "CIUDAD DE EL ALTO",
    "AC": "CIUDAD DE ACHOCALLA",
    "VI": "CIUDAD DE VIACHA",
}

# ==========================================
# CONFIGURACIÓN REGIONAL GLOBAL DE PLOTLY
# ==========================================
CONFIG_PLOTLY_ES = {
    "locale": "es",
    "locales": {
        "es": {
            "dictionary": {
                "Zoom in": "Acercar",
                "Zoom out": "Alejar",
                "Pan": "Desplazar",
                "Zoom": "Tamaño",
                "Reset axes": "Restablecer ejes",
                "Download plot as a PNG": "Descargar imagen PNG",
                "Autoscale": "Autoescalar",
            },
            "format": {},
        }
    },
    "displayModeBar": True,
}

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="SOR - DELAPAZ Service Center", layout="wide", page_icon="⚡"
)

# ==========================================
# INYECCIÓN DE CSS EXTERNO
# ==========================================
def cargar_css(ruta_css):
    try:
        with open(ruta_css, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo de estilos: {ruta_css}")


cargar_css("styles.css")


# ==========================================
# MODAL Y LÓGICA DE LOGOUT
# ==========================================
@st.dialog("Confirmar Cierre de Sesión")
def modal_confirmar_logout():
    st.write("¿Realmente deseas cerrar la sesión actual y volver al inicio?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Sí, cerrar sesión", type="primary", use_container_width=True
        ):
            st.session_state.clear()
            st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()


# ==========================================
# CONTROL DE AUTENTICACIÓN / LOGIN
# ==========================================
def verificar_credenciales_db(username, password_plana):
    """Consulta la tabla app_usuario en la base de datos LOCAL y valida la contraseña."""
    try:
        conexion = psycopg2.connect(
            host=DB_LOCAL_HOST,
            database=DB_LOCAL_NAME,
            user=DB_LOCAL_USER,
            password=DB_LOCAL_PASS,
            port=DB_LOCAL_PORT,
            connect_timeout=5,
        )
        cursor = conexion.cursor()

        query = """
            SELECT usr_id, usr_username, usr_password_hash, usr_nombre_completo, usr_cargo, usr_rol
            FROM public.app_usuario
            WHERE usr_username = %s AND usr_activo = TRUE;
        """
        cursor.execute(query, (username.strip(),))
        usuario = cursor.fetchone()

        if usuario:
            usr_id, usr_name, hash_db, nombre_comp, cargo, rol = usuario

            if bcrypt.checkpw(
                password_plana.encode("utf-8"), hash_db.encode("utf-8")
            ):
                cursor.execute(
                    "UPDATE public.app_usuario SET usr_ultimo_login = CURRENT_TIMESTAMP WHERE usr_id = %s;",
                    (usr_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO public.app_bitacora_actividad (usr_id, act_accion, act_descripcion)
                    VALUES (%s, 'LOGIN_SUCCESS', 'Inicio de sesión exitoso');
                """,
                    (usr_id,),
                )

                conexion.commit()
                cursor.close()
                conexion.close()

                return {
                    "usr_id": usr_id,
                    "usr_username": usr_name,
                    "usr_nombre_completo": nombre_comp,
                    "usr_cargo": cargo,
                    "usr_rol": rol,
                }

        cursor.execute(
            """
            INSERT INTO public.app_bitacora_actividad (usr_id, act_accion, act_descripcion)
            VALUES (NULL, 'LOGIN_FAILED', %s);
        """,
            (f"Intento fallido para el usuario: {username}",),
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        return None

    except Exception as e:
        st.error(
            f"❌ Error al consultar la base de datos local de usuarios: {e}"
        )
        return None


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    col_acc_1, col_acc_2, col_acc_3 = st.columns([1, 1.5, 1])

    with col_acc_2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(
                """
    <div class="energy-banner">
        <h1>Bienvenido</h1>
    </div>
    """,
                unsafe_allow_html=True,
            )

            with st.form("form_login"):
                usuario = st.text_input(
                    "Usuario", placeholder="Ingresa tu usuario"
                )
                password = st.text_input(
                    "Contraseña", type="password", placeholder="••••••••"
                )

                btn_ingresar = st.form_submit_button(
                    "Iniciar Sesión", use_container_width=True
                )

                if btn_ingresar:
                    if not usuario or not password:
                        st.warning("⚠️ Por favor ingresa el usuario y la contraseña.")
                    else:
                        with st.spinner("Verificando credenciales..."):
                            datos_usuario = verificar_credenciales_db(
                                usuario, password
                            )

                        if datos_usuario:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_info"] = datos_usuario
                            st.session_state["vista_actual"] = "operaciones"
                            st.rerun()
                        else:
                            st.error(
                                "❌ Credenciales incorrectas o usuario no activo"
                            )

    st.stop()

# ==========================================
# BANNER SUPERIOR ANIMADO
# ==========================================
st.markdown(
    """
    <div class="energy-banner">
        <h1>Plataforma de consulta, consolidación y reportes de cortes de energía</h1>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# LÓGICA DE CONEXIÓN Y PROCESAMIENTO
# ==========================================

def obtener_historial_exportaciones(lista_prgcod):
    """Consulta en la BD local qué usuarios y con qué formato (HTML/DOCX) han exportado cada prgcod."""
    if not lista_prgcod:
        return {}
    try:
        conexion = psycopg2.connect(
            host=DB_LOCAL_HOST,
            database=DB_LOCAL_NAME,
            user=DB_LOCAL_USER,
            password=DB_LOCAL_PASS,
            port=DB_LOCAL_PORT,
            connect_timeout=5,
        )
        cursor = conexion.cursor()
        query = """
            SELECT e.prgcod, u.usr_username, e.formato_exportacion
            FROM public.app_corte_exportado e
            JOIN public.app_usuario u ON e.usr_id = u.usr_id
            WHERE e.prgcod IN %s;
        """
        cursor.execute(query, (tuple(lista_prgcod),))
        filas = cursor.fetchall()
        cursor.close()
        conexion.close()

        historial = {}
        for prgcod, username, formato in filas:
            if prgcod not in historial:
                historial[prgcod] = []
            fmt_str = f" ({formato.upper()})" if formato else ""
            historial[prgcod].append(f"{username}{fmt_str}")

        return historial
    except Exception as e:
        st.error(f"❌ Error al consultar el historial de exportaciones: {e}")
        return {}


def registrar_cortes_exportados(lista_prgcod, usr_id, formato="HTML"):
    """Registra o actualiza en la BD local los prgcod exportados indicando el formato (HTML o DOCX)."""
    if not lista_prgcod or not usr_id:
        return
    try:
        conexion = psycopg2.connect(
            host=DB_LOCAL_HOST,
            database=DB_LOCAL_NAME,
            user=DB_LOCAL_USER,
            password=DB_LOCAL_PASS,
            port=DB_LOCAL_PORT,
            connect_timeout=5,
        )
        cursor = conexion.cursor()

        query = """
            INSERT INTO public.app_corte_exportado (prgcod, usr_id, formato_exportacion, exp_fecha)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (prgcod, usr_id, formato_exportacion)
            DO UPDATE SET exp_fecha = EXCLUDED.exp_fecha;
        """
        for prgcod in lista_prgcod:
            cursor.execute(query, (prgcod, usr_id, formato.upper()))

        conexion.commit()
        cursor.close()
        conexion.close()
    except Exception as e:
        st.error(
            f"❌ Error al registrar las exportaciones en la base de datos: {e}"
        )


def extraer_datos_db(fecha_ini, fecha_fin, estado=None):
    try:
        conexion = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=5,
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
    if not lista_prgcod:
        return pd.DataFrame()
    try:
        conexion = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=5,
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


def normalizar_texto_zonas(desc_original):
    texto_sin_sistema = re.sub(r"^\(.*?\)\s*", "", desc_original).strip()
    return re.sub(r"^[.,\s\-:;]+", "", texto_sin_sistema).strip()


def homologar_sistema(texto_parentesis, tdciucod=None):
    """Homologa la etiqueta del sistema y desglosa el Sistema Mayor por Ciudad usando tdciucod."""
    txt = str(texto_parentesis).upper().strip()
    
    if "MAYOR" in txt or "YMAYOR" in txt:
        codigo_ciudad = str(tdciucod).strip().upper() if tdciucod else ""
        return MAPEO_CIUDADES.get(codigo_ciudad, "CIUDAD DE LA PAZ")
    elif "NORTE" in txt or "NRT" in txt:
        return "SISTEMA NORTE"
    elif "AROMA" in txt or "ARM" in txt:
        return "SISTEMA AROMA"
    elif "NUEVO" in txt or "NVO" in txt:
        return "SISTEMA NUEVO"
    
    return "SISTEMA GENERAL"


def procesar_y_agrupar(df):
    df["inicio"] = pd.to_datetime(df["inicio"])
    df["fin"] = pd.to_datetime(df["fin"])
    reporte_agrupado_raw = {}

    for _, fila in df.iterrows():
        dia_semana_en = fila["inicio"].strftime("%A").upper()
        dia_semana_es = DIAS_ESPANOL.get(dia_semana_en, dia_semana_en)
        dia_str = f"{dia_semana_es} {fila['inicio'].day} DE {MESES_ESPANOL.get(fila['inicio'].month, 'JUNIO')} DE {fila['inicio'].year}"

        desc_original = str(fila["descripcion"]).strip()
        sistema_match = re.match(r"^\((.*?)\)", desc_original)
        
        texto_sistema = sistema_match.group(1) if sistema_match else ""
        tdciucod_val = fila.get("tdciucod", "")
        
        sistema = homologar_sistema(texto_sistema, tdciucod_val)

        detalle_zonas_procesado = normalizar_texto_zonas(desc_original)
        hora_ini_str = fila["inicio"].strftime("%H:%M")
        hora_fin_str = fila["fin"].strftime("%H:%M")
        motivo_str = (
            str(fila["motivo"]).strip().upper()
            if fila["motivo"]
            else "MANTENIMIENTO PREVENTIVO"
        )

        if dia_str not in reporte_agrupado_raw:
            reporte_agrupado_raw[dia_str] = {}
        if sistema not in reporte_agrupado_raw[dia_str]:
            reporte_agrupado_raw[dia_str][sistema] = []

        if not any(
            c["hora_inicio"] == hora_ini_str and c["hora_fin"] == hora_fin_str
            for c in reporte_agrupado_raw[dia_str][sistema]
        ):
            reporte_agrupado_raw[dia_str][sistema].append({
                "motivo": motivo_str,
                "hora_inicio": hora_ini_str,
                "hora_fin": hora_fin_str,
                "detalle_zonas": detalle_zonas_procesado,
            })

    reporte_ordenado = {}
    for dia_str, sistemas_dict in reporte_agrupado_raw.items():
        sistemas_ordenados = sorted(
            sistemas_dict.keys(),
            key=lambda x: (
                ORDEN_SISTEMAS.index(x)
                if x in ORDEN_SISTEMAS
                else len(ORDEN_SISTEMAS)
            ),
        )
        reporte_ordenado[dia_str] = {
            sis: sistemas_dict[sis] for sis in sistemas_ordenados
        }
    return reporte_ordenado


def construir_datos_html(df_program, df_operaciones):
    solicitudes_lista = []
    for _, fila in df_program.iterrows():
        f_ini = pd.to_datetime(fila["inicio"])
        f_fin = pd.to_datetime(fila["fin"])
        f_emision = (
            pd.to_datetime(fila["prgfhaviso"])
            if pd.notna(fila["prgfhaviso"])
            else datetime.now()
        )

        dia_en = f_ini.strftime("%A").upper()
        dia_es = DIAS_ESPANOL.get(dia_en, dia_en).lower()
        fecha_larga = f"{dia_es}, {f_ini.day} de {MESES_ESPANOL.get(f_ini.month, 'JUNIO').lower()} de {f_ini.year}"

        sub_ops = df_operaciones[df_operaciones["prgcod"] == fila["prgcod"]]
        ops_lista = []
        for idx, row_op in sub_ops.iterrows():
            ops_lista.append({
                "num": len(ops_lista) + 1,
                "lugar": (
                    row_op["prgopelug"] if pd.notna(row_op["prgopelug"]) else ""
                ),
                "operacion": (
                    row_op["prgopedsc"] if pd.notna(row_op["prgopedsc"]) else ""
                ),
                "efectuado_por": (
                    row_op["prgopeeje"] if pd.notna(row_op["prgopeeje"]) else ""
                ),
                "hora_prog": (
                    row_op["prgopehp"] if pd.notna(row_op["prgopehp"]) else ""
                ),
                "hora_real": (
                    row_op["prgopehr"] if pd.notna(row_op["prgopehr"]) else ""
                ),
            })

        potencia = fila["prgtotkva"] if pd.notna(fila["prgtotkva"]) else "10"
        clientes = fila["prgtotcon"] if pd.notna(fila["prgtotcon"]) else "30"
        ops_lista.append({
            "num": len(ops_lista) + 1,
            "lugar": "",
            "operacion": f"<strong>Potencia Interrumpida:</strong> {potencia} kVA (Afecta a {clientes} clientes).<br>Trabajos sobre Postes BT / Cables BT.",
            "efectuado_por": "RR.PP.",
            "hora_prog": f_fin.strftime("%H:%M"),
            "hora_real": "",
            "es_resumen": True,
        })

        if pd.notna(fila["prglbl"]) and str(fila["prglbl"]).strip() != "":
            num_registro = str(fila["prglbl"]).strip()
        else:
            num_registro = f"{fila['prgcod']}-{f_ini.year}"

        seccion_nativa = str(fila.get("subcod", "")).strip().upper()
        zona_nativa = (
            f"{seccion_nativa} - {str(fila.get('tdciucod', '')).strip().upper()}"
        )
        resp_nativo = str(fila.get("perpmresp", "")).strip().upper()
        azt_nativo = str(fila.get("pernomazt", "")).strip().upper()

        prensa = "Sí" if fila.get("prgavipre") == 1 else "No"
        personal = "Sí" if fila.get("prgaviper") == 1 else "No"
        municipal = "Sí" if fila.get("prgavialc") == 1 else "No"

        solicitudes_lista.append({
            "numero": num_registro,
            "seccion": seccion_nativa if seccion_nativa else "GENERAL",
            "zona": zona_nativa if seccion_nativa else "GENERAL",
            "senor": resp_nativo if resp_nativo else "SIN ASIGNAR",
            "descripcion_completa": str(fila["descripcion"]),
            "hora_desde": f_ini.strftime("%H:%M"),
            "hora_hasta": f_fin.strftime("%H:%M"),
            "fecha_dia": fecha_larga,
            "motivo": (
                str(fila["motivo"]).strip().upper()
                if fila["motivo"]
                else "REEMPLAZO DE TRANSFORMADOR"
            ),
            "proyecto_oc": (
                str(int(fila["prgproynro"]))
                if pd.notna(fila["prgproynro"])
                else ""
            ),
            "cargo_de": (
                fila["prgasigtra"] if pd.notna(fila["prgasigtra"]) else "ENDE S&C"
            ),
            "aprobado_ing": (
                fila["perpmaprb"] if pd.notna(fila["perpmaprb"]) else "SBC"
            ),
            "autorizado_coi": (
                fila["perpmcoi"] if pd.notna(fila["perpmcoi"]) else "GAE"
            ),
            "modalidad": (
                fila["tdmoddsg"] if pd.notna(fila["tdmoddsg"]) else "01"
            ),
            "fecha_emision": f_emision.strftime("%d/%m/%Y"),
            "operador": "J. HUARACHI",
            "publicado_prensa": prensa,
            "aviso_personal": personal,
            "aviso_municipal": municipal,
            "nombre_azt": azt_nativo if azt_nativo else "SIN ASIGNAR",
            "operaciones": ops_lista,
        })
    return solicitudes_lista


# ==========================================
# DECLARACIÓN DE COLUMNAS PRINCIPALES (1:3.2)
# ==========================================
col_izquierda, col_derecha = st.columns([1, 3.2])

if "vista_actual" not in st.session_state:
    st.session_state["vista_actual"] = "operaciones"

# --- COLUMNA IZQUIERDA: MENÚ, LOGOUT & SOPORTE ---
with col_izquierda:
    st.markdown('<div class="menu-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="menu-title">Módulos del Sistema</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "📄 Panel de Operaciones", key="btn_op", use_container_width=True
    ):
        st.session_state["vista_actual"] = "operaciones"
        st.rerun()

    if st.button(
        "📊 Analizador de Cortes", key="btn_an", use_container_width=True
    ):
        st.session_state["vista_actual"] = "analizador"
        st.rerun()

    st.markdown(
        "<hr style='border:0; border-top: 1px solid var(--border-color); margin: 15px 0;'>",
        unsafe_allow_html=True,
    )

    if st.button("🚪 Cerrar Sesión", key="btn_logout", use_container_width=True):
        modal_confirmar_logout()

    st.markdown("</div>", unsafe_allow_html=True)

    es_analizador = st.session_state.get("vista_actual") == "analizador"
    clase_p1 = "oculto" if es_analizador else "visible"
    clase_p2 = "visible" if es_analizador else "oculto"

    st.markdown(
        f"""<div class="contact-card">
            <div style="margin-bottom: 12px; display: flex; justify-content: center; align-items: center;">
            <img src="app/static/logo_blanco.png" alt="DELAPAZ" style="height: 42px; width: auto; object-fit: contain; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.2));">
            </div>
            <h3>Departamento de Comunicaciones y RRPP</h3>
            <div class="personaje-container">
            <img src="app/static/personaje.png" alt="Ingeniero Operaciones" class="personaje-img {clase_p1}">
            <img src="app/static/personaje2.png" alt="Ingeniero Analítica" class="personaje-img {clase_p2}">
            </div>
            </div>""",
        unsafe_allow_html=True,
    )

# --- COLUMNA DERECHA: CONTENEDOR DE CONTENIDO ---
with col_derecha:
    with st.container(border=True):

        if st.session_state["vista_actual"] == "operaciones":
            st.markdown(
                '<h3 class="canvas-title">Módulo de Exportación de Cortes de Energía</h3>',
                unsafe_allow_html=True,
            )

            col_fecha_p1, col_estado_p1 = st.columns([2.5, 1.5])
            with col_fecha_p1:
                rango_p1 = st.date_input(
                    "Ventana de Publicación",
                    [datetime.now(), datetime.now()],
                    format="DD/MM/YYYY",
                    key="rango_prensa",
                )

            with col_estado_p1:
                ESTADOS_DB = {
                    "TODOS": "TODOS",
                    "A": "Aprobado",
                    "P": "Pendiente",
                    "C": "Concluido",
                    "R": "Registrado",
                    "X": "Anulado",
                }

                estado_p1 = st.selectbox(
                    "Estado en Base de Datos",
                    options=list(ESTADOS_DB.keys()),
                    format_func=lambda clave: ESTADOS_DB[clave],
                    index=1,
                    key="estado_prensa",
                )

            f_ini_p1 = rango_p1[0] if len(rango_p1) > 0 else datetime.now()
            f_fin_p1 = rango_p1[1] if len(rango_p1) == 2 else f_ini_p1

            df_p1 = extraer_datos_db(f_ini_p1, f_fin_p1, estado_p1)

            if df_p1.empty:
                st.info("ℹ️ No se registran cortes en este rango.")
            else:
                st.success(
                    f"✓ Conexión establecida. Registros encontrados: {len(df_p1)}"
                )

                df_vista = df_p1.copy()

                # Generación de la columna de correlativos 1..N
                df_vista["#"] = range(1, len(df_vista) + 1)

                df_vista["Sistema"] = df_vista.apply(
                    lambda row: homologar_sistema(
                        re.match(r"^\((.*?)\)", str(row["descripcion"])).group(1)
                        if re.match(r"^\((.*?)\)", str(row["descripcion"]))
                        else "",
                        row.get("tdciucod", "")
                    ),
                    axis=1
                )
                df_vista["Zonas Normalizadas"] = df_vista["descripcion"].apply(
                    normalizar_texto_zonas
                )

                # Renombrado de columnas para la vista
                df_vista = df_vista.rename(
                    columns={"prgfhapr": "Autorizado", "prglbl": "SOR"}
                )

                columnas_vista = [
                    "#",
                    "Incluir en Reporte",
                    "Exportado Por",
                    "SOR",
                    "inicio",
                    "fin",
                    "Autorizado",
                    "Sistema",
                    "Zonas Normalizadas",
                    "motivo",
                ]

                # Editor interactivo con Checkbox
                df_editado = st.data_editor(
                    df_vista[columnas_vista],
                    column_config={
                        "#": st.column_config.NumberColumn(
                            "#",
                            help="Número correlativo de registro",
                            disabled=True,
                            format="%d",
                        ),
                        "Incluir en Reporte": st.column_config.CheckboxColumn(
                            "Incluir en Reporte",
                            help="Selecciona para incluir este corte en las exportaciones Word/HTML",
                            default=True,
                        ),
                        "Exportado Por": st.column_config.TextColumn(
                            "Exportado Por",
                            help="Usuarios y formato con el que ya se ha generado el reporte de este corte",
                            disabled=True,
                        ),
                        "SOR": st.column_config.TextColumn(disabled=True),
                        "inicio": st.column_config.DatetimeColumn(
                            disabled=True
                        ),
                        "fin": st.column_config.DatetimeColumn(disabled=True),
                        "Autorizado": st.column_config.DatetimeColumn(
                            disabled=True
                        ),
                        "Sistema": st.column_config.TextColumn(disabled=True),
                        "Zonas Normalizadas": st.column_config.TextColumn(
                            disabled=True
                        ),
                        "motivo": st.column_config.TextColumn(disabled=True),
                    },
                    disabled=[
                        c for c in columnas_vista if c != "Incluir en Reporte"
                    ],
                    use_container_width=True,
                    hide_index=True,
                    key="editor_cortes",
                )

                # Mapear estado editado de las casillas de verificación al dataframe principal
                df_p1["Incluir en Reporte"] = df_editado["Incluir en Reporte"]

                # Filtrar los seleccionados (marcados como True)
                df_p1_seleccionados = df_p1[
                    df_p1["Incluir en Reporte"] == True
                ].copy()

                st.markdown(
                    "<hr style='border: 0; border-top: 1px solid var(--border-color); margin: 30px 0;'>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<h3 class="canvas-subtitle">COMPILACIÓN Y EXPORTACIÓN</h3>',
                    unsafe_allow_html=True,
                )

                col_acc1, col_acc2 = st.columns(2)
                with col_acc1:
                    st.markdown(
                        "<p style='font-size:13px; margin-bottom:12px;'><strong>Generar Lote HTML para Impresión Física:</strong> Compila las boletas completas con su listado de operaciones individuales.</p>",
                        unsafe_allow_html=True,
                    )
                    if st.button("Lanzar Compilación HTML", key="btn_html"):
                        if df_p1_seleccionados.empty:
                            st.warning(
                                "⚠️ Debes seleccionar al menos un corte en la tabla para exportar."
                            )
                        else:
                            with st.spinner("Procesando operaciones detalladas..."):
                                lista_codigos = df_p1_seleccionados[
                                    "prgcod"
                                ].tolist()
                                df_ops = extraer_operaciones_lote(lista_codigos)
                                solicitudes_data = construir_datos_html(
                                    df_p1_seleccionados, df_ops
                                )

                                try:
                                    with open(
                                        "reporte-operaciones/reporte.html",
                                        "r",
                                        encoding="utf-8",
                                    ) as f:
                                        template_html = f.read()
                                    with open(
                                        "reporte-operaciones/reporte.css",
                                        "r",
                                        encoding="utf-8",
                                    ) as f:
                                        css_contenido = f.read()

                                    from jinja2 import Template

                                    jinja_template = Template(template_html)
                                    html_final = jinja_template.render(
                                        solicitudes=solicitudes_data,
                                        css_estilos=css_contenido,
                                    )

                                    ruta_salida = (
                                        "reporte-operaciones/lote_compilado.html"
                                    )
                                    with open(
                                        ruta_salida, "w", encoding="utf-8"
                                    ) as f:
                                        f.write(html_final)

                                    usr_id_actual = st.session_state.get(
                                        "usuario_info", {}
                                    ).get("usr_id")
                                    # Registro explícito del formato HTML
                                    registrar_cortes_exportados(
                                        lista_codigos, usr_id_actual, "HTML"
                                    )

                                    st.success(
                                        "🎉 HTML Compilado con éxito y registrado en la base de datos."
                                    )

                                    fecha_ini_str = f_ini_p1.strftime("%Y%m%d")
                                    if f_fin_p1 and f_fin_p1 != f_ini_p1:
                                        nombre_html = f"Compilado_Sor_{fecha_ini_str}_a_{f_fin_p1.strftime('%Y%m%d')}.html"
                                    else:
                                        nombre_html = f"Compilado_Sor_{fecha_ini_str}.html"

                                    with open(ruta_salida, "rb") as file_html:
                                        st.download_button(
                                            label="Descargar Archivo HTML",
                                            data=file_html,
                                            file_name=nombre_html,
                                            mime="text/html",
                                        )
                                except Exception as html_err:
                                    st.error(f"Error: {html_err}")

                with col_acc2:
                    st.markdown(
                        "<p style='font-size:13px; margin-bottom:12px;'><strong>Reporte para Medios de Prensa (Word):</strong> Consolida y agrupa la información de manera amigable para el público.</p>",
                        unsafe_allow_html=True,
                    )
                    if df_p1_seleccionados.empty:
                        st.info(
                            "ℹ️ Selecciona casillas en la tabla para habilitar la vista de reportes."
                        )
                    else:
                        reporte_estructurado = procesar_y_agrupar(
                            df_p1_seleccionados
                        )
                        try:
                            # 1. Construcción dinámica de la fecha actual de emisión
                            fecha_actual = datetime.now()
                            dia_act = fecha_actual.day
                            mes_act = MESES_ESPANOL.get(fecha_actual.month, "JULIO").lower()
                            anio_act = fecha_actual.year
                            fecha_pie_str = f"La Paz, {dia_act} de {mes_act} de {anio_act}"

                            # 2. Render de plantilla Word con contexto
                            doc = DocxTemplate("plantilla_cortes.docx")
                            contexto = {
                                "reporte_agrupado": reporte_estructurado,
                                "fecha_emision_pie": fecha_pie_str,
                            }
                            doc.render(contexto)

                            target_stream = BytesIO()
                            doc.save(target_stream)
                            target_stream.seek(0)

                            fecha_ini_str = f_ini_p1.strftime("%Y%m%d")
                            if f_fin_p1 and f_fin_p1 != f_ini_p1:
                                nombre_word = f"Aviso_Cortes_{fecha_ini_str}_a_{f_fin_p1.strftime('%Y%m%d')}.docx"
                            else:
                                nombre_word = f"Aviso_Cortes_{fecha_ini_str}.docx"

                            if st.download_button(
                                label="Descargar Documento Word",
                                data=target_stream,
                                file_name=nombre_word,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            ):
                                usr_id_actual = st.session_state.get(
                                    "usuario_info", {}
                                ).get("usr_id")
                                lista_codigos = df_p1_seleccionados[
                                    "prgcod"
                                ].tolist()
                                # Registro explícito del formato DOCX
                                registrar_cortes_exportados(
                                    lista_codigos, usr_id_actual, "DOCX"
                                )
                                st.success(
                                    "🎉 Documento Word descargado y registrado."
                                )
                                st.rerun()

                        except Exception as e:
                            st.error(f"Error al procesar plantilla Word: {e}")

        elif st.session_state["vista_actual"] == "analizador":
            st.markdown(
                '<h3 class="canvas-title">Métricas y analíticas de cortes de energía</h3>',
                unsafe_allow_html=True,
            )

            rango_p2 = st.date_input(
                "Periodo de Análisis",
                [datetime.now() - timedelta(days=30), datetime.now()],
                format="DD/MM/YYYY",
                key="rango_dashboard",
            )
            f_ini_p2 = (
                rango_p2[0]
                if len(rango_p2) > 0
                else datetime.now() - timedelta(days=30)
            )
            f_fin_p2 = (
                rango_p2[1] if len(rango_p2) == 2 else datetime.now()
            )

            df_p2 = extraer_datos_db(f_ini_p2, f_fin_p2)

            if df_p2.empty:
                st.info("ℹ No se registran cortes en este rango temporal.")
            else:
                import plotly.express as px

                df_analisis = df_p2.copy()
                df_analisis["inicio"] = pd.to_datetime(df_analisis["inicio"])
                df_analisis["fin"] = pd.to_datetime(df_analisis["fin"])
                df_analisis["duracion_horas"] = (
                    df_analisis["fin"] - df_analisis["inicio"]
                ).dt.total_seconds() / 3600

                df_analisis["Sistema"] = df_analisis.apply(
                    lambda row: homologar_sistema(
                        re.match(r"^\((.*?)\)", str(row["descripcion"])).group(1)
                        if re.match(r"^\((.*?)\)", str(row["descripcion"]))
                        else "",
                        row.get("tdciucod", "")
                    ),
                    axis=1
                )

                df_analisis = df_analisis[
                    df_analisis["Sistema"] != "SISTEMA GENERAL"
                ]

                col_kpi1, col_kpi2 = st.columns(2)
                with col_kpi1:
                    st.metric("Total Interrupciones", len(df_analisis))
                with col_kpi2:
                    st.metric(
                        "Duración Promedio de Corte",
                        f"{round(df_analisis['duracion_horas'].mean(), 1)} hrs",
                    )

                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    df_conteo = (
                        df_analisis.groupby("Sistema")
                        .size()
                        .reset_index(name="Cantidad")
                    )

                    fig_bar = px.bar(
                        df_conteo,
                        x="Sistema",
                        y="Cantidad",
                        title="Distribución de Cortes por Sistema",
                        color="Sistema",
                        text_auto=True,
                        color_discrete_sequence=[
                            "#052E2B",
                            "#E04F1D",
                            "#A8C591",
                            "#526361",
                        ],
                    )

                    fig_bar.update_traces(
                        textfont_size=14,
                        textposition="outside",
                        hovertemplate="<b>%{x}</b><br>Total Cortes: %{y}<extra></extra>",
                    )

                    fig_bar.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=(
                            "white"
                            if st.get_option("theme.base") == "dark"
                            else "black"
                        ),
                        yaxis_title="Cantidad de Cortes",
                    )

                    st.plotly_chart(
                        fig_bar,
                        use_container_width=True,
                        config=CONFIG_PLOTLY_ES,
                    )

                with col_g2:
                    df_linea = df_analisis.copy()
                    df_linea["fecha_dia"] = df_linea["inicio"].dt.date
                    df_tendencia = (
                        df_linea.groupby(["fecha_dia", "Sistema"])
                        .size()
                        .reset_index(name="cantidad_cortes")
                    )

                    fig_lineas = px.line(
                        df_tendencia,
                        x="fecha_dia",
                        y="cantidad_cortes",
                        color="Sistema",
                        title="Frecuencia Operativa",
                        color_discrete_sequence=[
                            "#E04F1D",
                            "#052E2B",
                            "#A8C591",
                        ],
                    )
                    fig_lineas.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=(
                            "white"
                            if st.get_option("theme.base") == "dark"
                            else "black"
                        ),
                    )

                    st.plotly_chart(
                        fig_lineas,
                        use_container_width=True,
                        config=CONFIG_PLOTLY_ES,
                    )

# ==========================================
# PIE DE PÁGINA (FOOTER)
# ==========================================
st.markdown(
    """
    <div class="custom-footer">
        <div class="footer-brand">DELAPAZ — Departamento de Comunicaciones y RRPP</div>
        <div>Plataforma de Consulta y de Cortes de Energía © 2026</div>
        <div class="footer-author">Desarrollado: Efrain Callizaya - 75866754</div>
    </div>
    """,
    unsafe_allow_html=True,
)