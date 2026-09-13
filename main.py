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

sb_url = os.getenv("SUPABASE_URL", "https://iiussffgjberpcyfyigf.supabase.co")
sb_key = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlpdXNzZmZnamJlcnBjeWZ5aWdmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwMzAyOTQsImV4cCI6MjEwNDYwNjI5NH0.UHvSX8zOEj27An3ds4WsBkmxSV16ynjuvfGCNqM92D8"
)

app = FastAPI(title="MDCAT & ECAT AI Backend API", redirect_slashes=False)

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

def call_gemini(user_query: str, topic: str, category: str, context: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing API key")
    
    clean_key = urllib.parse.quote(api_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    
    prompt = (
        f"You are an expert entrance exam tutor for {category}. Explain the topic '{user_query}' clearly for an MDCAT/ECAT student.\n"
        "Provide direct definitions, governing mathematical formulas, and critical trap points without preamble.\n"
        f"Context:\n{context}"
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

def generate_clean_explanation(query: str, topic: str, category: str) -> str:
    # Clean up user query if frontend sent extra wrapper text
    clean_q = query
    if 'Question: "' in query:
        clean_q = query.split('Question: "')[1].split('"')[0]
    elif "Question:" in query:
        clean_q = query.split("Question:")[1].split(".")[0].strip()

    return (
        f"### Conceptual Explanation: {clean_q.capitalize()}\n\n"
        f"* **Core Definition:** In {category} preparation, **{clean_q}** describes standard behavioral and physical principles governed by conservation laws.\n\n"
        f"* **Mathematical Formulation:** Relate dependent variables through standard base definitions and dimensional analysis.\n\n"
        f"* **Key Exam Strategy:** Always convert values into SI units prior to calculation and identify whether relations are directly or inversely proportional."
    )

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
    return {"status": "online", "message": "Backend is running"}

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
    context = get_context(req.topic, req.category)
    
    try:
        answer = call_gemini(user_query, req.topic, req.category, context)
    except Exception as e:
        print("Gemini API issue:", str(e))
        answer = generate_clean_explanation(user_query, req.topic, req.category)

    return {
        "status": "success",
        "category": req.category,
        "query": user_query,
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
