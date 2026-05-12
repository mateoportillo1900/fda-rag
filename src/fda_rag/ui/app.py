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
    pass

from fda_rag.agent.graph import build_graph  # noqa: E402

# ── constants ─────────────────────────────────────────────────────────────────
DRUGS = [
    "Metformin", "Warfarin", "Atorvastatin", "Sertraline", "Semaglutide",
    "Adalimumab", "Amoxicillin", "Prednisone", "Naloxone", "Pembrolizumab",
]

SECTION_META = {
    "boxed warning":      ("🚨", "#ef4444", "#450a0a"),
    "warnings":           ("⚠️", "#f97316", "#431407"),
    "contraindications":  ("🚫", "#fb923c", "#431407"),
    "dosage":             ("💊", "#38bdf8", "#082f49"),
    "adverse":            ("⚡", "#facc15", "#422006"),
    "drug interactions":  ("🔄", "#a78bfa", "#2e1065"),
    "indications":        ("✅", "#4ade80", "#052e16"),
    "description":        ("📋", "#22d3ee", "#083344"),
    "pharmacology":       ("🔬", "#34d399", "#022c22"),
    "clinical":           ("🏥", "#818cf8", "#1e1b4b"),
}

def section_style(section_name: str):
    sl = section_name.lower()
    for key, (icon, color, bg) in SECTION_META.items():
        if key in sl:
            return icon, color, bg
    return "📄", "#60a5fa", "#172554"

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FDA Drug Label Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: #060910; }
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
  #MainMenu, footer { visibility: hidden; }
  header { visibility: visible; background: transparent !important; }
  header[data-testid="stHeader"] { background: transparent !important; }

  /* ── sidebar ── */
  [data-testid="stSidebar"] {
    background: #0a0d14 !important;
    border-right: 1px solid #1a1f2e !important;
  }
  [data-testid="stSidebar"] * { color: #94a3b8; }

  /* ── hero ── */
  .hero {
    background: linear-gradient(135deg, #0f172a 0%, #1a0d2e 40%, #0d1f2d 100%);
    border: 1px solid #1e293b;
    border-radius: 20px;
    padding: 2.5rem 3rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(139,92,246,0.08) 0%, transparent 70%);
    pointer-events: none;
  }
  .hero::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 50%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(14,165,233,0.06) 0%, transparent 70%);
    pointer-events: none;
  }
  .hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(139,92,246,0.15);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #a78bfa;
    letter-spacing: .04em;
    margin-bottom: 14px;
  }
  .hero h1 {
    font-size: 2.4rem;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 12px;
    background: linear-gradient(135deg, #f8fafc 0%, #a78bfa 50%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .hero p {
    font-size: 1rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 600px;
    margin-bottom: 20px;
  }
  .hero-metrics {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }
  .metric {
    display: flex;
    flex-direction: column;
  }
  .metric-val {
    font-size: 1.6rem;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1;
  }
  .metric-label {
    font-size: 10px;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-top: 4px;
  }
  .metric-divider {
    width: 1px;
    background: #1e293b;
    align-self: stretch;
  }
  .hero-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .hbadge {
    font-size: 10px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid;
    letter-spacing: .03em;
  }

  /* ── pipeline steps ── */
  .pipeline {
    display: grid;
    grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr;
    gap: 0;
    align-items: center;
    margin-bottom: 1.5rem;
    background: #0a0d14;
    border: 1px solid #1a1f2e;
    border-radius: 16px;
    padding: 20px 24px;
  }
  .pipe-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 8px;
  }
  .pipe-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }
  .pipe-title {
    font-size: 11px;
    font-weight: 700;
    color: #e2e8f0;
    text-align: center;
  }
  .pipe-sub {
    font-size: 9px;
    color: #475569;
    text-align: center;
    line-height: 1.4;
  }
  .pipe-arrow {
    font-size: 16px;
    color: #1e293b;
    padding: 0 4px;
  }

  /* ── chat messages ── */
  .chat-user {
    background: linear-gradient(135deg, #1e1b4b, #1a0d2e);
    border: 1px solid #312e81;
    border-radius: 16px 16px 4px 16px;
    padding: 14px 18px;
    margin: 8px 0;
    font-size: 14px;
    color: #e2e8f0;
    max-width: 80%;
    margin-left: auto;
  }
  .chat-assistant {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 4px 16px 16px 16px;
    padding: 18px 20px;
    margin: 8px 0;
    font-size: 14px;
    color: #cbd5e1;
    line-height: 1.7;
  }
  .chat-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  /* ── source cards ── */
  .src-card {
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border: 1px solid;
    position: relative;
    transition: all .2s;
  }
  .src-top {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .src-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
  }
  .src-drug { font-size: 13px; font-weight: 700; color: #f1f5f9; }
  .src-section {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid;
    margin-left: auto;
    white-space: nowrap;
  }
  .src-text { font-size: 12px; color: #64748b; line-height: 1.6; }
  .src-score { font-size: 10px; margin-top: 8px; color: #334155; }

  /* ── sidebar elements ── */
  .drug-chip {
    display: inline-block;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    color: #64748b;
    margin: 2px;
    font-weight: 500;
  }
  .sidebar-section {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #334155;
    margin: 16px 0 10px;
  }
  .limit-item {
    display: flex;
    gap: 8px;
    font-size: 11px;
    color: #475569;
    line-height: 1.5;
    margin-bottom: 10px;
    align-items: flex-start;
  }
  .limit-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #dc2626;
    margin-top: 5px;
    flex-shrink: 0;
  }
</style>
""", unsafe_allow_html=True)

# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-tag">⚡ Powered by RAG — Retrieval-Augmented Generation</div>
  <h1>FDA Drug Label<br>Assistant</h1>
  <p>Ask plain-English questions about FDA-approved drug labels and get cited,
  grounded answers — every response traces directly back to official
  <a href="https://dailymed.nlm.nih.gov" style="color:#60a5fa;text-decoration:none;">DailyMed</a> source text.</p>

  <div class="hero-metrics">
    <div class="metric">
      <span class="metric-val">10</span>
      <span class="metric-label">Drug Labels</span>
    </div>
    <div class="metric-divider"></div>
    <div class="metric">
      <span class="metric-val">53</span>
      <span class="metric-label">Label Passages</span>
    </div>
    <div class="metric-divider"></div>
    <div class="metric">
      <span class="metric-val">1024</span>
      <span class="metric-label">Vector Dimensions</span>
    </div>
    <div class="metric-divider"></div>
    <div class="metric">
      <span class="metric-val">70B</span>
      <span class="metric-label">LLM Parameters</span>
    </div>
  </div>

  <div class="hero-badges">
    <span class="hbadge" style="background:#172554;border-color:#1d4ed8;color:#93c5fd;">Voyage AI · Embeddings</span>
    <span class="hbadge" style="background:#052e16;border-color:#16a34a;color:#86efac;">pgvector · Neon</span>
    <span class="hbadge" style="background:#2e1065;border-color:#7c3aed;color:#c4b5fd;">LangGraph · Agent</span>
    <span class="hbadge" style="background:#1c1500;border-color:#d97706;color:#fcd34d;">Groq · Llama 3.3 70B</span>
    <span class="hbadge" style="background:#0d2626;border-color:#0d9488;color:#5eead4;">Streamlit · UI</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── pipeline ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pipeline">
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#1e1b4b;">🧑</div>
    <div class="pipe-title">Ask</div>
    <div class="pipe-sub">Type any drug question</div>
  </div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#082f49;">🔢</div>
    <div class="pipe-title">Embed</div>
    <div class="pipe-sub">Voyage AI voyage-3</div>
  </div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#052e16;">🗄️</div>
    <div class="pipe-title">Search</div>
    <div class="pipe-sub">pgvector cosine search</div>
  </div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#1e1b4b;">🎯</div>
    <div class="pipe-title">Rerank</div>
    <div class="pipe-sub">Voyage AI rerank-2</div>
  </div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#2e1065;">🤖</div>
    <div class="pipe-title">Generate</div>
    <div class="pipe-sub">Groq Llama 3.3 70B</div>
  </div>
  <div class="pipe-arrow">→</div>
  <div class="pipe-step">
    <div class="pipe-icon" style="background:#0d2626;">📄</div>
    <div class="pipe-title">Cited Answer</div>
    <div class="pipe-sub">Grounded in source text</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def render_sources(sources: list) -> None:
    if not sources:
        return
    with st.expander(f"📄 {len(sources)} source passage(s) retrieved", expanded=False):
        for i, src in enumerate(sources, 1):
            drug    = getattr(src, "drug_name",    src["drug_name"]    if isinstance(src, dict) else "")
            section = getattr(src, "section_name", src["section_name"] if isinstance(src, dict) else "")
            text    = getattr(src, "chunk_text",   src["chunk_text"]   if isinstance(src, dict) else "")
            score   = getattr(src, "score",        src["score"]        if isinstance(src, dict) else 0)
            excerpt = text[:400] + ("…" if len(text) > 400 else "")
            icon, color, bg = section_style(section)
            st.markdown(f"""
<div class="src-card" style="background:{bg}22;border-color:{color}33;">
  <div class="src-top">
    <div class="src-icon" style="background:{bg};color:{color};">{icon}</div>
    <div>
      <div class="src-drug">[{i}] {drug}</div>
    </div>
    <span class="src-section" style="color:{color};border-color:{color}33;background:{bg};">{section}</span>
  </div>
  <div class="src-text">{excerpt}</div>
  <div class="src-score">Relevance score: {score:.3f}</div>
</div>
""", unsafe_allow_html=True)


def run_query(question: str) -> tuple[str, list]:
    result = st.session_state.agent.invoke(
        {"question": question, "chunks": [], "answer": ""}
    )
    return result["answer"], result["chunks"]


# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:4px 0 16px;">
  <div style="font-size:18px;font-weight:800;color:#f1f5f9;">💊 FDA Assistant</div>
  <div style="font-size:11px;color:#334155;margin-top:4px;">Drug Label Intelligence</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">Available Drugs</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="margin-bottom:12px;line-height:2.2;">
  <span class="drug-chip">Metformin</span>
  <span class="drug-chip">Warfarin</span>
  <span class="drug-chip">Atorvastatin</span>
  <span class="drug-chip">Sertraline</span>
  <span class="drug-chip">Semaglutide</span>
  <span class="drug-chip">Adalimumab</span>
  <span class="drug-chip">Amoxicillin</span>
  <span class="drug-chip">Prednisone</span>
  <span class="drug-chip">Naloxone</span>
  <span class="drug-chip">Pembrolizumab</span>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── drug filter ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">🔍 Filter by Drug</div>', unsafe_allow_html=True)
    selected_drug = st.selectbox(
        "Focus on one drug",
        ["All drugs"] + DRUGS,
        index=0,
        label_visibility="collapsed",
    )
    if selected_drug != "All drugs":
        st.caption(f"Focusing on **{selected_drug}**")

    st.divider()

    # ── compare ────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">⚖️ Compare Two Drugs</div>', unsafe_allow_html=True)
    drug_a = st.selectbox("Drug A", DRUGS, index=0, key="drug_a")
    drug_b = st.selectbox("Drug B", DRUGS, index=1, key="drug_b")
    compare_topic = st.selectbox(
        "Topic",
        ["interactions", "warnings", "contraindications", "side effects", "dosage"],
        key="compare_topic",
    )
    if st.button("⚖️ Compare", use_container_width=True):
        if drug_a == drug_b:
            st.warning("Pick two different drugs.")
        else:
            st.session_state["prefill"] = (
                f"Compare {drug_a} and {drug_b} — what are the key differences "
                f"in their {compare_topic}?"
            )

    st.divider()

    # ── examples ───────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">💡 Try These</div>', unsafe_allow_html=True)
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

    # ── stack ──────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">⚙️ Stack</div>', unsafe_allow_html=True)
    st.markdown("""
| Layer | Tool |
|-------|------|
| DB | Neon + pgvector |
| Embed | Voyage AI |
| Rerank | Voyage AI |
| Agent | LangGraph |
| LLM | Groq / Llama 3.3 |
| UI | Streamlit |
""")

    st.divider()

    # ── limitations ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">⚠️ Known Limitations</div>', unsafe_allow_html=True)
    st.markdown("""
<div>
  <div class="limit-item"><div class="limit-dot"></div><div><strong style="color:#94a3b8">10 drugs only</strong> — thousands of FDA drugs are not in this database</div></div>
  <div class="limit-item"><div class="limit-dot"></div><div><strong style="color:#94a3b8">Answer quality</strong> — only as good as the 5 passages retrieved</div></div>
  <div class="limit-item"><div class="limit-dot"></div><div><strong style="color:#94a3b8">Data freshness</strong> — labels from May 2026, may not reflect recent updates</div></div>
  <div class="limit-item"><div class="limit-dot"></div><div><strong style="color:#94a3b8">Free tier limits</strong> — may slow under heavy usage</div></div>
  <div class="limit-item"><div class="limit-dot"></div><div><strong style="color:#94a3b8">Not medical advice</strong> — always consult a healthcare provider</div></div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption("Data: [DailyMed](https://dailymed.nlm.nih.gov) · Educational use only")


# ── session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    with st.spinner("Initialising agent…"):
        st.session_state.agent = build_graph()

# ── chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("content"):
            with st.expander("📋 Copy answer", expanded=False):
                st.code(msg["content"], language="text")
        if msg.get("sources"):
            render_sources(msg["sources"])

# ── input ─────────────────────────────────────────────────────────────────────
prefill   = st.session_state.pop("prefill", None)
raw_input = st.chat_input("Ask anything about an FDA drug label…") or prefill

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
        with st.spinner("Searching drug labels…"):
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
