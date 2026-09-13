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
        return "Error: GEMINI_API_KEY environment variable is missing on Vercel."

    api_key = raw_key.split(",")[0].strip()

    prompt = (
        f"You are an expert tutor for entrance exams (MDCAT and ECAT).\n"
        f"Student question: '{clean_query}'.\n\n"
        "Provide a high-yield, accurate conceptual answer tailored for entrance exams.\n"
        "Include core definitions, governing equations or biological mechanisms, and critical exam pitfalls.\n"
        "Do not include conversational greetings. Answer directly using structured markdown."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # Working active endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={urllib.parse.quote(api_key)}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=12) as resp:
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
        answer = f"Gemini API Error: {str(e)}"

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
