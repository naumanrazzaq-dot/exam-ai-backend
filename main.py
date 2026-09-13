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
    raw_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not raw_key:
        raise ValueError("Missing API key")

    api_key = raw_key.split(",")[0].strip()

    prompt = (
        f"You are an expert AI tutor for MDCAT and ECAT entrance exams.\n"
        f"Student question: '{clean_query}'.\n\n"
        "Provide a concise, complete conceptual explanation tailored for competitive entrance tests.\n"
        "Include definition, key formula/relationship, and common exam traps.\n"
        "Keep math readable and do not truncate formulas. Avoid long conversational greetings."
    )

    # 1500 tokens gives complete answers without cutting formulas
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1500,
            "temperature": 0.3
        }
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={urllib.parse.quote(api_key)}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

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
        print("Gemini API exception:", str(e))
        answer = (
            f"### Conceptual Summary: {clean_q.title()}\n\n"
            f"**1. Core Principle for {req.category}:**\n"
            f"In entrance exam science, **{clean_q}** covers standard fundamental physical or biological laws.\n\n"
            f"**2. High-Yield Exam Takeaway:**\n"
            f"* Verify dependencies, governing conditions, and base SI units.\n"
            f"* Always identify direct versus inverse proportionalities to evaluate options quickly."
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
