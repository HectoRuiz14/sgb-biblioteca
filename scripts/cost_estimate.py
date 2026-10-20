"""Estimación de costos del LLM. ACTUALIZA los precios con los vigentes (Google AI Studio / OpenAI) antes de citarlos."""
INPUT_PRICE_PER_1M = 0.30    # USD por 1M tokens de entrada  (VERIFICAR precio actual)
OUTPUT_PRICE_PER_1M = 2.50   # USD por 1M tokens de salida   (VERIFICAR precio actual)
AVG_INPUT_TOKENS = 400       # reemplazar por el promedio real de compare_prompts.py
AVG_OUTPUT_TOKENS = 150
CALLS_PER_DAY = 200

per_call = AVG_INPUT_TOKENS / 1e6 * INPUT_PRICE_PER_1M + AVG_OUTPUT_TOKENS / 1e6 * OUTPUT_PRICE_PER_1M
print(f"Cost per call: ${per_call:.6f}\nDaily ({CALLS_PER_DAY} calls): ${per_call*CALLS_PER_DAY:.4f}\nMonthly (30 days): ${per_call*CALLS_PER_DAY*30:.2f}")
