# ⚡ Sistema de Automatización y Reportes de Cortes de Energía (`sor_automatizacion`)

Plataforma integral desarrollada en **Python / Streamlit** para la consulta, consolidación, generación automatizada de reportes documentales (`.docx` / `.html`) y visualización ejecutiva para la gestión de interrupciones del servicio eléctrico.

---

## 📂 Estructura del Proyecto

```text
sor_automatizacion/
├── .streamlit/             # Configuración de tema y servidor de Streamlit
├── presentacion/          # Diapositivas dinámicas e insumos (Reveal.js / HTML)
├── reporte-operaciones/   # Módulo / Scripts de procesamiento de operaciones
├── reportes/              # Directorio de salida de documentos generados
├── static/                # Archivos estáticos (imágenes, logos, recursos)
├── app.py                 # Punto de entrada principal de la aplicación
├── interface.py           # Componentes de interfaz gráfica de usuario
├── comprobacion_hash.py   # Script para validación y seguridad de archivos
├── prueba_db_local.py     # Script de pruebas y conexión a Base de Datos
├── plantilla_cortes.docx  # Plantilla oficial Word para generación de avisos
├── styles.css             # Estilos personalizados CSS para la app
└── requirements.txt       # Lista de dependencias del proyecto