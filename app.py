"""
app.py
======
Streamlit frontend for the AI SQL Agent.

Run with:
    streamlit run app.py

HOW THIS WORKS:
  - The agent (database + LLM + tools) is initialised ONCE using
    Streamlit's @st.cache_resource — not rebuilt on every interaction.
  - Each question triggers agent.run_query_streamlit() which returns
    the SQL + answer as a dict instead of printing to terminal.
  - Chat history is stored in st.session_state and displayed as a
    conversation thread that persists across queries.
  - The reasoning steps (tool calls) are shown in an expander so you
    can inspect the agent's thinking without cluttering the main view.
"""

import streamlit as st
from agent import get_database, get_llm, get_tools, build_agent, run_query_streamlit

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — must be the very first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SQL Agent",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — light theme with uniform example boxes
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── App background ── */
.stApp {
    background-color: #f8f9fa;
    color: #1f2937;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}
[data-testid="stSidebar"] * {
    color: #4b5563 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #1f2937 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Main header ── */
.main-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem;
    font-weight: 600;
    color: #000000 !important;
    letter-spacing: -0.02em;
    padding: 1.2rem 0 0.2rem 0;
}
.main-subheader {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: #000000 !important;
    letter-spacing: 0.08em;
    margin-bottom: 1.8rem;
}

/* ── Chat messages ── */
.user-bubble {
    background: #e0e7ff;
    border: 1px solid #c7d2fe;
    border-left: 3px solid #6366f1;
    border-radius: 4px 12px 12px 4px;
    padding: 0.9rem 1.2rem;
    margin: 1rem 0 0.4rem 0;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.95rem;
    color: #1f2937;
}
.agent-bubble {
    background: #f0fdf4;
    border: 1px solid #dcfce7;
    border-left: 3px solid #22c55e;
    border-radius: 4px 12px 12px 4px;
    padding: 0.9rem 1.2rem;
    margin: 0.4rem 0 0.4rem 0;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.95rem;
    color: #1f2937;
}
.label-user {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #6366f1;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}
.label-agent {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: #22c55e;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

/* ── SQL block ── */
.sql-block {
    background: #fafaf9;
    border: 1px solid #e7e5e4;
    border-top: 2px solid #6366f1;
    border-radius: 0 0 6px 6px;
    padding: 0.8rem 1rem;
    margin: 0.6rem 0 0 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
    color: #6366f1;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
}
.sql-label {
    background: #6366f1;
    color: #fff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    padding: 0.2rem 0.6rem;
    border-radius: 6px 6px 0 0;
    display: inline-block;
    margin-top: 0.8rem;
}

/* ── Example chips ── */
.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin: 0.8rem 0 1rem 0;
}
.chip {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 20px;
    padding: 0.3rem 0.8rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: #4b5563;
    cursor: pointer;
    transition: all 0.15s;
}
.chip:hover {
    border-color: #6366f1;
    color: #6366f1;
}

/* ── Status badge ── */
.status-ok {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #22c55e;
}
.status-err {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #ef4444;
}

/* ── Thinking steps ── */
.step-block {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 0.6rem 0.9rem;
    margin: 0.3rem 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: #6b7280;
    line-height: 1.5;
}
.step-tool {
    color: #d97706;
}
.step-obs {
    color: #0284c7;
}

/* ── Divider ── */
hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1.5rem 0;
}

/* ── Input box ── */
[data-testid="stTextInput"] input {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    color: #1f2937 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.1) !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #9ca3af !important;
}

/* ── Button ── */
button[data-testid="baseButton-secondary"],
button[kind="primary"],
.stButton button,
.stButton > button,
div[data-testid="stColumn"] button {
    background-color: #3b82f6 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s !important;
    min-height: 80px !important;
    height: 80px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    line-height: 1.3 !important;
    flex-wrap: wrap !important;
}
button:hover,
.stButton button:hover,
.stButton > button:hover,
button[kind="primary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
div[data-testid="stColumn"] button:hover {
    background-color: #2563eb !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
}

/* ── Expander (thinking steps) ── */
[data-testid="stExpander"] {
    background: #f9fafb !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
}
[data-testid="stExpander"] summary {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #4b5563 !important;
}

/* ── Scrollable chat area ── */
.chat-container {
    max-height: 62vh;
    overflow-y: auto;
    padding-right: 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: #e5e7eb transparent;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #d1d5db;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
}
.empty-icon {
    font-size: 2.5rem;
    margin-bottom: 0.8rem;
    opacity: 0.4;
}

/* ── Metric cards in sidebar ── */
.metric-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    margin: 0.4rem 0;
}
.metric-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3rem;
    font-weight: 600;
    color: #6366f1;
}
.metric-lbl {
    font-family: 'IBM Plex Sans', monospace;
    font-size: 0.72rem;
    color: #6b7280;
    margin-top: 0.1rem;
}

/* ── Example boxes wrapper ── */
.example-boxes-wrapper {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin: 1rem 0;
}

