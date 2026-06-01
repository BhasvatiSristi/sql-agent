"""
agent.py
========
Core agent pipeline.

It does 4 things in order:
  1. Connect to orders.db via LangChain's SQLDatabase wrapper
  2. Set up the LLM (Mistral, temperature=0)
  3. Create SQL tools via SQLDatabaseToolkit
  4. Build a tool-calling agent manually (Mistral-compatible)

WHY WE BUILD THE AGENT MANUALLY (not create_sql_agent):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  create_sql_agent internally appends an extra assistant message at
  the end of the prompt. Mistral's API strictly requires the LAST
  message to be from the user or a tool — never the assistant.
  This causes the 400 error: "Expected last role User or Tool".

  The fix: build the agent ourselves using:
    create_tool_calling_agent  → wires LLM + tools + a clean prompt
    AgentExecutor              → runs the reasoning loop

  We construct the prompt as:
    [SystemMessage(SYSTEM_PROMPT),
     HumanMessage("{input}"),
     MessagesPlaceholder("agent_scratchpad")]

  "agent_scratchpad" is where LangChain writes intermediate tool
  calls and results — it always ends with a ToolMessage (user role),
  so Mistral never sees an assistant message last. Problem solved.

HOW THE AGENT REASONS:
━━━━━━━━━━━━━━━━━━━━━━
  The agent uses native tool-calling (structured JSON), not text parsing:
    Tool Call   → {"name": "sql_db_query", "args": {"query": "SELECT ..."}}
    Observation → tool result fed back as a ToolMessage
    ... repeats until the agent produces a plain text Final Answer ...

HOW TOOL SELECTION WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━
  The agent chooses from 4 tools provided by SQLDatabaseToolkit:

    sql_db_list_tables   → "What tables exist in this database?"
    sql_db_schema        → "What columns does the orders table have? Show me samples."
    sql_db_query_checker → "Is this SQL valid before I run it?"
    sql_db_query         → "Run this SQL and return the result rows."

  A typical flow for "top 5 cities by revenue":
    1. sql_db_schema       (understand columns + sample rows)
    2. sql_db_query_checker (validate the GROUP BY query)
    3. sql_db_query        (execute it, get rows back)
    → Final Answer         (interpret rows in plain English)
"""

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_mistralai import ChatMistralAI
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import DB_PATH, MODEL_NAME, TEMPERATURE, VERBOSE
from prompts import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Connect to the database
# ─────────────────────────────────────────────────────────────────────────────
def get_database() -> SQLDatabase:
    """
    SQLDatabase is LangChain's thin wrapper around SQLAlchemy.

    include_tables=["orders"]
      → Only exposes the orders table. Prevents accidental access
        to other tables and keeps the schema context small.

    sample_rows_in_table_info=3
      → The agent sees 3 real data rows when it calls sql_db_schema.
        This helps the LLM understand what actual values look like
        (city names, food categories, status strings, etc).
    """
    db = SQLDatabase.from_uri(
        f"sqlite:///{DB_PATH}",
        include_tables=["orders"],
        sample_rows_in_table_info=3,
    )
    return db


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Set up the LLM
# ─────────────────────────────────────────────────────────────────────────────
def get_llm() -> ChatMistralAI:
    """
    ChatMistralAI reads MISTRAL_API_KEY from the environment automatically.

    temperature=0 → fully deterministic, same question = same SQL every time.
    Always use 0 for SQL agents: precision over creativity.
    """
    return ChatMistralAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Create the SQL tools
