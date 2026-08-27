# ⚡ Sistema de Automatización y Reportes de Cortes de Energía (`sor_automatizacion`)

Plataforma integral desarrollada en **Python / Streamlit** para la consulta, consolidación, generación automatizada de reportes documentales (`.docx` / `.html`) y visualización analítica ejecutiva para la gestión de interrupciones del servicio eléctrico.

---

## 🛠️ Novedades y Mejoras Recientes

- **Gráficas Adaptables (Plotly):** Implementación de fondos transparentes (`rgba(0,0,0,0)`) y esquemas de color adaptables en los gráficos de distribución y frecuencia operativa para garantizar una legibilidad perfecta en modo claro y oscuro.
- **Optimización de Conexión a BD:** Incorporación de parámetros TCP Keep-Alive en las consultas a la base de datos GIS/PostgreSQL para mantener conexiones estables durante largas sesiones.
- **Historial de Exportaciones:** Registro en tiempo real de exportaciones individuales y por lote vinculadas a la sesión del usuario.
- **Normalización de Sistemas:** Clasificación y agrupación automática de zonas pertenecientes al Sistema Mayor, Aroma, Norte y Nuevo.

---

## 📂 Estructura del Proyecto

```text
sor_automatizacion/
├── .streamlit/             # Configuración de tema y servidor de Streamlit
├── presentacion/          # Diapositivas dinámicas e insumos (Reveal.js / HTML)
├── reporte-operaciones/   # Plantillas HTML/CSS y generador de lotes de operaciones
├── reportes/              # Directorio de salida de documentos generados
├── static/                # Archivos estáticos (imágenes, logos, recursos)
├── app.py                 # Punto de entrada principal de la aplicación
├── interface.py           # Interfaz principal, lógica de interfaz y paneles Plotly
├── comprobacion_hash.py   # Script para validación y seguridad de contraseñas/archivos
├── prueba_db_local.py     # Script de pruebas y verificación de conexión PostgreSQL
├── plantilla_cortes.docx  # Plantilla oficial Word para generación de avisos
├── styles.css             # Estilos personalizados CSS para la app
└── requirements.txt       # Lista de dependencias del proyecto