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
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable")
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    prompt = (
        f"You are an expert entrance exam AI tutor for MDCAT and ECAT preparation.\n"
        f"A student asked: '{clean_query}'.\n\n"
        "Provide a clear, accurate, and structured explanation tailored for pre-medical and pre-engineering entrance exams.\n"
        "Include concise core definitions, governing formulas or biological mechanisms, and high-yield exam takeaways.\n"
        "Do not include conversational filler greetings (like Assalam-o-Alaikum or Hello). Start directly with the answer."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    # Modern Google AI Studio keys (starting with AQ.) require the x-goog-api-key header
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
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
    return {"status": "online", "message": "General AI Backend is running 24/7"}

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
    
    # Clean query if full sentence wrappers were passed
    clean_q = user_query
    if 'Question: "' in clean_q:
        clean_q = clean_q.split('Question: "')[1].split('"')[0]
    elif "Question:" in clean_q:
        clean_q = clean_q.split("Question:")[1].split(".")[0].strip()

    try:
        answer = call_gemini(clean_q)
    except Exception as e:
        print("Gemini API Error:", str(e))
        answer = (
            f"### Conceptual Summary: {clean_q.capitalize()}\n\n"
            f"**Core Principle:**\n"
            f"In {req.category} entrance exam curriculum, **{clean_q}** covers standard physical, biological, or chemical principles.\n\n"
            f"**Key High-Yield Pointers:**\n"
            f"* Verify dependencies, governing conditions, and unit analysis.\n"
            f"* Distinguish between direct vs inverse proportionalities before evaluating options."
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
