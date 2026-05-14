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

DRUGS = [
    # Original 10
    "Metformin", "Warfarin", "Atorvastatin", "Sertraline", "Semaglutide",
    "Adalimumab", "Amoxicillin", "Prednisone", "Naloxone", "Pembrolizumab",
    # Added 10
    "Lisinopril", "Levothyroxine", "Amlodipine", "Omeprazole", "Albuterol",
    "Gabapentin", "Escitalopram", "Azithromycin", "Apixaban", "Metoprolol",
]

DRUG_CATEGORIES = {
    "Diabetes / GLP-1":     ["Metformin", "Semaglutide"],
    "Cardiovascular":        ["Warfarin", "Atorvastatin", "Lisinopril", "Amlodipine", "Apixaban", "Metoprolol"],
    "Mental Health":         ["Sertraline", "Escitalopram"],
    "Immunology / Biologic": ["Adalimumab", "Pembrolizumab", "Prednisone"],
    "Antibiotics":           ["Amoxicillin", "Azithromycin"],
    "Neurology / Pain":      ["Gabapentin", "Naloxone"],
    "GI / Metabolic":        ["Omeprazole", "Levothyroxine"],
    "Respiratory":           ["Albuterol"],
}

SECTION_META = {
    "boxed warning":      ("🚨", "#ef4444", "#450a0a"),
    "warnings":           ("⚠️",  "#f97316", "#431407"),
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

st.set_page_config(
    page_title="FDA Drug Label Assistant",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",  # collapsed by default on mobile
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

  .stApp { background: #07090f; }
  .block-container { padding-top: 2rem; max-width: 1100px; }
  #MainMenu, footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent !important; }
  [data-testid="stSidebar"] { background: #090c14 !important; border-right: 1px solid #12172a !important; }

  /* hero */
  .hero {
    border-radius: 18px;
    padding: 2rem 2.25rem 1.75rem;
    margin-bottom: 0.75rem;
    background: #0d1021;
    border: 1px solid #1a2035;
    position: relative;
    overflow: hidden;
  }
  .hero-glow {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background:
      radial-gradient(ellipse 60% 50% at 80% 20%, rgba(124,58,237,0.12) 0%, transparent 70%),
      radial-gradient(ellipse 40% 60% at 10% 80%, rgba(14,165,233,0.08) 0%, transparent 70%);
    pointer-events: none;
  }
  .hero-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.35);
    border-radius: 20px; padding: 4px 12px;
    font-size: 10px; font-weight: 700; color: #a78bfa;
    letter-spacing: .05em; text-transform: uppercase;
    margin-bottom: 12px;
  }
  .hero-title {
    font-size: 2.25rem; font-weight: 900; line-height: 1.05;
    color: #f8fafc; margin-bottom: 10px; position: relative;
  }
  .hero-title span { color: #8b5cf6; }
  .hero-desc { font-size: 0.95rem; color: #94a3b8; line-height: 1.6; margin-bottom: 18px; max-width: 600px; }
  .hero-desc a { color: #60a5fa; text-decoration: none; }
  .hero-desc a:visited { color: #60a5fa; }
  .hero-metrics { display: flex; gap: 0; margin-bottom: 16px; border: 1px solid #1e293b; border-radius: 10px; overflow: hidden; width: fit-content; }
  .hmetric { padding: 10px 20px; text-align: center; border-right: 1px solid #1e293b; }
  .hmetric:last-child { border-right: none; }
  .hmetric-val { font-size: 1.4rem; font-weight: 900; color: #f1f5f9; line-height: 1; }
  .hmetric-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-top: 5px; font-weight: 600; }
  .hero-tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .htag { font-size: 10px; font-weight: 600; padding: 4px 10px; border-radius: 6px; border: 1px solid; }
  .gh-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.04); border: 1px solid #1e293b;
    border-radius: 8px; padding: 5px 13px;
    font-size: 11px; font-weight: 600; color: #94a3b8;
    text-decoration: none; transition: border-color .2s, color .2s;
  }
  .gh-btn:hover { border-color: #334155; color: #e2e8f0; }

  /* pipeline */
  .pipe-wrap {
    background: #0b0e1a; border: 1px solid #1e293b;
    border-radius: 14px; padding: 18px 22px; margin-bottom: 0.75rem;
  }
  .pipe-label {
    font-size: 10px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: #64748b; margin-bottom: 12px;
  }
  .pipe-row { display: flex; align-items: center; gap: 0; }
  .pipe-node { display: flex; flex-direction: column; align-items: center; gap: 7px; flex: 1; }
  .pipe-icon {
    width: 48px; height: 48px; border-radius: 14px;
    display: flex; align-items: center; justify-content: center; font-size: 22px;
    border: 1px solid;
  }
  .pipe-name { font-size: 11px; font-weight: 700; color: #cbd5e1; text-align: center; }
  .pipe-tool { font-size: 9px; color: #334155; text-align: center; line-height: 1.4; }
  .pipe-arr { color: #1e293b; font-size: 18px; padding: 0 6px; flex-shrink: 0; margin-bottom: 20px; }

  /* source cards */
  .src { border-radius: 12px; padding: 16px; margin-bottom: 10px; border: 1px solid; }
  .src-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .src-ico { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
  .src-drug { font-size: 13px; font-weight: 700; color: #f1f5f9; }
  .src-tag { font-size: 9px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; padding: 3px 8px; border-radius: 4px; border: 1px solid; margin-left: auto; white-space: nowrap; }
  .src-body { font-size: 12px; color: #4b5563; line-height: 1.65; }
  .src-score { font-size: 10px; color: #1f2937; margin-top: 8px; }

  /* sidebar */
  .sb-head { font-size: 10px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; color: #94a3b8; margin: 18px 0 10px; }
  .chip { display: inline-block; background: #0f172a; border: 1px solid #1e293b; border-radius: 5px; padding: 3px 9px; font-size: 10px; color: #cbd5e1; margin: 2px; font-weight: 500; }
  .lim { display: flex; gap: 8px; font-size: 11px; color: #94a3b8; margin-bottom: 8px; line-height: 1.5; }
  .lim-dot { width: 5px; height: 5px; border-radius: 50%; background: #ef4444; margin-top: 6px; flex-shrink: 0; }

  /* ── mobile ── */
  @media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem !important; }

    .hero { padding: 1.5rem 1.25rem 1.25rem; border-radius: 14px; }
    .hero-title { font-size: 2rem; }
    .hero-desc { font-size: 0.875rem; margin-bottom: 18px; }
    .hero-pill { font-size: 10px; padding: 4px 10px; margin-bottom: 12px; }

    .hero-metrics {
      width: 100% !important;
      display: grid !important;
      grid-template-columns: 1fr 1fr;
    }
    .hmetric { padding: 10px 8px; }
    .hmetric-val { font-size: 1.3rem; }
    .hmetric:nth-child(2) { border-right: none; }

    .hero-tags { gap: 4px; }
    .htag { font-size: 9px; padding: 3px 8px; }
    .gh-btn { font-size: 10px; padding: 4px 10px; }

    .pipe-wrap { padding: 16px 14px; border-radius: 12px; }
    .pipe-wrap p { font-size: 12px !important; }

    .src { padding: 12px; }
    .src-head { gap: 8px; }
    .src-drug { font-size: 12px; }
    .src-tag { font-size: 8px; }
    .src-body { font-size: 11px; }
  }
</style>
""", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-glow"></div>
  <div class="hero-pill">⚡ Retrieval-Augmented Generation</div>
  <div class="hero-title">FDA Drug Label<br><span>Assistant</span></div>
  <div class="hero-desc">
    Ask plain-English questions about FDA-approved drug labels. Every answer is grounded in official <a href="https://dailymed.nlm.nih.gov" target="_blank">DailyMed</a> source text — zero hallucination.
  </div>
  <div class="hero-metrics">
    <div class="hmetric"><div class="hmetric-val">20</div><div class="hmetric-label">Drug Labels</div></div>
    <div class="hmetric"><div class="hmetric-val">735</div><div class="hmetric-label">Passages</div></div>
    <div class="hmetric"><div class="hmetric-val">1024</div><div class="hmetric-label">Vector Dims</div></div>
    <div class="hmetric"><div class="hmetric-val">70B</div><div class="hmetric-label">LLM Params</div></div>
  </div>
  <div class="hero-tags">
    <span class="htag" style="background:#172554;border-color:#1d4ed8;color:#93c5fd;">Voyage AI · Embeddings</span>
    <span class="htag" style="background:#052e16;border-color:#16a34a;color:#86efac;">pgvector · Neon</span>
    <span class="htag" style="background:#2e1065;border-color:#7c3aed;color:#c4b5fd;">LangGraph · Agent</span>
    <span class="htag" style="background:#1c1500;border-color:#d97706;color:#fcd34d;">Groq · Llama 3.3 70B</span>
    <a class="gh-btn" href="https://github.com/mateoportillo1900/fda-rag" target="_blank">
      <svg height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
      View on GitHub
    </a>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pipe-wrap">
<div class="pipe-label">How it works</div>
<p style="font-size:14px;color:#cbd5e1;line-height:1.65;margin:0 0 12px 0;">
This app uses <b style="color:#f1f5f9;">Retrieval-Augmented Generation (RAG)</b> to ground every answer in
real FDA-approved drug labels from DailyMed — no memorized training data, no hallucinations.
</p>
<p style="font-size:14px;color:#cbd5e1;line-height:1.65;margin:0;">
Your question is embedded by <b style="color:#93c5fd;">Voyage AI</b>, matched against 735 indexed passages in
<b style="color:#86efac;">Neon Postgres</b> with pgvector, reranked, and sent to <b style="color:#c4b5fd;">Groq Llama 3.3 70B</b> with
strict instructions to cite every claim — orchestrated by a <b style="color:#fcd34d;">LangGraph</b> agent.
</p>
</div>
""", unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def render_sources(sources: list) -> None:
    if not sources:
        return
    with st.expander(f"📄 {len(sources)} source passage(s) retrieved", expanded=False):
        for i, src in enumerate(sources, 1):
            drug    = getattr(src, "drug_name",    src["drug_name"]    if isinstance(src, dict) else "")
            section = getattr(src, "section_name", src["section_name"] if isinstance(src, dict) else "")
            text    = getattr(src, "chunk_text",   src["chunk_text"]   if isinstance(src, dict) else "")
            score   = getattr(src, "score",        src["score"]        if isinstance(src, dict) else 0)
            excerpt = text[:420] + ("…" if len(text) > 420 else "")
            icon, color, bg = section_style(section)
            st.markdown(f"""
<div class="src" style="background:{bg}18;border-color:{color}25;">
  <div class="src-head">
    <div class="src-ico" style="background:{bg};color:{color};">{icon}</div>
    <div><div class="src-drug">[{i}] {drug}</div></div>
    <span class="src-tag" style="color:{color};border-color:{color}30;background:{bg};">{section}</span>
  </div>
  <div class="src-body">{excerpt}</div>
  <div class="src-score">Score: {score:.3f}</div>
</div>""", unsafe_allow_html=True)


def run_query(question: str) -> tuple[str, list]:
    result = st.session_state.agent.invoke({"question": question, "chunks": [], "answer": ""})
    return result["answer"], result["chunks"]


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:8px 0 12px">
  <div style="font-size:18px;font-weight:800;color:#f1f5f9;">💊 FDA Assistant</div>
  <div style="font-size:10px;color:#64748b;margin-top:4px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;">Drug Label Intelligence</div>
</div>""", unsafe_allow_html=True)

    # ── 1. Quick examples (lowest-friction way to start)
    st.markdown('<div class="sb-head">💡 Try an example</div>', unsafe_allow_html=True)
    examples = [
        "What are the contraindications for warfarin?",
        "What drug interactions does atorvastatin have?",
        "What is the dosage for amoxicillin?",
        "What are the warnings for lisinopril?",
        "How does apixaban work?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["prefill"] = ex

    st.divider()

    # ── 2. Compare two drugs (next most common action)
    st.markdown('<div class="sb-head">⚖️ Compare two drugs</div>', unsafe_allow_html=True)
    drug_a = st.selectbox("Drug A", DRUGS, index=0, key="drug_a")
    drug_b = st.selectbox("Drug B", DRUGS, index=1, key="drug_b")
    compare_topic = st.selectbox(
        "Topic",
        ["interactions", "warnings", "contraindications", "side effects", "dosage", "mechanism of action"],
        key="compare_topic",
    )
    if st.button("Compare", use_container_width=True, type="primary"):
        if drug_a == drug_b:
            st.warning("Select two different drugs.")
        else:
            st.session_state["prefill"] = (
                f"Compare {drug_a} and {drug_b} — "
                f"what are the key differences in their {compare_topic}?"
            )

    st.divider()

    # ── 3. Optional scope filter
    st.markdown('<div class="sb-head">🔍 Narrow to specific drugs (optional)</div>', unsafe_allow_html=True)
    selected_drugs = st.multiselect(
        "Drugs",
        DRUGS,
        default=[],
        placeholder="All 20 drugs",
        label_visibility="collapsed",
    )

    st.divider()

    # ── 4. Reference (collapsed — only opens if user wants to browse)
    with st.expander(f"📚 Browse all 20 drugs by category"):
        for cat, members in DRUG_CATEGORIES.items():
            st.markdown(
                f'<div style="font-size:10px;color:#94a3b8;font-weight:700;margin:8px 0 4px;">{cat}</div>'
                + '<div>' + ''.join(f'<span class="chip">{d}</span>' for d in members) + '</div>',
                unsafe_allow_html=True,
            )

    with st.expander("⚠️ Limitations"):
        st.markdown("""
<div>
  <div class="lim"><div class="lim-dot"></div><div><b style="color:#94a3b8">20 drugs only</b> — not a complete FDA database</div></div>
  <div class="lim"><div class="lim-dot"></div><div><b style="color:#94a3b8">Top 5 passages</b> — answers limited by retrieval</div></div>
  <div class="lim"><div class="lim-dot"></div><div><b style="color:#94a3b8">Not medical advice</b> — consult a healthcare provider</div></div>
  <div class="lim"><div class="lim-dot"></div><div><b style="color:#94a3b8">Free tier APIs</b> — may slow under heavy load</div></div>
</div>""", unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.caption("Data: [DailyMed](https://dailymed.nlm.nih.gov) · Educational use only")


# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    with st.spinner("Initialising…"):
        st.session_state.agent = build_graph()

# ── CHAT HISTORY ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("content"):
            with st.expander("📋 Copy answer", expanded=False):
                st.code(msg["content"], language="text")
        if msg.get("sources"):
            render_sources(msg["sources"])

# ── INPUT ─────────────────────────────────────────────────────────────────────
prefill   = st.session_state.pop("prefill", None)
raw_input = st.chat_input("Ask anything about an FDA drug label…") or prefill
if raw_input and selected_drugs:
    scope = " and ".join(selected_drugs)
    question = f"[Focus only on {scope}] {raw_input}"
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
                st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
            except Exception as exc:
                err = f"⚠️ Something went wrong: {exc}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err, "sources": []})
