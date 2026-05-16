"""
Context-Aware Translation API
==============================
A FastAPI backend that orchestrates multilingual translation, text refinement,
and grammar explanation using Google's Gemini generative AI model.

Architecture:
    Client (fetch) → FastAPI endpoint → Prompt Builder → Gemini API → JSON response

All prompt construction is handled server-side to maintain a clean separation
of concerns between the frontend (presentation) and backend (logic/orchestration).
"""

import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# 1. Environment Configuration
#    Credentials are loaded from a .env file and NEVER hardcoded.
#    See .env.example for required variables.
# ---------------------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "No API Key found. Please set GEMINI_API_KEY in your .env file. "
        "See .env.example for reference."
    )

# ---------------------------------------------------------------------------
# 2. Gemini Model Configuration
#    'flash-lite' is optimised for speed and lower cost.
#    Switch to 'gemini-2.5-flash' or 'gemini-2.5-pro' for complex reasoning.
# ---------------------------------------------------------------------------
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")


# ---------------------------------------------------------------------------
# 3. FastAPI Application Initialisation
#    The metadata here powers the auto-generated /docs (Swagger UI) page,
#    turning it into professional, self-documenting API documentation.
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Context-Aware Translation API",
    description=(
        "A multilingual translation and text refinement API powered by Google Gemini. "
        "Supports contextual prompt injection, multiple translation styles, "
        "and grammar explanation for translated output."
    ),
    version="1.0.0",
    contact={"name": "Developer"},
)


# ---------------------------------------------------------------------------
# 4. CORS Middleware
#    Cross-Origin Resource Sharing must be enabled so the frontend (served on
#    a different origin during development) can make fetch() requests to this
#    API. In production, replace allow_origins=["*"] with the specific domain.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Development: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# 5. Request / Response Models
#    Using optional fields keeps the API extensible and self-documenting.
#    A single endpoint handles translate, refine, and explain — differentiated
#    by the 'mode' field — while optional fields prevent hidden coupling.
# ---------------------------------------------------------------------------
class TextRequest(BaseModel):
    """Payload for all text-processing operations."""

    source_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The original text to translate, refine, or explain.",
    )
    mode: str = Field(
        ...,
        description="Processing mode: 'translate', 'refine', or 'explain'.",
    )
    source_lang: str = Field(
        default="auto",
        description="Source language. Use 'auto' for automatic detection.",
    )
    target_lang: str | None = Field(
        default=None,
        description="Target language for translation (e.g. 'Urdu', 'Spanish').",
    )
    tone: str = Field(
        default="Normal",
        description="Desired style/tone (e.g. 'Literal', 'Poetic', 'Professional').",
    )
    translated_text: str | None = Field(
        default=None,
        description="Previously translated text — used only in 'explain' mode.",
    )
    context_hint: str | None = Field(
        default=None,
        description=(
            "Optional situational context that makes translation context-aware. "
            "Examples: 'formal business email', 'restaurant conversation', "
            "'legal contract', 'casual gaming chat'."
        ),
    )


class TextResponse(BaseModel):
    """Successful processing result."""

    result: str = Field(..., description="The processed text output.")


# ---------------------------------------------------------------------------
# 6. Prompt Engineering
#    ALL prompts are constructed server-side. The frontend sends structured
#    data; the backend decides how to frame the request to the AI model.
#    This maintains a clean separation of concerns and makes prompts
#    maintainable and testable in isolation.
# ---------------------------------------------------------------------------

# -- Style maps for translation and refinement tones --
TRANSLATION_STYLES = {
    "Normal": "Translate naturally and idiomatically. Preserve the original tone and intent. Do not add extra flair.",
    "Literal": "Translate word-for-word. Ignore idioms (e.g., 'raining cats and dogs' should involve animals falling). Do smooth out grammar.",
    "Literary": "Use rich, elevated vocabulary. Make it sound like classic literature or high prose.",
    "Poetic": "Focus on rhythm and flow. Use evocative language appropriate for poetry.",
    "Motivational": "Translate the meaning but infuse it with energy and hype.",
    "Satirical": "Translate the meaning but add a layer of irony or sarcasm.",
    "Gen Z": "Translate the meaning but use modern internet slang/lingo.",
}

REFINE_STYLES = {
    "Professional": "Make it business-appropriate, concise, and objective. No contractions.",
    "Casual": "Make it sound like a friendly text to a friend. Use contractions and relaxed grammar.",
    "Scientific": "Use academic/scientific terminology. Present ideas as hypotheses or observations. Be precise.",
    "Creative": "Think abstractly. Connect ideas with metaphors. Make the text 'bubble up' with imagery and unique associations.",
    "Poetic": "Rewrite as a poem or lyrical prose. Focus on beauty and rhythm.",
    "Motivational": "Act as a high-energy coach. Inspire action! Use exclamation points!",
    "Old English": "Rewrite using archaic vocabulary (thou, hath, etc.) and Shakespearean grammar.",
    "Gen Z": "Rewrite using current Gen Z slang (no cap, fr, vibe check).",
}


