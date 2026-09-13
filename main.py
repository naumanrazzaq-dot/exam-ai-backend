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
        raise ValueError("GEMINI_API_KEY environment variable missing in Vercel")

    # Handle comma-separated keys if provided
    keys = [k.strip() for k in api_key.split(",") if k.strip()]
    active_key = keys[0]

    prompt = (
        f"You are an expert entrance exam AI tutor for MDCAT and ECAT.\n"
        f"Student Question: '{clean_query}'.\n\n"
        "Provide a detailed, accurate conceptual breakdown tailored for exam preparation.\n"
        "Include core definitions, fundamental formulas/principles, and common trap points.\n"
        "Answer directly without greetings."
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # Direct v1 endpoint with URL parameter and x-goog-api-key header
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={urllib.parse.quote(active_key)}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": active_key
        }
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
    except urllib.error.HTTPError as he:
        # Read exact response from Google to identify blockage
        err_msg = he.read().decode("utf-8")
        print("Google HTTP Error:", err_msg)
        answer = (
            f"### API Key Verification Notice\n\n"
            f"Google Gemini rejected the key with status **{he.code}**.\n\n"
            f"**Google Response:** `{err_msg[:250]}`"
        )
    except Exception as e:
        print("Call Error:", str(e))
        answer = (
            f"### Service Notice\n\n"
            f"Unable to connect to Gemini API: `{str(e)}`"
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
