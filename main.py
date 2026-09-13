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
        f"You are an expert tutor for entrance exams (MDCAT and ECAT).\n"
        f"Answer this question clearly and accurately: '{clean_query}'.\n"
        "Provide core definitions, components/formulas, and high-yield exam traps.\n"
        "Do not include filler greetings."
    )
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    # Endpoint permutations to handle modern keys
    targets = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={urllib.parse.quote(api_key)}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={urllib.parse.quote(api_key)}"
    ]

    for target in targets:
        try:
            req = urllib.request.Request(
                target,
                data=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            continue

    raise RuntimeError("Gemini API calls failed")

def generate_subject_aware_response(query: str, category: str) -> str:
    q = query.lower()

    # BIOLOGY DOMAIN
    if any(k in q for k in ["cell", "mitochondria", "organelle", "nucleus"]):
        return (
            "### Biology: The Fundamental Unit of Life (Cell)\n\n"
            "**1. Definition & Cell Theory:**\n"
            "The cell is the basic structural, functional, and biological unit of all known organisms.\n"
            "* Proposed by Schleiden and Schwann (1838–1839); Rudolf Virchow added *Omnis cellula e cellula* (cells arise from pre-existing cells).\n\n"
            "**2. Prokaryotic vs. Eukaryotic Distinctions:**\n"
            "* **Prokaryotes (Bacteria):** Lack membrane-bound organelles; 70S ribosomes ($50S + 30S$ subunits); naked circular DNA in nucleoid.\n"
            "* **Eukaryotes:** Membrane-bound nucleus, 80S ribosomes ($60S + 40S$ subunits), extensive compartmentalization.\n\n"
            "**3. High-Yield MDCAT Exam Traps:**\n"
            "*This screenshot shows an automated, "mad-libs" style template glitch on an ed-tech platform. Rather than providing actual educational content about a biological or electrochemical **cell**, the system has slotted the literal search query *"what is cell"* into a generic physics/math boilerplate template.

**Signs of the Template Failure**

* **Literal Query Injection:** Phrases like *"what is cell forms a vital foundation..."* and *"How does what is cell directly relate to core exam questions?"* indicate a placeholder variable like `{{query}}` was simply dropped into prewritten text.
* **Mismatched Subject Matter:** A query about a "cell" generates tips for coordinate axes, boundary conditions, and calculus limits ($x \to 0$, $x \to \infty$).
* **Irrelevant Call to Action:** The bottom action button prompts you to practice **Centripetal Force & Banking of Roads Questions**, completely detached from cells.

If you are looking for an actual definition depending on your subject:

* **Biology:** The basic structural, functional, and biological unit of all known living organisms (the fundamental building block of life).
* **Physics / Chemistry:** An electrochemical device capable of either generating electrical energy from chemical reactions (galvanic/voltaic cell) or using electrical energy to cause chemical reactions (electrolytic cell).