/* ── Individual example box styling ── */
.example-box {
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 1.5rem;
    background: #ffffff;
    border: 2px solid #6366f1;
    border-radius: 10px;
    cursor: pointer;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.9rem;
    color: #1f2937;
    font-weight: 500;
    transition: all 0.2s ease;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.example-box:hover {
    background: #eef2ff;
    border-color: #4f46e5;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# AGENT INITIALISATION — cached so it only runs once per session
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def init_agent():
    """
    @st.cache_resource caches the return value across all reruns.
    The agent is expensive to build (connects to DB, loads LLM, fetches tools),
    so we build it once and reuse it for every query in the session.
    """
    db = get_database()
    llm = get_llm()
    tools = get_tools(db, llm)
    agent_executor = build_agent(llm, tools)
    return agent_executor


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE — persists across reruns within a session
# ─────────────────────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    # Each entry: {"question": str, "sql": str|None, "answer": str, "steps": list, "error": bool}
    st.session_state.history = []

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🗄️ SQL Agent")
    st.markdown("---")

    # Connection status
    try:
        agent_executor = init_agent()
        st.markdown('<div class="status-ok">● connected · orders.db</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown('<div class="status-err">✕ connection failed</div>', unsafe_allow_html=True)
        st.error(str(e))
        st.stop()

    st.markdown("<br>", unsafe_allow_html=True)

    # Stats
    st.markdown("**Session stats**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{st.session_state.query_count}</div>
            <div class="metric-lbl">queries run</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        errors = sum(1 for h in st.session_state.history if h.get("error"))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{errors}</div>
            <div class="metric-lbl">errors</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Schema reference
    with st.expander("📋 Schema reference", expanded=False):
        st.markdown("""
```
TABLE: orders
─────────────────────────────
order_id           TEXT
customer_id        TEXT
city               TEXT
food_category      TEXT
order_value        REAL
time_of_day        TEXT
order_date         TEXT
order_status       TEXT
delivery_time_mins INTEGER
rating             REAL
revenue_category   TEXT
is_completed       INTEGER
  (1 = completed)
```
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    # Clear history
    if st.button("🗑  Clear history", use_container_width=True):
        st.session_state.history = []
        st.session_state.query_count = 0
        st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-family: IBM Plex Mono, monospace; font-size: 0.65rem; '
        'color: #2d3145; line-height: 1.6;">Powered by<br>LangChain · Mistral<br>SQLite · Streamlit</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">AI SQL Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subheader">▸ ask questions in plain english · get sql + answers</div>', unsafe_allow_html=True)

# ── Example query chips ───────────────────────────────────────────────────────
EXAMPLES = [
    "Total revenue by city",
    "Avg delivery time for completed orders",
    "Top 5 food categories by revenue",
    "City with highest avg rating",
    "How many orders were cancelled?",
    "Revenue breakdown by time of day",
]

st.markdown("**Try an example:**")

# Create uniform example boxes using columns
cols = st.columns(3)  # 3 boxes per row for consistency
for i, example in enumerate(EXAMPLES):
    col_index = i % 3
    with cols[col_index]:
        if st.button(example, key=f"chip_{i}", use_container_width=True, help=f"Run: {example}"):
            st.session_state.pending_query = example
    # Create new row after every 3 boxes
    if (i + 1) % 3 == 0 and i < len(EXAMPLES) - 1:
        cols = st.columns(3)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Chat history display ──────────────────────────────────────────────────────
if not st.session_state.history:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">⌗</div>
        <div>No queries yet.<br>Ask a question above or pick an example.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    for entry in st.session_state.history:
        # User bubble
        st.markdown(f"""
        <div class="user-bubble">
            <div class="label-user">you</div>
            {entry['question']}
        </div>
        """, unsafe_allow_html=True)

        # Agent bubble
        answer_html = entry['answer'].replace('\n', '<br>')
        st.markdown(f"""
        <div class="agent-bubble">
            <div class="label-agent">agent</div>
            {answer_html}
        </div>
        """, unsafe_allow_html=True)

        # SQL block (shown below the answer bubble)
        if entry.get("sql"):
            st.markdown('<div class="sql-label">SQL</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sql-block">{entry["sql"]}</div>', unsafe_allow_html=True)

        # Reasoning steps (collapsible)
        if entry.get("steps"):
            with st.expander(f"🔍 reasoning steps ({len(entry['steps'])} tool calls)", expanded=False):
                for step_num, (tool_name, tool_input, observation) in enumerate(entry["steps"], 1):
                    input_str = tool_input if isinstance(tool_input, str) else str(tool_input)
                    obs_str = str(observation)[:400] + ("..." if len(str(observation)) > 400 else "")
                    st.markdown(f"""
                    <div class="step-block">
                        <span style="color:#6b7280">step {step_num} ·</span>
                        <span class="step-tool"> {tool_name}</span><br>
                        <span style="color:#374151">input: </span><span style="color:#d1d5db">{input_str[:200]}</span><br>
                        <span class="step-obs">obs: {obs_str}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)


# ── Input bar ─────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
input_col, btn_col = st.columns([5, 1])

with input_col:
    user_input = st.text_input(
        label="query",
        label_visibility="collapsed",
        placeholder="Ask a question about your orders data...",
        key="user_input",
        value=st.session_state.pending_query or "",
    )

with btn_col:
    submit = st.button("Run →", use_container_width=True)

# Clear pending query after it's been loaded into the input
if st.session_state.pending_query:
    st.session_state.pending_query = None


# ─────────────────────────────────────────────────────────────────────────────
# QUERY EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
if submit and user_input.strip():
    question = user_input.strip()

    with st.spinner("Thinking..."):
        result = run_query_streamlit(agent_executor, question)

    # Append to history
    st.session_state.history.append(result)
    st.session_state.query_count += 1

    # Rerun to refresh the chat display with the new entry
    st.rerun()