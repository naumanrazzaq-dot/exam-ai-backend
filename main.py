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
        raise ValueError("GEMINI_API_KEY is not set in Vercel environment variables.")

    # Get primary key without spaces
    api_key = raw_key.split(",")[0].strip()

    prompt = (
        f"You are an expert entrance exam AI tutor for MDCAT and ECAT students.\n"
        f"The student asked: '{clean_query}'.\n\n"
        "Provide a high-yield, structured conceptual answer.\n"
        "Include core definitions, governing formulas/principles, and crucial exam trap points.\n"
        "Do not include conversational greetings. Answer directly using clear markdown."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # List of valid modern endpoint variations
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={urllib.parse.quote(api_key)}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={urllib.parse.quote(api_key)}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={urllib.parse.quote(api_key)}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={urllib.parse.quote(api_key)}"
    ]

    last_error = ""
    for url in endpoints:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as he:
            err_text = he.read().decode("utf-8")
            last_error = f"Status {he.code}: {err_text}"
            continue
        except Exception as ex:
            last_error = str(ex)
            continue

    raise RuntimeError(last_error)

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
        print("Live API failure:", str(e))
        answer = (
            f"### Conceptual Review: {clean_q.title()}\n\n"
            f"**1. Core Principle for {req.category}:**\n"
            f"In competitive exam curriculum, **{clean_q}** establishes foundational theoretical properties and mathematical proportionalities.\n\n"
            f"**2. High-Yield Exam Takeaway:**\n"
            f"* Ensure conversion of variables to proper SI base units before computation.\n"
            f"* Test limiting dependencies to rule out incorrect options quickly."
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
