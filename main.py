import os
import json
import urllib.request
import urllib.parse
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from mangum import Mangum

app = FastAPI(title="MDCAT & ECAT AI Backend API", redirectslashes=False)

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
        raise ValueError("Environment variable GEMINI_API_KEY Vercel par set nahi hai.")

    prompt = (
        f"You are an expert tutor for entrance exams (MDCAT and ECAT).\n"
        f"Explain: '{clean_query}' thoroughly.\n"
        "Provide direct definitions, formulas or mechanisms, and high-yield exam traps.\n"
        "No conversational greetings."
    )
    
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    # Try both standard endpoints
    models = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]
    last_error = ""

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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
            err_body = he.read().decode("utf-8")
            last_error = f"Google API Error ({he.code}): {err_body}"
        except Exception as ex:
            last_error = str(ex)

    raise RuntimeError(last_error)

def generate_topic_specific_fallback(query: str, category: str) -> str:
    q = query.lower()

    if "nuclear" in q:
        return (
            "### Nuclear Physics & Radioactivity\n\n"
            "**1. Core Definition:**\n"
            "Nuclear physics deals with the constituents, structure, behavior, and interactions of atomic nuclei.\n\n"
            "**2. Governing Principles & Equations:**\n"
            "* **Mass Defect & Binding Energy:** $\\Delta E = (\\Delta m) c^2$\n"
            "* **Radioactive Decay Law:** $N = N_0 e^{-\\lambda t}$\n"
            "* **Half-Life Formula:** $T_{1/2} = \\frac{\\ln 2}{\\lambda} \\approx \\frac{0.693}{\\lambda}$\n\n"
            "**3. MDCAT/ECAT Traps:**\n"
            "* $\\alpha$-decay decreases atomic number $Z$ by 2 and mass number $A$ by 4.\n"
            "* $\\beta^-$-decay increases $Z$ by 1, leaving $A$ unchanged."
        )

    if "cell" in q:
        return (
            "### Cell Biology: The Unit of Life\n\n"
            "**1. Core Definition:**\n"
            "The cell is the basic structural and functional unit of all living organisms.\n\n"
            "**2. Key Structural Components:**\n"
            "* **Prokaryotic vs Eukaryotic:** Prokaryotes lack membrane-bound organelles and possess 70S ribosomes, whereas eukaryotes have 80S ribosomes and compartmentalized organelles.\n"
            "* **Mitochondria:** Double-membraned organelle generating ATP via oxidative phosphorylation.\n\n"
            "**3. MDCAT Exam Tip:**\n"
            "* Plant cell walls consist of cellulose, fungal walls of chitin, and bacterial walls of peptidoglycan."
        )

    return (
        f"### Conceptual Analysis: {query.title()}\n\n"
        f"**1. High-Yield Definition for {category}:**\n"
        f"In entrance test curriculum, **{query}** represents fundamental scientific principles evaluated through conceptual applications and quantitative dependencies.\n\n"
        f"**2. Key Exam Strategy:**\n"
        f"* Verify units, boundary conditions, and direct/inverse proportionalities.\n"
        f"* Eliminate distractor options that violate conservation laws or dimensional balance."
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
        # Fallback ke sath actual error bhi log/inspect hoga
        print("Backend Error:", str(e))
        answer = generate_topic_specific_fallback(clean_q, req.category)

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
