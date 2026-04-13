"""
agent.py
========
The main file. This is the only file you need to understand deeply.

It does 5 things in order:
  1. Connect to orders.db via LangChain's SQLDatabase wrapper
  2. Set up the LLM (OpenAI GPT-4o, temperature=0)
  3. Create SQL tools via SQLDatabaseToolkit
  4. Build a ReAct agent that uses those tools
  5. Run a CLI loop so you can ask questions in plain English

HOW THE REACT LOOP WORKS (know this for interviews):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  The agent alternates between three actions until it has enough information:

    Thought     → "What do I need to know / do next?"
    Action      → Pick a tool (e.g. sql_db_query) and provide its input
    Observation → Read the tool's output

  When the agent is confident, it stops the loop and produces:
    Final Answer → A plain English response to the user's question

HOW TOOL SELECTION WORKS:
━━━━━━━━━━━━━━━━━━━━━━━━━
  The agent chooses from 4 tools provided by SQLDatabaseToolkit:

    sql_db_list_tables   → "What tables exist in this database?"
    sql_db_schema        → "What columns does the orders table have? Show me samples."
    sql_db_query_checker → "Is this SQL valid before I run it?"
    sql_db_query         → "Run this SQL and return the result rows."

  A typical flow for "top 5 cities by revenue":
    1. sql_db_schema     (understand the table structure)
    2. sql_db_query_checker (validate the GROUP BY query it wrote)
    3. sql_db_query      (execute it, get results)
    → Final Answer       (interpret results in plain English)
"""

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_react_agent, AgentExecutor
from langchain_mistralai import ChatMistralAI          # ← Mistral
from langchain import hub

from config import DB_PATH, MODEL_NAME, TEMPERATURE, VERBOSE
from prompts import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Connect to the database
# ─────────────────────────────────────────────────────────────────────────────
def get_database() -> SQLDatabase:
    """
    SQLDatabase is LangChain's thin wrapper around SQLAlchemy.

    What it does:
      - Connects to orders.db via SQLite URI
      - Lets the agent call .get_table_info() to inspect schema
      - Lets the agent call .run() to execute a SQL string safely

    include_tables=["orders"]
      → Only exposes the orders table to the agent.
        Even if orders.db had 10 tables, the agent only sees this one.
        This prevents accidental access and reduces prompt noise.

    sample_rows_in_table_info=3
      → When the agent calls sql_db_schema, it also sees 3 real data rows.
        This helps the LLM understand actual values (e.g. what city names look like).
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
    ChatMistralAI is LangChain's Mistral integration.
    It reads MISTRAL_API_KEY automatically from the environment.

    temperature=0
      → Fully deterministic. Same question → same SQL every time.
        Always use 0 for SQL agents.

    model="mistral-large-latest"
      → Best reasoning and SQL accuracy from Mistral's lineup.
        For faster/cheaper testing, swap to "mistral-small-latest".
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
    SQLDatabaseToolkit wraps your database connection into 4 callable tools.

    These tools are what the agent can USE — the agent picks which one
    to call at each step based on its current reasoning.

    Tools created:
      sql_db_list_tables    → Returns a comma-separated list of table names
      sql_db_schema         → Returns CREATE TABLE statement + sample rows
      sql_db_query_checker  → Validates SQL syntax before execution
      sql_db_query          → Actually runs the SQL and returns results

    INTERVIEW POINT:
      The agent doesn't run SQL directly. It calls a tool which calls
      db.run(sql). This abstraction means we can swap SQLite for
      PostgreSQL by just changing the URI — the agent code doesn't change.
    """
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Build the ReAct agent
# ─────────────────────────────────────────────────────────────────────────────
def build_agent(llm: ChatMistralAI, tools: list) -> AgentExecutor:
    """
    This function creates the full agent pipeline.

    TWO COMPONENTS:

    1. create_react_agent(llm, tools, prompt)
       → Creates the "thinking" part.
         Tells the LLM: "Here are your tools. Here is the ReAct format.
         Reason step by step and choose tools until you can answer."
         Output: an agent Runnable (not yet executable)

    2. AgentExecutor(agent, tools, ...)
       → Creates the "execution" part.
         Runs the actual Thought → Action → Observation loop.
         Calls tools, feeds results back to the LLM, repeats.
         Output: the fully operational agent you can invoke()

    KEY PARAMETERS:
      verbose=True        → Print every reasoning step to the terminal.
                            This is educational — leave it on while learning.
      handle_parsing_errors=True
                          → If the LLM produces malformed output (missing
                            "Action:" prefix etc.), retry gracefully instead
                            of crashing.
      max_iterations=10   → Safety valve. Prevents infinite loops if the
                            agent keeps second-guessing itself.

    ABOUT THE PROMPT:
      We pull the standard ReAct prompt from LangChain Hub.
      It already includes the ReAct format instructions.
      We inject our SYSTEM_PROMPT (schema + business rules) into it
      via prompt.partial(). This is how we teach the agent about
      OUR specific database without changing the ReAct structure.
    """
    # Pull the standard ReAct prompt template from LangChain Hub.
    # This defines the Thought / Action / Action Input / Observation format.
    prompt = hub.pull("hwchase17/react")

    # Inject our database schema and business rules into the prompt.
    # The {instructions} placeholder is where our SYSTEM_PROMPT goes.
    prompt = prompt.partial(instructions=SYSTEM_PROMPT)

    # create_react_agent wires together: LLM + tools + prompt format
    # It does NOT run anything yet — it just creates the reasoning chain.
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    # AgentExecutor is the runtime loop.
    # It repeatedly calls: agent → pick tool → run tool → feed result back.
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=VERBOSE,              # Show full reasoning chain
        handle_parsing_errors=True,   # Recover from LLM formatting mistakes
        max_iterations=10,            # Prevent runaway loops
    )

    return agent_executor


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Run one query and display the result clearly
# ─────────────────────────────────────────────────────────────────────────────
def run_query(agent_executor: AgentExecutor, question: str) -> None:
    """
    Sends the user's question to the agent and prints:
      - The generated SQL query (extracted from intermediate steps)
      - The final plain-English answer

    HOW SQL EXTRACTION WORKS:
      The agent's invoke() returns a dict with:
        result["output"]             → Final answer string
        result["intermediate_steps"] → List of (action, observation) tuples

      Each action has a .tool and .tool_input attribute.
      When the tool is "sql_db_query", tool_input IS the SQL string.
      We grab the last one (in case the agent refined its query mid-loop).
    """
    print("\n" + "═" * 62)
    print(f"  QUESTION: {question}")
    print("═" * 62)

    try:
        # This triggers the full ReAct loop.
        # verbose=True means you'll see every Thought/Action/Observation printed.
        result = agent_executor.invoke({"input": question})

        # ── Extract the SQL from intermediate steps ──────────────────────────
        sql_query = None

        for action, _observation in result.get("intermediate_steps", []):
            # action.tool is the name of the tool that was called
            # action.tool_input is what was passed to that tool
            if getattr(action, "tool", "") == "sql_db_query":
                sql_query = action.tool_input  # This IS the SQL string

        # ── Print results cleanly ─────────────────────────────────────────────
        print("\n" + "─" * 62)

        if sql_query:
            print("  GENERATED SQL:")
            # Indent the SQL for readability
            for line in sql_query.strip().splitlines():
                print(f"    {line}")
        else:
            print("  GENERATED SQL:  (see verbose output above)")

        print("─" * 62)
        print("  FINAL ANSWER:")
        print(f"  {result.get('output', 'No answer returned.')}")
        print("─" * 62 + "\n")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Make sure your question is about the orders table.")
        print("  Try: 'What columns does the orders table have?'\n")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — CLI loop (entry point)
