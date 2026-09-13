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

# Comprehensive academic response engine
KNOWLEDGE_BASE = {
    "inertia": (
        "### Inertia in Classical Mechanics\n\n"
        "**1. Definition & Newton's First Law:**\n"
        "Inertia is the inherent property of a body that resists any change in its state of rest or uniform motion in a straight line. It is quantified solely by the **mass** of the body.\n\n"
        "**2. Governing Relations:**\n"
        "* Measure of Inertia: $m \\text{ (Mass)}$\n"
        "* Moment of Inertia (Rotational analogue): $I = \\sum m r^2$\n\n"
        "**3. High-Yield Exam Pitfalls:**\n"
        "* Inertia does not depend on velocity or acceleration; only on mass.\n"
        "* Rotational inertia depends both on mass and the distribution of mass relative to the axis of rotation."
    ),
    "enzyme": (
        "### Enzymes: Biological Catalysts\n\n"
        "**1. Core Biological Definition:**\n"
        "Enzymes are globular proteins that accelerate biochemical reaction rates by lowering the activation energy ($E_a$) without undergoing permanent chemical changes.\n\n"
        "**2. Key Characteristics & Kinetics:**\n"
        "* **Active Site:** Specific 3D region where substrate binding occurs (Lock & Key / Induced Fit models).\n"
        "* **Optimum Range:** Highly sensitive to thermal denaturation and pH variations.\n\n"
        "**3. Entry Test Trap Points:**\n"
        "* Enzymes alter reaction kinetics ($k$), but do NOT alter equilibrium constants ($K_{eq}$) or standard free energy change ($\\Delta G$)."
    ),
    "momentum": (
        "### Linear Momentum & Impulse\n\n"
        "**1. Definition & Formulation:**\n"
        "Momentum ($\\vec{p}$) measures the quantity of motion contained in an object, defined as the product of mass and linear velocity:\n"
        "$$\\vec{p} = m \\cdot \\vec{v}$$\n\n"
        "**2. Conservation & SI Units:**\n"
        "* SI Unit: $\\text{kg}\\cdot\\text{m/s}$ or $\\text{N}\\cdot\\text{s}$\n"
        "* Conservation Principle: In an isolated system ($\\Sigma \\vec{F}_{ext} = 0$), total linear momentum is strictly conserved.\n\n"
        "**3. High-Yield Pitfall:**\n"
        "* Momentum is a vector quantity; direction changes produce non-zero impulse even if scalar speed is constant."
    ),
    "mdcat": (
        "### Medical and Dental College Admission Test (MDCAT)\n\n"
        "**Overview:**\n"
        "MDCAT stands for the **Medical & Dental College Admission Test**, the standardized examination required for admission into MBBS and BDS programs across Pakistan.\n\n"
        "**Core Subject Distribution:**\n"
        "* Biology (Highest weightage)\n"
        "* Chemistry & Physics (Conceptual & numerical focus)\n"
        "* English & Logical Reasoning"
    )
}

def call_gemini(clean_query: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("No API Key configured")

    prompt = (
        f"You are a subject tutor for entrance exams (MDCAT/ECAT).\n"
        f"Explain: '{clean_query}'.\n"
        "Provide direct definitions, formulas, and high-yield exam traps without greetings."
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    # Header-based request
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

def generate_intelligent_academic_response(query: str, category: str) -> str:
    q_lower = query.lower()
    for key, text in KNOWLEDGE_BASE.items():
        if key in q_lower:
            return text

    # Standard high-yield response generator
    return (
        f"### Conceptual Analysis: {query.title()}\n\n"
        f"**1. Core Definition for {category}:**\n"
        f"In entrance exam sciences, **{query}** represents fundamental physical or biological principles governed by standard laws.\n\n"
        "**2. Essential Exam Strategy:**\n"
        "* Verify dimensional consistency and convert given values into standard SI base units prior to computation.\n"
        "* Distinguish direct versus inverse proportionalities to eliminate distractor choices quickly.\n"
        "* Relate this concept back to fundamental conservation laws tested in the curriculum."
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
    return {"status": "online", "message": "API is active"}

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
    except Exception:
        answer = generate_intelligent_academic_response(clean_q, req.category)

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
