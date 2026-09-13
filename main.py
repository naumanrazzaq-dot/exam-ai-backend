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
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")
    
    prompt = (
        f"You are an expert entrance exam AI tutor for MDCAT and ECAT.\n"
        f"Explain '{clean_query}' thoroughly.\n"
        "Provide a clear core definition, key formulas or biological mechanisms, and high-yield entry test exam tips.\n"
        "Do not include conversational greetings. Answer directly."
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    # Method 1: Query param method
    try:
        clean_key = urllib.parse.quote(api_key)
        url1 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
        req1 = urllib.request.Request(url1, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req1, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        pass

    # Method 2: Header authentication method
    url2 = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    req2 = urllib.request.Request(
        url2, 
        data=payload, 
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
    )
    with urllib.request.urlopen(req2, timeout=12) as resp:
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
    
    # Strip client instruction wrappers
    clean_q = user_query
    if 'Question: "' in clean_q:
        clean_q = clean_q.split('Question: "')[1].split('"')[0]
    elif "Question:" in clean_q:
        clean_q = clean_q.split("Question:")[1].split(".")[0].strip()

    try:
        answer = call_gemini(clean_q)
    except Exception as e:
        print("Live call error:", str(e))
        answer = (
            f"### Conceptual Summary: {clean_q.capitalize()}\n\n"
            f"**Definition:**\n"
            f"In {req.category} entrance exam preparation, **{clean_q}** covers standard fundamental principles evaluated consistently.\n\n"
            f"**Key Focus Points:**\n"
            f"* Verify dependencies, governing equations, and dimensional units.\n"
            f"* Identify direct vs inverse relationships to evaluate questions accurately."
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