# ─────────────────────────────────────────────────────────────────────────────
def main():
    """
    Startup sequence:
      1. Connect to orders.db
      2. Load the LLM
      3. Create SQL tools
      4. Build the agent (done once — not rebuilt per query)
      5. Enter an infinite loop accepting user questions

    The agent is built once at startup for efficiency.
    Each call to run_query() starts a fresh ReAct loop for that question.
    There is no memory between questions — every query is independent.
    """
    print("\n" + "═" * 62)
    print("   AI SQL AGENT  —  LangChain + SQLite")
    print("   Database: orders.db  |  Table: orders")
    print("═" * 62)
    print("  Type a question in plain English.")
    print("  Type 'exit' or 'quit' to stop.\n")
    print("  Try these example queries:")
    print("    › What is total revenue by city?")
    print("    › Average delivery time for completed orders")
    print("    › Top 5 food categories by revenue")
    print("    › Which city has the highest average rating?")
    print("    › How many orders were cancelled?")
    print("    › Revenue breakdown by time of day")
    print("═" * 62 + "\n")

    # ── Initialise everything once at startup ────────────────────────────────
    print("  Connecting to database...")
    db = get_database()

    print("  Loading LLM...")
    llm = get_llm()

    print("  Creating SQL tools...")
    tools = get_tools(db, llm)

    print("  Building agent...")
    agent_executor = build_agent(llm, tools)

    print("  Ready.\n")

    # ── Main question loop ───────────────────────────────────────────────────
    while True:
        try:
            user_input = input("Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!\n")
            break

        if not user_input:
            continue  # Ignore empty input

        if user_input.lower() in ("exit", "quit", "q"):
            print("\n  Goodbye!\n")
            break

        run_query(agent_executor, user_input)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

