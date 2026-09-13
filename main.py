import os
import hashlib
import json
import urllib.request
import urllib.parse
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from mangum import Mangum

# Supabase Credentials
sb_url = os.getenv("SUPABASE_URL", "https://iiussffgjberpcyfyigf.supabase.co")
sb_key = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlpdXNzZmZnamJlcnBjeWZ5aWdmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwMzAyOTQsImV4cCI6MjEwNDYwNjI5NH0.UHvSX8zOEj27An3ds4WsBkmxSV16ynjuvfGCNqM92D8"
)

app = FastAPI(title="MDCAT & ECAT AI Backend API", redirect_slashes=False)

# Comprehensive CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def generate_vector(text: str, dim: int = 768):
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vals = [float((b / 255.0) * 2 - 1) for b in h]
    repeats = (dim // len(vals)) + 1
    return (vals * repeats)[:dim]

def get_context(topic: str, category: str):
    try:
        from supabase import create_client
        supabase = create_client(sb_url, sb_key)
        q_vec = generate_vector(topic)
        res = supabase.rpc("match_documents", {
            "query_embedding": q_vec,
            "match_count": 3,
            "filter_category": category
        }).execute()
        return "\n\n".join([d["content"] for d in res.data]) if res.data else ""
    except Exception:
        return ""

def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not configured")
    
    clean_key = urllib.parse.quote(api_key)
    # Using Gemini 1.5 Flash endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
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
    return {"status": "online", "message": "Backend is running 24/7"}

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
    try:
        context = get_context(req.topic, req.category)
        prompt = (
            f"You are an expert entrance exam tutor for {req.category}.\n"
            f"The student asked: '{user_query}'.\n"
            "Provide a concise, high-yield, structured conceptual explanation for exam preparation.\n"
            "Include key definitions, governing formulas, and common exam pitfalls.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{user_query}\n\n"
            "Answer:"
        )
        answer = call_gemini(prompt)
    except Exception as e:
        print("Live Gemini call error:", str(e))
        answer = (
            f"### Conceptual Breakdown: {req.topic}\n\n"
            f"* **Core Concept:** {user_query} governs physical and scientific behavior evaluated heavily in {req.category}.\n"
            "* **Standard Relations & SI Units:** Always confirm fundamental base units and identify direct vs inverse proportionalities.\n"
            "* **Exam Tip:** Eliminate answer options that violate dimensional analysis before evaluating numeric calculations."
        )

    return {
        "status": "success",
        "category": req.category,
        "query": user_query,
        "answer": answer
    }

@app.post("/quiz")
@app.post("/quiz/")
def generate_quiz(req: QuizRequest):
    try:
        context = get_context(req.topic, req.category)
        prompt = (
            f"You are an entry test examiner for {req.category}.\n"
            f"Generate 3 fresh conceptual MCQs for topic: '{req.topic}' starting at index #{req.start_index}.\n"
            "Return strictly a valid JSON array of objects without markdown formatting or code blocks.\n"
            "Ensure 'correct_letter' is exactly one of: 'A', 'B', 'C', or 'D'.\n"
            "Schema:\n"
            "[\n"
            "  {\n"
            '    "question": "Question text",\n'
            '    "options": ["Option text A", "Option text B", "Option text C", "Option text D"],\n'
            '    "correct_letter": "A",\n'
            '    "explanation": "Detailed explanation."\n'
            "  }\n"
            "]\n\n"
            f"Context:\n{context}"
        )
        raw = call_gemini(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
        mcqs_data = json.loads(raw)
    except Exception:
        mcqs_data = []

    return {
        "status": "success",
        "category": req.category,
        "topic": req.topic,
        "mcqs": mcqs_data
    }

handler = Mangum(app)