def _build_context_line(context_hint: str | None) -> str:
    """Return a context instruction line if a hint is provided, else empty string."""
    if context_hint and context_hint.strip():
        return f"CONTEXT: This text is for the following situation — {context_hint.strip()}. Adapt your output accordingly.\n"
    return ""


def build_prompt(req: TextRequest) -> str:
    """
    Construct the full prompt string from a structured request.

    Prompt lifecycle:
        1. Determine mode (translate / refine / explain)
        2. Look up style instruction from the relevant map
        3. Inject optional context hint if provided
        4. Assemble final prompt with clear role + instructions
    """
    context_line = _build_context_line(req.context_hint)

    # ── MODE: REFINE ──────────────────────────────────────────────────
    if req.mode == "refine":
        instruction = REFINE_STYLES.get(req.tone, f"Maintain a {req.tone} tone.")

        return (
            f"You are an expert editor. Rewrite the following text. "
            f"Reply with ONLY the refined text — no greetings, no commentary.\n"
            f"STYLE GOAL: {instruction}\n"
            f"{context_line}"
            f"Keep the core meaning but completely adapt the style.\n\n"
            f"Text:\n{req.source_text}"
        )

    # ── MODE: EXPLAIN ─────────────────────────────────────────────────
    # The frontend sends the original text AND the translated text as
    # separate structured fields. The backend constructs the full prompt.
    elif req.mode == "explain":
        return (
            f"Act as a friendly language tutor.\n"
            f"The user's original text: \"{req.source_text}\"\n"
            f"The translation into {req.target_lang}: \"{req.translated_text}\"\n\n"
            f"Write a short, simple paragraph (max 5 lines) explaining the translation. "
            f"Do NOT use bullet points. "
            f"Focus on why specific words were chosen for this context and grammar, "
            f"and briefly mention why a literal translation would be wrong here. "
            f"Do not greet the user. Just provide the explanation directly."
        )

    # ── MODE: TRANSLATE (default) ─────────────────────────────────────
    else:
        instruction = TRANSLATION_STYLES.get(req.tone, f"Maintain a {req.tone} tone.")
        from_lang = (
            f"from {req.source_lang}"
            if req.source_lang != "auto"
            else "from the detected language"
        )

        return (
            f"Act as a professional translator. Translate {from_lang} into {req.target_lang}.\n"
            f"TRANSLATION STYLE: {instruction}\n"
            f"{context_line}"
            f"Do not include explanations. Reply with ONLY the translated text.\n\n"
            f"Text:\n{req.source_text}"
        )


# ---------------------------------------------------------------------------
# 7. API Endpoint
#    Single endpoint handles all processing modes via the 'mode' field.
#    Request lifecycle: validate → build prompt → call Gemini → return result.
# ---------------------------------------------------------------------------
@app.post(
    "/process_text",
    response_model=TextResponse,
    tags=["Translation"],
    summary="Translate, refine, or explain multilingual text",
    description=(
        "Processes text using Google Gemini based on the specified mode. "
        "Supports 'translate' (with tone and optional context), 'refine' "
        "(style rewriting), and 'explain' (grammar analysis of translations). "
        "All prompt engineering is handled server-side."
    ),
    responses={
        200: {
            "description": "Successfully processed text",
            "content": {
                "application/json": {
                    "example": {"result": "Translated or refined text appears here."}
                }
            },
        },
        400: {"description": "Empty or invalid source text"},
        502: {"description": "AI model returned an empty response"},
        500: {"description": "Internal server error"},
    },
)
async def process_text(request: TextRequest):
    """
    Main processing endpoint.

    Accepts a structured payload, constructs the appropriate prompt,
    sends it to the Gemini API, and returns the cleaned result.
    """
    # ── Input validation ──────────────────────────────────────────────
    if not request.source_text.strip():
        raise HTTPException(status_code=400, detail="Source text cannot be empty.")

    if request.mode == "explain" and not request.translated_text:
        raise HTTPException(
            status_code=400,
            detail="Explain mode requires 'translated_text' to be provided.",
        )

    try:
        # ── Prompt construction ───────────────────────────────────────
        final_prompt = build_prompt(request)

        # ── Gemini API call ───────────────────────────────────────────
        response = model.generate_content(final_prompt)

        # ── Response validation (defensive programming) ───────────────
        if not response.text:
            raise HTTPException(
                status_code=502,
                detail="AI model returned an empty response. Please try again.",
            )

        return {"result": response.text.strip()}

    except HTTPException:
        # Re-raise HTTP exceptions as-is (don't wrap them in a 500)
        raise
    except Exception as e:
        print(f"[ERROR] process_text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 8. Health Check
#    Simple endpoint to verify the API is running — useful for monitoring
#    and deployment health checks.
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    tags=["System"],
    summary="API health check",
    description="Returns the current status of the API server.",
)
async def health_check():
    """Returns API status for monitoring and deployment verification."""
    return {"status": "healthy", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# 9. Development Server
#    When running directly with `python main.py`, uvicorn starts with
#    hot-reload enabled for rapid development iteration.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
