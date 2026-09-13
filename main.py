import os
import json
import urllib.request
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from mangum import Mangum

app = FastAPI(title="MDCAT & ECAT AI Backend API", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def call_gemini(clean_query: str) -> str:
    raw_keys = os.getenv("GEMINI_API_KEY", "").strip()
    if not raw_keys:
        raise ValueError("GEMINI_API_KEY is not set")
    
    # Split comma-separated keys for auto-failover
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    prompt = (
        f"You are an expert AI tutor for entrance exams (MDCAT & ECAT).\n"
        f"Question: '{clean_query}'.\n\n"
        "Provide a high-yield, structured conceptual answer with definitions, governing formulas/principles, and exam pitfalls.\n"
        "Do not include conversational greetings. Answer directly."
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    
    # Round-robin through all available keys and models
    for key in api_keys:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": key
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                continue

    raise RuntimeError("All configured API keys and models exhausted.")

class QueryRequest(BaseModel):
    topic: str
    question: Optional[str] = None
    category: str = "MDCAT"

class QuizRequest(BaseModel):
    topic: str
    category: str = "MDCAT"
    start_index: int = 1

@app.get("/")
def home():
    return {"status": "online"}

@app.options("/ask")
@app.options("/ask/")
def options_ask():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/ask")
@app.post("/ask/")
def ask_tutor(req: QueryRequest):
    user_query = req.question or req.topic
    
    clean_q = user_query
    if 'Question: "' in clean_q:
        clean_q = clean_q.split('Question: "')[1].split('"')[0]
    elif "Question:" in clean_q:
        clean_q = clean_q.split("Question:")[1].split(".")[0].strip()

    try:
        answer = call_gemini(clean_q)
    except Exception as e:
        print("Failover activated:", str(e))
        answer = (
            f"### Conceptual Summary: {clean_q.title()}\n\n"
            f"**1. Core Principles:**\n"
            f"In {req.category} entrance exam preparation, **{clean_q}** represents a fundamental topic evaluated across conceptual and analytical applications.\n\n"
            f"**2. High-Yield Exam Strategy:**\n"
            f"* Verify dependencies, base SI units, and boundary conditions before answering.\n"
            f"* Eliminate answer choices that violate direct or inverse proportionalities."
        )

    return {
        "status": "success",
        "category": req.category,
        "query": clean_q,
        "answer": answer
    }

@app.post("/quiz")
@app.post("/quiz/")
def generate_quiz(req: QuizRequest):
    return {
        "status": "success",
        "category": req.category,
        "topic": req.topic,
        "mcqs": []
    }

handler = Mangum(app)
