"""12 llamadas reales al LLM (4 preguntas x 3 técnicas) -> results/prompt_comparison.md
Requisitos: servidor corriendo en :8000, GEMINI_API_KEY en .env y `python -m scripts.seed` ejecutado.
Uso: python -m scripts.compare_prompts"""
import pathlib

import httpx

BASE = "http://localhost:8000"
QUESTIONS = ["Do you have books by García Márquez?", "¿Qué libros hay sobre software?",
             "Which Novela books have more than 2 copies available?", "Do you have anything about quantum physics?"]
TECHNIQUES = ["zero-shot", "few-shot", "cot"]

login = httpx.post(f"{BASE}/api/v1/auth/login", json={"email": "demo@sgb.local", "password": "Demo12345"}, timeout=30)
login.raise_for_status()
headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

rows = []
for q in QUESTIONS:
    for t in TECHNIQUES:
        try:
            r = httpx.post(f"{BASE}/api/v1/ai/ask", json={"question": q, "technique": t}, headers=headers, timeout=60)
            d = r.json()
            if r.status_code == 200:
                rows.append((t, q, d["answer"].replace("\n", " "), d["prompt_tokens"], d["completion_tokens"], d["latency_ms"]))
            else:
                rows.append((t, q, f"ERROR {r.status_code}: {d.get('detail')}", 0, 0, 0))
        except httpx.HTTPError as e:
            rows.append((t, q, f"ERROR: {e}", 0, 0, 0))

out = pathlib.Path("results"); out.mkdir(exist_ok=True)
lines = ["| Technique | Question | Answer | In tokens | Out tokens | Latency (ms) | Quality (1-5, fill in) |", "|---|---|---|---|---|---|---|"]
lines += [f"| {t} | {q} | {a} | {i} | {o} | {l} |  |" for t, q, a, i, o, l in rows]
ok = [r for r in rows if r[3]]
if ok:
    lines.append(f"\nAverage input tokens: {sum(r[3] for r in ok)/len(ok):.0f} | average output tokens: {sum(r[4] for r in ok)/len(ok):.0f}")
(out / "prompt_comparison.md").write_text("\n".join(lines), encoding="utf-8")
print(f"{len(rows)} calls -> results/prompt_comparison.md")
