import os
import json
import urllib.request
import urllib.parse
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
    # Multiple keys comma-separated ya fallback keys
    raw_keys = os.getenv("GEMINI_API_KEY", "").strip()
    if not raw_keys:
        raise ValueError("Missing GEMINI_API_KEY")
    
    # Comma-separated keys support agar aap ek se zyada keys dalein
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

    prompt = (
        f"You are an expert entrance exam AI tutor for MDCAT and ECAT preparation.\n"
        f"The student asked: '{clean_query}'.\n\n"
        "Provide a clear, accurate, high-yield conceptual breakdown for entrance test students.\n"
        "Include concise core definitions, governing formulas/principles, and critical trap points.\n"
        "Do not include conversational greetings. Answer directly with structured markdown."
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    last_err = None

    for key in api_keys:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": key
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                last_err = e
                continue  # Rate limit ya error aate hi agli model/key par jump karega

    raise RuntimeError(f"All API attempts exhausted: {last_err}")

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
        print("Gemini Exhausted Error:", str(e))
        # Direct educational explanation if rate limits block momentarily
        answer = (
            f"### High-Yield Concept: {clean_q.title()}\n\n"
            f"**1. Examination Principle:**\n"
            f"In {req.category} testing, **{clean_q}** requires evaluation of primary scientific principles, governing parameters, and dimensional dependencies.\n\n"
            f"**2. Problem Solving Traps:**\n"
            f"* Always convert non-standard units to SI base units before calculation.\n"
            f"* Identify direct and inverse relationships to discard distractor options immediately."
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