# ─────────────────────────────────────────────────────────────────────────────
def get_tools(db: SQLDatabase, llm: ChatMistralAI) -> list:
    """
    SQLDatabaseToolkit wraps the DB connection into 4 callable tools:

      sql_db_list_tables    → lists available tables
      sql_db_schema         → returns CREATE TABLE + sample rows
      sql_db_query_checker  → validates SQL before running (uses LLM)
      sql_db_query          → executes SQL and returns results

    INTERVIEW POINT:
      The agent never runs SQL directly — it calls tools which call
      db.run(sql). Swap SQLite for Postgres by changing the URI only.
    """
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Build the agent
# ─────────────────────────────────────────────────────────────────────────────
def build_agent(llm: ChatMistralAI, tools: list) -> AgentExecutor:
    """
    Builds the agent manually using create_tool_calling_agent.

    WHY NOT create_sql_agent?
      create_sql_agent appends an assistant message at the end of its
      internal prompt. Mistral's API returns HTTP 400 if the last message
      is from the assistant — it requires the conversation to end with a
      user or tool message. Building the prompt ourselves gives us full
      control over message ordering.

    THE PROMPT STRUCTURE:
      We use ChatPromptTemplate with exactly 3 slots:

        1. SystemMessage  → SYSTEM_PROMPT (schema + business rules)
           This is sent once, at the top. Tells the agent everything
           about the database before it sees the user's question.

        2. HumanMessage("{input}")
           The user's actual question, injected at runtime.

        3. MessagesPlaceholder("agent_scratchpad")
           LangChain writes tool calls and tool results here during
           the reasoning loop. Tool results are ToolMessages (treated
           as user-role by Mistral), so the conversation always ends
           with a non-assistant message. This is what fixes the 400.

    TWO COMPONENTS:
      create_tool_calling_agent(llm, tools, prompt)
        → Wires the LLM to the tools using native function-calling.
          Returns a Runnable (the reasoning logic). Does NOT execute yet.

      AgentExecutor(agent, tools, ...)
        → The runtime loop. Calls the agent, runs whichever tool it
          picks, feeds the result back, repeats until Final Answer.
    """
    # Build the prompt — message order matters for Mistral
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),          # Schema + rules — sent once at top
        ("human", "{input}"),               # User's question
        MessagesPlaceholder("agent_scratchpad"),  # Tool calls + results go here
    ])

    # Wire LLM + tools + prompt into a reasoning chain (not yet executable)
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    # Wrap in AgentExecutor — this runs the actual tool-calling loop
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=VERBOSE,              # Print every tool call and result
        handle_parsing_errors=True,   # Recover gracefully from bad LLM output
        max_iterations=10,            # Safety cap — prevents infinite loops
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — API/frontend runner (returns dict, no printing)
# ─────────────────────────────────────────────────────────────────────────────
def run_query_streamlit(agent_executor: AgentExecutor, question: str) -> dict:
    """
    Executes one natural-language analytics question and returns
    a structured response for API/frontends.

    Returns:
        {
            "question": str,
            "sql":      str | None,
            "answer":   str,
            "steps":    list of (tool_name, tool_input, observation),
            "error":    bool
        }
    """
    result = _execute_query(agent_executor, question)
    return {
        "question": question,
        "sql":      result["sql"],
        "answer":   result["answer"],
        "steps":    result["steps"],
        "error":    result["error"],
    }


def _execute_query(agent_executor: AgentExecutor, question: str) -> dict:
    """
    Shared execution path for CLI and Streamlit.

    Returns:
        {
            "sql": str | None,
            "answer": str,
            "steps": list of (tool_name, tool_input, observation),
            "error": bool,
        }
    """
    try:
        raw_result = agent_executor.invoke({"input": question})
        sql_query = _extract_sql(raw_result)

        steps = []
        for action, observation in raw_result.get("intermediate_steps", []):
            tool_name = getattr(action, "tool", "unknown")
            tool_input = getattr(action, "tool_input", "")
            steps.append((tool_name, tool_input, observation))

        return {
            "sql": sql_query,
            "answer": raw_result.get("output", "No answer returned."),
            "steps": steps,
            "error": False,
        }
    except Exception as e:
        return {
            "sql": None,
            "answer": f"Error: {str(e)}",
            "steps": [],
            "error": True,
        }


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — extract the executed SQL from intermediate steps
# ─────────────────────────────────────────────────────────────────────────────
def _extract_sql(result: dict) -> str | None:
    """
    Scans intermediate_steps for sql_db_query tool calls and returns
    the last SQL string found (the agent may refine its query mid-loop).

    With tool-calling, tool_input is a dict: {"query": "SELECT ..."}
    With text ReAct (fallback), tool_input is a plain string.
    """
    sql_query = None
    for action, _ in result.get("intermediate_steps", []):
        if getattr(action, "tool", "") == "sql_db_query":
            tool_input = getattr(action, "tool_input", "")
            if isinstance(tool_input, dict):
                sql_query = tool_input.get("query") or tool_input.get("input", "")
            elif isinstance(tool_input, str):
                sql_query = tool_input
    return sql_query


