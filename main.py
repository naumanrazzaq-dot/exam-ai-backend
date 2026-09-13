import os
import hashlib
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from google import genai
from supabase import create_client
from mangum import Mangum

sb_url = os.getenv("SUPABASE_URL", "https://iiussffgjberpcyfyigf.supabase.co")
sb_key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlpdXNzZmZnamJlcnBjeWZ5aWdmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwMzAyOTQsImV4cCI6MjEwNDYwNjI5NH0.UHvSX8zOEj27An3ds4WsBkmxSV16ynjuvfGCNqM92D8")

supabase = create_client(sb_url, sb_key)

api_key = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6JKE0BWQySBI1TH7YhmhJz-0MyttsZspgO0xVVOIFDsJA")
gemini_client = genai.Client(api_key=api_key)

app = FastAPI(title="MDCAT & ECAT AI Backend API")

# Explicit origins + regex allows any vercel domain or localhost without breaking credentials
origins = [
    "https://crackitai-sepia.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_vector(text: str, dim: int = 768):
    h = hashlib.sha256(text.encode('utf-8')).digest()
    vals = [float((b / 255.0) * 2 - 1) for b in h]
    repeats = (dim // len(vals)) + 1
    return (vals * repeats)[:dim]

def get_context(topic: str, category: str):
    q_vec = generate_vector(topic)
    try:
        res = supabase.rpc("match_documents", {
            "query_embedding": q_vec,
            "match_count": 3,
            "filter_category": category
        }).execute()
        return "\n\n".join([d["content"] for d in res.data]) if res.data else ""
    except Exception:
        return ""

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

@app.post("/ask")
async def ask_tutor(req: QueryRequest):
    user_query = req.question or req.topic
    context = get_context(req.topic, req.category)
    prompt = (
        f"You are an expert entrance exam tutor for {req.category}.\n"
        f"The student asked: '{user_query}'. Automatically correct any typos.\n"
        "Provide a high-yield, structured conceptual explanation for exam preparation.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{user_query}\n\n"
        "Answer:"
    )
    res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return {
        "status": "success",
        "category": req.category,
        "query": user_query,
        "answer": res.text
    }

@app.post("/quiz")
async def generate_quiz(req: QuizRequest):
    context = get_context(req.topic, req.category)
    prompt = (
        f"You are an entry test examiner for {req.category}.\n"
        f"The student entered: '{req.topic}'. Automatically correct any typos.\n"
        f"Generate 3 fresh, unique conceptual MCQs starting at index #{req.start_index}.\n"
        "Return strictly a valid JSON array of objects without markdown formatting or code blocks.\n"
        "Ensure 'correct_letter' is exactly one of: 'A', 'B', 'C', or 'D'.\n"
        "Schema:\n"
        "[\n"
        "  {\n"
        '    "question": "Question text",\n'
        '    "options": ["Option text A", "Option text B", "Option text C", "Option text D"],\n'
        '    "correct_letter": "A",\n'
        '    "explanation": "Detailed explanation in English."\n'
        "  }\n"
        "]\n\n"
        f"Context:\n{context}"
    )
    res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = res.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("\n", 1)[0]
    
    try:
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
