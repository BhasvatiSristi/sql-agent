"""
cli.py
======
Terminal interface for the AI SQL Agent.

Run with:
    python cli.py
"""

from agent import get_database, get_llm, get_tools, build_agent, run_query


def main() -> None:
    print("\n" + "═" * 62)
    print("   AI SQL AGENT  -  LangChain + Mistral + SQLite")
    print("   Database: orders.db  |  Table: orders")
    print("═" * 62)
    print("  Type a question in plain English.")
    print("  Type 'exit' or 'quit' to stop.\n")
    print("  Example queries:")
    print("    > What is total revenue by city?")
    print("    > Average delivery time for completed orders")
    print("    > Top 5 food categories by revenue")
    print("    > Which city has the highest average rating?")
    print("    > How many orders were cancelled?")
    print("═" * 62 + "\n")

    print("  Connecting to database...")
    db = get_database()

    print("  Loading LLM...")
    llm = get_llm()

    print("  Creating SQL tools...")
    tools = get_tools(db, llm)

    print("  Building agent...")
    agent_executor = build_agent(llm, tools)

    print("  Ready.\n")

    while True:
        try:
            user_input = input("Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("\n  Goodbye!\n")
            break

        run_query(agent_executor, user_input)


if __name__ == "__main__":
    main()
