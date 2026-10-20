"""Plantillas de prompt: zero-shot, few-shot y chain-of-thought."""

SYSTEM = (
    "You are a helpful librarian assistant for a library management system. "
    "Answer ONLY using the catalog context provided. If the answer is not in the context, say you don't have that information. "
    "Answer in the same language as the question."
)

FEW_SHOT = """Here are examples of how to answer:

Context:
- ID 1: "Don Quijote" by Miguel de Cervantes | category: Classic | year: 1605 | available copies: 2 of 2
Question: Do you have books by Cervantes?
Answer: Yes. We have "Don Quijote" by Miguel de Cervantes (2 of 2 copies available).

Context:
(no matching books found in the catalog)
Question: Do you have books about quantum physics?
Answer: I don't have any books about quantum physics in the catalog.
"""


def build_prompt(technique: str, question: str, context: str) -> str:
    base = f"Context:\n{context}\nQuestion: {question}\n"
    if technique == "zero-shot":
        return f"{SYSTEM}\n\n{base}Answer:"
    if technique == "few-shot":
        return f"{SYSTEM}\n\n{FEW_SHOT}\nNow answer this one.\n\n{base}Answer:"
    if technique == "cot":
        return (f"{SYSTEM}\n\n{base}Think step by step: (1) identify what the user asks, (2) check which books in the context match, "
                "(3) check availability. Then give the final answer on a last line starting with 'Final answer:'.")
    raise ValueError(f"Unknown technique: {technique}")
