"""
FDA Drug Label Assistant — Streamlit UI
Run: streamlit run src/fda_rag/ui/app.py
"""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

try:
    for key in ("DATABASE_URL", "VOYAGE_API_KEY", "GROQ_API_KEY"):
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # running locally with .env — no secrets.toml needed

from fda_rag.agent.graph import build_graph  # noqa: E402

# ── constants ─────────────────────────────────────────────────────────────────
DRUGS = [
    "Metformin", "Warfarin", "Atorvastatin", "Sertraline", "Semaglutide",
    "Adalimumab", "Amoxicillin", "Prednisone", "Naloxone", "Pembrolizumab",
]

SECTION_META = {
    "boxed warning":      ("🚨", "#991b1b"),
    "warnings":           ("⚠️", "#dc2626"),
    "contraindications":  ("🚫", "#ea580c"),
    "dosage":             ("💊", "#2563eb"),
    "adverse":            ("⚡", "#d97706"),
    "drug interactions":  ("🔄", "#7c3aed"),
    "indications":        ("✅", "#16a34a"),
    "description":        ("📋", "#0891b2"),
    "pharmacology":       ("🔬", "#0d9488"),
    "clinical":           ("🏥", "#6366f1"),
}


def section_style(section_name: str) -> tuple[str, str]:
    sl = section_name.lower()
    for key, (icon, color) in SECTION_META.items():
        if key in sl:
            return icon, color
    return "📄", "#3b82f6"


# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FDA Drug Label Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background-color: #0f1117; }
  .block-container { padding-top: 2rem; }

  .hero {
    background: linear-gradient(135deg, #1a1f2e 0%, #16213e 50%, #0f1117 100%);
    border: 1px solid #2d3748; border-radius: 16px;
    padding: 2rem 2.5rem; margin-bottom: 1.5rem;
  }
  .hero h1 { font-size: 2rem; font-weight: 800; color: #f8fafc; margin: 0 0 0.5rem; }
  .hero p  { font-size: 1rem; color: #94a3b8; margin: 0; line-height: 1.6; }

  .badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 1rem; }
  .badge  { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px; border: 1px solid; }
  .badge-blue   { background:#172554; border-color:#1d4ed8; color:#93c5fd; }
  .badge-green  { background:#052e16; border-color:#16a34a; color:#86efac; }
  .badge-purple { background:#2e1065; border-color:#7c3aed; color:#c4b5fd; }
  .badge-yellow { background:#422006; border-color:#d97706; color:#fcd34d; }
  .badge-red    { background:#450a0a; border-color:#dc2626; color:#fca5a5; }

  .steps-row { display: flex; gap: 12px; margin-bottom: 1.5rem; }
  .step {
    flex: 1; background: #1e2433; border: 1px solid #2d3748;
    border-radius: 12px; padding: 1rem; text-align: center;
  }
  .step .step-num   { font-size: 1.4rem; margin-bottom: 6px; }
  .step .step-title { font-size: 12px; font-weight: 700; color: #e2e8f0; margin-bottom: 4px; }
  .step .step-desc  { font-size: 11px; color: #64748b; line-height: 1.4; }

  .source-card {
    background: #1a1f2e; border: 1px solid #2d3748;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
  }
  .source-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
  .source-icon   { font-size: 16px; }
  .source-drug   { font-size: 13px; font-weight: 700; color: #f1f5f9; }
  .source-section-badge {
    font-size: 10px; font-weight: 600; padding: 2px 8px;
    border-radius: 10px; border: 1px solid; margin-left: auto;
  }
  .source-excerpt { font-size: 12px; color: #94a3b8; line-height: 1.6; }
  .source-score   { font-size: 10px; color: #475569; margin-top: 6px; }

  .drug-pill {
    display: inline-block; background: #1e2433; border: 1px solid #2d3748;
    border-radius: 20px; padding: 3px 10px; font-size: 11px; color: #94a3b8; margin: 2px;
  }

  #MainMenu, footer { visibility: hidden; }
  /* Keep header visible so sidebar toggle button works */
  header { visibility: visible; }
  header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>💊 FDA Drug Label Assistant</h1>
  <p>Ask plain-English questions about FDA-approved drug labels.<br>
  Every answer is grounded in official
  <a href="https://dailymed.nlm.nih.gov" style="color:#60a5fa">DailyMed</a>
  data — no hallucination.</p>
  <div class="badges">
    <span class="badge badge-blue">Voyage AI · Semantic Search</span>
    <span class="badge badge-green">pgvector · Neon Postgres</span>
    <span class="badge badge-purple">LangGraph · Agent</span>
    <span class="badge badge-yellow">Groq · Llama 3.3 70B</span>
    <span class="badge badge-red">10 FDA Drug Labels</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── how it works ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="steps-row">
  <div class="step">
    <div class="step-num">🔍</div>
    <div class="step-title">1. You ask a question</div>
    <div class="step-desc">Type any clinical question about a drug's usage, warnings, or interactions</div>
  </div>
  <div class="step">
    <div class="step-num">📡</div>
    <div class="step-title">2. Semantic search</div>
    <div class="step-desc">Your question is embedded into a vector and matched against label passages in Neon</div>
  </div>
  <div class="step">
    <div class="step-num">🎯</div>
    <div class="step-title">3. Reranking</div>
    <div class="step-desc">Top results are reranked by Voyage AI for maximum relevance</div>
  </div>
  <div class="step">
    <div class="step-num">✍️</div>
    <div class="step-title">4. Cited answer</div>
    <div class="step-desc">Llama 3.3 reads the passages and writes a cited answer — only from source text</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def render_sources(sources: list) -> None:
    if not sources:
        return
    with st.expander(f"📄 {len(sources)} source passage(s) used", expanded=False):
        for i, src in enumerate(sources, 1):
            drug    = getattr(src, "drug_name",    src["drug_name"]    if isinstance(src, dict) else "")
            section = getattr(src, "section_name", src["section_name"] if isinstance(src, dict) else "")
            text    = getattr(src, "chunk_text",   src["chunk_text"]   if isinstance(src, dict) else "")
            score   = getattr(src, "score",        src["score"]        if isinstance(src, dict) else 0)
            excerpt = text[:400] + ("…" if len(text) > 400 else "")
            icon, color = section_style(section)
            st.markdown(f"""
<div class="source-card" style="border-left: 3px solid {color}">
  <div class="source-header">
    <span class="source-icon">{icon}</span>
    <span class="source-drug">[{i}] {drug}</span>
    <span class="source-section-badge" style="color:{color}; border-color:{color}; background:{color}22">{section}</span>
  </div>
  <div class="source-excerpt">{excerpt}</div>
  <div class="source-score">relevance score: {score:.3f}</div>
</div>
""", unsafe_allow_html=True)


def run_query(question: str) -> tuple[str, list]:
    result = st.session_state.agent.invoke(
        {"question": question, "chunks": [], "answer": ""}
    )
    return result["answer"], result["chunks"]


# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Available Drug Labels")
    st.markdown("""
<div style="margin-bottom:12px">
  <span class="drug-pill">Metformin</span>
  <span class="drug-pill">Warfarin</span>
  <span class="drug-pill">Atorvastatin</span>
  <span class="drug-pill">Sertraline</span>
  <span class="drug-pill">Semaglutide</span>
  <span class="drug-pill">Adalimumab</span>
  <span class="drug-pill">Amoxicillin</span>
  <span class="drug-pill">Prednisone</span>
  <span class="drug-pill">Naloxone</span>
  <span class="drug-pill">Pembrolizumab</span>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── drug filter / autocomplete ─────────────────────────────────────────
    st.markdown("### 🔍 Filter by Drug")
    selected_drug = st.selectbox(
        "Focus answers on one drug",
        ["All drugs"] + DRUGS,
        index=0,
        label_visibility="collapsed",
    )
    if selected_drug != "All drugs":
        st.caption(f"Questions will be focused on **{selected_drug}**")

    st.divider()

    # ── compare two drugs ──────────────────────────────────────────────────
    st.markdown("### ⚖️ Compare Two Drugs")
    drug_a = st.selectbox("Drug A", DRUGS, index=0, key="drug_a")
    drug_b = st.selectbox("Drug B", DRUGS, index=1, key="drug_b")
    compare_topic = st.selectbox(
        "Compare by",
        ["interactions", "warnings", "contraindications", "side effects", "dosage"],
        key="compare_topic",
    )
    if st.button("⚖️ Compare", use_container_width=True):
        if drug_a == drug_b:
            st.warning("Please pick two different drugs.")
        else:
            st.session_state["prefill"] = (
                f"Compare {drug_a} and {drug_b} — what are the key differences "
                f"in their {compare_topic}?"
            )

    st.divider()

    # ── example questions ──────────────────────────────────────────────────
    st.markdown("### 💡 Try asking")
    examples = [
        "What are the contraindications for warfarin?",
        "What drug interactions does atorvastatin have?",
        "What is the dosage for amoxicillin?",
        "What are the warnings for prednisone?",
        "What are the adverse reactions for metformin?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["prefill"] = ex

    st.divider()
    st.markdown("### ⚙️ Stack")
    st.markdown("""
| Layer | Tool |
|-------|------|
| Search | pgvector |
| Embed | Voyage AI |
| Rerank | Voyage AI |
| Agent | LangGraph |
| LLM | Groq / Llama 3.3 |
| UI | Streamlit |
""")

    st.divider()

    # ── known limitations ──────────────────────────────────────────────────
    st.markdown("### ⚠️ Known Limitations")
    st.markdown("""
**Drug coverage**
Only 10 of the thousands of FDA-approved drugs are in this database. Questions about any other drug will return irrelevant results.

**Data freshness**
Labels were downloaded in May 2026. Drug labels are updated periodically — this app may not reflect the latest revisions.

**Answer quality**
The AI can only answer from the 5 passages retrieved. If the relevant section wasn't retrieved, the answer will be incomplete or incorrect.

**Not medical advice**
This tool is for educational purposes only. Never make clinical decisions based on this app. Always consult the official [DailyMed](https://dailymed.nlm.nih.gov) label and a qualified healthcare provider.

**Rate limits**
Built on free-tier APIs. Under heavy usage, responses may slow down or temporarily fail.
""")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Data: [DailyMed](https://dailymed.nlm.nih.gov)")
    st.caption("⚠️ For educational purposes only. Not medical advice.")


# ── session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    with st.spinner("Loading…"):
        st.session_state.agent = build_graph()

# ── render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("content"):
            with st.expander("📋 Copy answer", expanded=False):
                st.code(msg["content"], language="text")
        if msg.get("sources"):
            render_sources(msg["sources"])

# ── handle input ──────────────────────────────────────────────────────────────
prefill   = st.session_state.pop("prefill", None)
raw_input = st.chat_input("Ask about any FDA drug label…") or prefill

# Apply drug filter prefix if a specific drug is selected
if raw_input and selected_drug != "All drugs":
    question = f"[Focus only on {selected_drug}] {raw_input}"
else:
    question = raw_input

if question:
    display_question = raw_input or question
    st.session_state.messages.append({"role": "user", "content": display_question, "sources": []})
    with st.chat_message("user"):
        st.markdown(display_question)

    with st.chat_message("assistant"):
        with st.spinner("Searching FDA drug labels…"):
            try:
                answer, sources = run_query(question)

                st.markdown(answer)
                with st.expander("📋 Copy answer", expanded=False):
                    st.code(answer, language="text")
                render_sources(sources)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )

            except Exception as exc:
                error_msg = f"⚠️ Something went wrong: {exc}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg, "sources": []}
                )
