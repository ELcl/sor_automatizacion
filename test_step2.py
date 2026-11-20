from llm_service import obtener_datos_operativos_db, generar_diagnostico_operativo

print("1. Conectando a PostgreSQL y extrayendo métricas reales...")
resumen, criticos = obtener_datos_operativos_db()

print(f"   - Total cortes detectados en BD: {resumen.get('total_cortes', 0)}")
print(f"   - Eventos críticos recuperados: {len(criticos)}")

print("\n2. Enviando datos reales a Gemini...")
diagnostico = generar_diagnostico_operativo(resumen, criticos)

print("\n--- DIAGNÓSTICO BASADO EN TU BASE DE DATOS ---")
print(diagnostico)