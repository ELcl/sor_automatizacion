from llm_service import generar_diagnostico_operativo

# Datos de prueba simulando la consulta a la BD
resumen_mock = {
    'total_cortes': 42,
    'duracion_total_hrs': 18.5,
    'saidi_promedio_min': 26.4,
    'causa_principal': 'Falla por descargas atmosféricas / Clima'
}

cortes_mock = [
    {"alimentador": "ALM-04", "duracion_min": 140, "usuarios_afectados": 1200, "motivo": "Caída de rama sobre línea MP"},
    {"alimentador": "ALM-12", "duracion_min": 95, "usuarios_afectados": 850, "motivo": "Actuación de reconectador por sobrecorriente"}
]

print("⏳ Solicitando diagnóstico sintético a Gemini...")
resultado = generar_diagnostico_operativo(resumen_mock, cortes_mock)

print("\n--- DIAGNÓSTICO OBTENIDO ---")
print(resultado)