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

# Robust Subject Knowledge Base for Entrance Exams
KNOWLEDGE_BASE = {
    "physics": (
        "### Fundamentals of Physics\n\n"
        "**1. Core Definition:**\n"
        "Physics is the foundational branch of science concerned with the nature and properties of matter and energy. It explores mechanics, thermodynamics, electromagnetism, and modern physics.\n\n"
        "**2. Essential Domains in Entrance Exams:**\n"
        "* **Mechanics:** Vectors, Newton's Laws, Work, Energy, and Momentum conservation.\n"
        "* **Electromagnetism:** Coulomb's law, electric fields, Gauss's law, and electromagnetic induction.\n\n"
        "**3. High-Yield Exam Strategy:**\n"
        "* Always check unit homogeneity and dimensional formulas ($[M^a L^b T^c]$) before selecting an option.\n"
        "* Watch for vector vs scalar trap distinctions (e.g., velocity vs speed, work vs torque)."
    ),
    "inertia": (
        "### Inertia in Classical Mechanics\n\n"
        "**1. Definition & Newton's First Law:**\n"
        "Inertia is the inherent resistance of an object to any change in its velocity (either speed or direction). It is strictly measured by an object's **mass**.\n\n"
        "**2. Governing Equations:**\n"
        "* Linear Inertia: Measured solely by mass ($m$).\n"
        "* Rotational Inertia: $I = \\sum m r^2$.\n\n"
        "**3. Exam Pitfalls:**\n"
        "* Inertia does NOT depend on speed, gravity, or applied force."
    ),
    "enzyme": (
        "### Enzymes: Biological Catalysts\n\n"
        "**1. Definition & Function:**\n"
        "Enzymes are specialized globular proteins that accelerate biological chemical reactions by lowering activation energy ($E_a$).\n\n"
        "**2. Core Kinetics:**\n"
        "* Active sites bind specific substrates following the Induced Fit Model.\n"
        "* Rate depends on substrate concentration, temperature, and pH.\n\n"
        "**3. Exam Pitfall:**\n"
        "* Enzymes do not shift the chemical equilibrium ($K_{eq}$) or alter $\\Delta G$."
    ),
    "momentum": (
        "### Linear Momentum & Impulse\n\n"
        "**1. Formulation:**\n"
        "Linear momentum is the measure of motion: $p = m \\cdot v$.\n\n"
        "**2. Conservation Principle:**\n"
        "* Total momentum remains conserved in isolated systems: $\\sum p_{initial} = \\sum p_{final}$.\n"
        "* Impulse: $J = \\Delta p = F_{net} \\cdot \\Delta t$.\n\n"
        "**3. Exam Pitfall:**\n"
        "* In elastic collisions, both kinetic energy and momentum are conserved; in inelastic collisions, only momentum is conserved."
    ),
    "environment": (
        "### Ecology & Environmental Factors\n\n"
        "**1. Definition:**\n"
        "The environment encompasses all surrounding abiotic (non-living) and biotic (living) factors interacting with organisms.\n\n"
        "**2. Key Ecological Hierarchy:**\n"
        "* Organism $\\rightarrow$ Population $\\rightarrow$ Community $\\rightarrow$ Ecosystem $\\rightarrow$ Biosphere.\n\n"
        "**3. High-Yield Tip:**\n"
        "* Distinguish between Habitat (address) and Niche (functional profession of the species)."
    ),
    "mdcat": (
        "### Medical & Dental College Admission Test (MDCAT)\n\n"
        "**Structure & Focus:**\n"
        "MDCAT tests conceptual mastery across Biology, Chemistry, Physics, English, and Logical Reasoning.\n\n"
        "**Strategy:**\n"
        "* Prioritize biological diagrams, classification systems, and organic reaction mechanisms."
    ),
    "ecat": (
        "### Engineering College Admission Test (ECAT)\n\n"
        "**Structure & Focus:**\n"
        "ECAT evaluates analytical problem solving in Mathematics, Physics, Chemistry/Computer Science, and English.\n\n"
        "**Strategy:**\n"
        "* Focus on shortcut calculations, calculus fundamentals, vectors, and mechanics."
    )
}

def call_gemini(clean_query: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing API key")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={urllib.parse.quote(api_key)}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": f"Explain this entry test topic clearly with definitions, formulas, and pitfalls: {clean_query}"}]}]
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

def generate_smart_response(clean_q: str, category: str) -> str:
    q_lower = clean_q.lower()
    for key, content in KNOWLEDGE_BASE.items():
        if key in q_lower:
            return content

    return (
        f"### Conceptual Breakdown: {clean_q.title()}\n\n"
        f"**1. Core Principles & Definition:**\n"
        f"In entrance exam science, **{clean_q}** forms a vital foundation for conceptual evaluation. It describes fundamental physical, biological, or quantitative behaviors governed by established theoretical principles.\n\n"
        f"**2. Essential Exam Strategy:**\n"
        f"* Verify boundary conditions, coordinate axes, and standard SI units.\n"
        f"* Track direct vs. inverse proportional relationships between variables to eliminate distractor options quickly.\n"
        f"* Test limiting cases (e.g., $x \\to 0$ or $x \\to \\infty$) to confirm mathematical consistency."
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
    except Exception:
        answer = generate_smart_response(clean_q, req.category)

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
