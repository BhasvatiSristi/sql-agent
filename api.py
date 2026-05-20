"""
FastAPI backend for the React + Tailwind frontend.

Run with:
    uvicorn api:app --reload --port 8000
"""

from functools import lru_cache
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import get_database, get_llm, get_tools, build_agent, run_query_streamlit

EXAMPLES = [
    "Total revenue by city",
    "Avg delivery time for completed orders",
    "Top 5 food categories by revenue",
    "City with highest avg rating",
    "How many orders were cancelled?",
    "Revenue breakdown by time of day",
]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language analytics question")


app = FastAPI(title="AI SQL Agent API", version="1.0.0")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_agent_executor():
    db = get_database()
    llm = get_llm()
    tools = get_tools(db, llm)
    return build_agent(llm, tools)


@app.get("/api/health")
def health():
    get_agent_executor()
    return {"status": "ok"}


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.post("/api/query")
def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = run_query_streamlit(get_agent_executor(), question)
    return result
