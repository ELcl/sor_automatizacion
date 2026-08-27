-- =============================================================================
-- PROYECTO: Plataforma RRPP / Boletines SOR (DELAPAZ)
-- OBJETIVO: Instalación completa de la Base de Datos e Inserción Automática
-- MOTOR:    PostgreSQL 16
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PASO 1: HABILITAR EXTENSIÓN PARA HASHEO NATIVO
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- PASO 2: CREACIÓN DE ESTRUCTURA DE TABLAS E ÍNDICES
-- -----------------------------------------------------------------------------

-- 2.1. Tabla de Usuarios
CREATE TABLE IF NOT EXISTS app_usuario (
    usr_id SERIAL PRIMARY KEY,
    usr_username VARCHAR(50) NOT NULL UNIQUE,
    usr_password_hash VARCHAR(255) NOT NULL,
    usr_nombre_completo VARCHAR(150) NOT NULL,
    usr_cargo VARCHAR(100),
    usr_rol VARCHAR(20) NOT NULL DEFAULT 'OPERADOR', -- 'ADMIN', 'OPERADOR', 'CONSULTA'
    usr_activo BOOLEAN NOT NULL DEFAULT TRUE,
    usr_fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    usr_ultimo_login TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE app_usuario IS 'Almacena credenciales y roles del personal con acceso a la app';


-- 2.2. Tabla de Historial de Cortes Exportados por Registro
CREATE TABLE IF NOT EXISTS public.app_corte_exportado (
    exp_id SERIAL PRIMARY KEY,
    prgcod INTEGER NOT NULL,
    usr_id INTEGER NOT NULL,
    formato_exportacion VARCHAR(10) NOT NULL DEFAULT 'HTML', -- 'DOCX' o 'HTML'
    exp_fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_usuario_exportado 
        FOREIGN KEY (usr_id) 
        REFERENCES public.app_usuario (usr_id) 
        ON DELETE CASCADE,
        
    CONSTRAINT uq_corte_usuario_formato 
        UNIQUE (prgcod, usr_id, formato_exportacion)
);

COMMENT ON TABLE public.app_corte_exportado IS 'Registro histórico de las exportaciones de cortes (boletas HTML o minutas DOCX) por usuario.';
COMMENT ON COLUMN public.app_corte_exportado.prgcod IS 'Código único del programa de corte (sorprogram.prgcod).';
COMMENT ON COLUMN public.app_corte_exportado.usr_id IS 'Identificador del usuario que realizó la exportación.';
COMMENT ON COLUMN public.app_corte_exportado.formato_exportacion IS 'Formato del archivo generado: DOCX (Word) o HTML (Impresión).';
COMMENT ON COLUMN public.app_corte_exportado.exp_fecha IS 'Fecha y hora exactas en que se realizó la exportación.';

CREATE INDEX IF NOT EXISTS idx_corte_exportado_prgcod ON public.app_corte_exportado (prgcod);
CREATE INDEX IF NOT EXISTS idx_corte_exportado_usr_id ON public.app_corte_exportado (usr_id);


-- 2.3. Tabla de Historial General de Reportes Exportados (Lotes)
CREATE TABLE IF NOT EXISTS app_reporte_exportado (
    rep_id SERIAL PRIMARY KEY,
    usr_id INT NOT NULL REFERENCES app_usuario(usr_id) ON DELETE RESTRICT,
    rep_tipo_formato VARCHAR(10) NOT NULL,
    rep_modulo VARCHAR(50) NOT NULL,
    rep_fecha_corte_inicio DATE NOT NULL,
    rep_fecha_corte_fin DATE NOT NULL,
    rep_total_registros INT NOT NULL DEFAULT 0,
    rep_nombre_archivo VARCHAR(255) NOT NULL,
    rep_fecha_exportacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rep_detalles JSONB
);

CREATE INDEX IF NOT EXISTS idx_reporte_usr_id ON app_reporte_exportado(usr_id);
CREATE INDEX IF NOT EXISTS idx_reporte_fecha ON app_reporte_exportado(rep_fecha_exportacion DESC);


-- 2.4. Tabla de Bitácora / Auditoría
CREATE TABLE IF NOT EXISTS app_bitacora_actividad (
    act_id BIGSERIAL PRIMARY KEY,
    usr_id INT REFERENCES app_usuario(usr_id) ON DELETE SET NULL,
    act_accion VARCHAR(100) NOT NULL,
    act_descripcion TEXT,
    act_ip VARCHAR(45),
    act_fecha TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON app_bitacora_actividad(act_fecha DESC);

-- -----------------------------------------------------------------------------
-- PASO 3: INSERCIÓN CON HASHEO AUTOMÁTICO (bf = Blowfish / Bcrypt)
-- -----------------------------------------------------------------------------

INSERT INTO app_usuario (usr_username, usr_password_hash, usr_nombre_completo, usr_cargo, usr_rol, usr_activo)
VALUES 
(
    'root', 
    crypt('r00t_2026', gen_salt('bf', 12)), 
    'Administrador del Sistema', 
    'Super Administrador', 
    'ADMIN',
    TRUE
),
(
    'vladimir.castillo', 
    crypt('comunicaciones_0', gen_salt('bf', 12)), 
    'Vladimir Castillo', 
    'Analista de Comunicaciones', 
    'OPERADOR',
    TRUE
),
(
    'julio.ochave', 
    crypt('comunicaciones_1', gen_salt('bf', 12)), 
    'Julio Ochave', 
    'Operador RRPP', 
    'OPERADOR',
    TRUE
),
(
    'marco.camacho', 
    crypt('comunicaciones_2', gen_salt('bf', 12)), 
    'Marco Camacho', 
    'Operador RRPP', 
    'OPERADOR',
    TRUE
)
ON CONFLICT (usr_username) DO UPDATE 
SET usr_password_hash = EXCLUDED.usr_password_hash,
    usr_activo = EXCLUDED.usr_activo;

-- -----------------------------------------------------------------------------
-- PASO 4: VERIFICACIÓN
-- -----------------------------------------------------------------------------
SELECT usr_id, usr_username, usr_nombre_completo, usr_cargo, usr_rol, usr_activo 
FROM app_usuario 
ORDER BY usr_id ASC;