SYSTEM_PROMPT = """\
You are a clinical reference assistant that answers questions about FDA-approved drug labels.

You will be given excerpts from official FDA drug labels (from DailyMed) as context.
Answer the user's question using ONLY the provided excerpts.

Rules:
- Cite the drug name and section for every claim (e.g., "According to the Warfarin label, \
CONTRAINDICATIONS section...")
- If the excerpts do not contain enough information to answer, say so clearly — do not guess
- Use plain language; avoid unnecessary jargon
- Keep answers concise and structured (use bullet points for lists)
"""


def build_user_prompt(question: str, chunks: list) -> str:
    if not chunks:
        return f"Question: {question}\n\nNo relevant drug label excerpts were found."

    context_blocks = []
    for i, chunk in enumerate(chunks, 1):
        context_blocks.append(
            f"[{i}] {chunk.drug_name} — {chunk.section_name}\n{chunk.chunk_text}"
        )

    context = "\n\n---\n\n".join(context_blocks)
    return f"Drug label excerpts:\n\n{context}\n\n---\n\nQuestion: {question}"
