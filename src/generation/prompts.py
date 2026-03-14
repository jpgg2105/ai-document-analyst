"""Prompt templates for the generation pipeline."""

SYSTEM_PROMPT = (
    "You are an expert technical documentation assistant. "
    "Your job is to answer questions based ONLY on the provided context.\n\n"
    "Rules:\n"
    "1. Answer based strictly on the provided context. "
    "Do not use outside knowledge.\n"
    "2. If the context does not contain enough information to answer, say: "
    "\"I don't have enough information in the provided documents "
    'to answer this question."\n'
    "3. Always cite your sources using [Source: filename, Page X] format.\n"
    "4. Be concise and precise. Prefer short, clear answers.\n"
    "5. If the question is ambiguous, state your interpretation "
    "before answering.\n"
    "6. Never fabricate information. If you're unsure, say so."
)

QUERY_TEMPLATE = """Context from retrieved documents:
---
{context}
---

Question: {query}

Provide a clear, well-cited answer based on the context above."""

_NO_INFO_MSG = "I don't have enough information in the provided documents to answer this question."


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM.

    Each chunk is wrapped with source metadata so the model can cite it.
    """
    sections: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        filename = chunk.get("filename", "unknown")
        page = chunk.get("page_number", "?")
        section = chunk.get("section", "")
        text = chunk.get("text", "")

        header = f"[Source {i}: {filename}, Page {page}"
        if section:
            header += f", Section: {section}"
        header += "]"

        sections.append(f"{header}\n{text}")

    return "\n\n".join(sections)


def build_query_prompt(query: str, chunks: list[dict]) -> str:
    """Build the full user prompt including formatted context."""
    context = format_context(chunks)
    return QUERY_TEMPLATE.format(context=context, query=query)
