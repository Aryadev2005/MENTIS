"""LangGraph OA solver agent — all branch routers, 6 nodes."""

import logging
from typing import TypedDict

from langgraph.graph import StateGraph, END

from ..services.openai_service import parse_oa_screenshot
from ..services.claude_service import solve_with_vision
from ..models.vector.qdrant_client import oa_question_store
from ..database.redis_client import cache

logger = logging.getLogger(__name__)

DOMAIN_SYSTEM_PROMPTS = {
    "coding": (
        "You are an expert competitive programmer. Solve this problem with a complete, correct solution. "
        "Output: (1) Algorithm approach in 2 sentences, (2) Time & Space complexity, "
        "(3) Complete working code with comments, (4) Walk through with given example. "
        "Zero hallucination — only output correct code."
    ),
    "mcq_aptitude": (
        "You are a quantitative aptitude expert. Solve this aptitude question step-by-step. "
        "Show all working. State the correct option clearly. "
        "Output: {working_steps, correct_option, explanation}"
    ),
    "mcq_technical_cs": (
        "You are a CS expert with deep knowledge of OS, DBMS, Computer Networks, OOP, DSA, "
        "and System Design. Answer this MCQ with explanation. "
        "Output: {correct_option, explanation, key_concept}"
    ),
    "mcq_technical_ece": (
        "You are an Electronics & Communication Engineering expert specializing in Analog Circuits, "
        "Digital Electronics, Signals & Systems, VLSI, and Communications. "
        "Answer this MCQ with a clear explanation. Output: {correct_option, explanation, key_concept}"
    ),
    "mcq_technical_mech": (
        "You are a Mechanical Engineering expert covering Thermodynamics, Fluid Mechanics, "
        "Manufacturing Processes, Strength of Materials, and Machine Design. "
        "Answer this MCQ step by step. Output: {correct_option, explanation, key_concept}"
    ),
    "mcq_technical_civil": (
        "You are a Civil Engineering expert in Structural Analysis, Geotechnical Engineering, "
        "Transportation, Environmental Engineering, and Fluid Mechanics. "
        "Answer this MCQ with explanation. Output: {correct_option, explanation, key_concept}"
    ),
    "mcq_technical_chem": (
        "You are a Chemical Engineering expert in Mass Transfer, Heat Transfer, "
        "Chemical Reaction Engineering, Process Control, and Thermodynamics. "
        "Answer this MCQ step by step. Output: {correct_option, explanation, key_concept}"
    ),
    "debugging": (
        "You are an expert debugger. Find ALL bugs in this code. "
        "Output: (1) List of bugs with line numbers, (2) Corrected code, (3) Explanation of each bug."
    ),
    "output_prediction": (
        "You are a code execution engine. Trace through this code exactly as a computer would. "
        "Show variable states at each step. Output the exact program output. Be precise."
    ),
}

QUESTION_TYPE_TO_CONFIDENCE_BASE = {
    "mcq_aptitude": 92,
    "mcq_technical_cs": 88,
    "mcq_technical_ece": 85,
    "mcq_technical_mech": 83,
    "mcq_technical_civil": 82,
    "mcq_technical_chem": 81,
    "debugging": 80,
    "output_prediction": 90,
    "coding": 75,
}


class OAState(TypedDict):
    screenshot_b64: str
    session_id: str
    user_id: str
    department: str | None
    company: str | None
    preferred_language: str

    parsed_question: dict
    question_type: str | None
    retrieved_context: str

    solution: str
    approach: str | None
    code: str | None
    time_complexity: str | None
    confidence: int
    confidence_level: str
    warning: str | None
    similar_found: bool
    error: str | None


async def node_capture_parse(state: OAState) -> dict:
    """Node 2: Parse OA screenshot with GPT-4o Vision."""
    try:
        parsed = await parse_oa_screenshot(state["screenshot_b64"])
        if not parsed:
            parsed = await solve_with_vision(
                state["screenshot_b64"],
                "Extract the complete question from this screenshot. Output JSON with keys: question_text, question_type, options, code_snippet.",
            )

        return {
            "parsed_question": parsed,
            "question_type": parsed.get("question_type", "mcq_aptitude"),
        }
    except Exception as e:
        logger.error(f"Screenshot parse failed: {e}")
        return {"error": str(e), "parsed_question": {}, "question_type": None}


async def node_retrieve_similar(state: OAState) -> dict:
    """Node 3: Retrieve similar OA questions from Qdrant."""
    question_text = state["parsed_question"].get("question_text", "")
    if not question_text:
        return {"retrieved_context": "", "similar_found": False}

    filters: dict = {}
    if state.get("company"):
        filters["company"] = state["company"]
    if state.get("department"):
        filters["department"] = state["department"]

    try:
        results = await oa_question_store.search(
            query=question_text,
            limit=3,
            score_threshold=0.80,
            filters=filters if filters else None,
            cache=cache,
        )

        if results:
            context = "\n\n".join([
                f"[Similar OA Question - Score: {r['score']:.2f}]\n"
                f"Q: {r['payload'].get('question', '')[:300]}\n"
                f"A: {r['payload'].get('answer', '')[:500]}"
                for r in results
            ])
            return {"retrieved_context": context, "similar_found": True}

    except Exception as e:
        logger.warning(f"Qdrant retrieval failed: {e}")

    return {"retrieved_context": "", "similar_found": False}


async def node_solve(state: OAState) -> dict:
    """Node 4: Route to specialized solver and generate solution."""
    question_type = state.get("question_type", "mcq_aptitude")
    system_prompt = DOMAIN_SYSTEM_PROMPTS.get(question_type, DOMAIN_SYSTEM_PROMPTS["mcq_aptitude"])

    parsed = state["parsed_question"]
    question_text = parsed.get("question_text", "")
    options = parsed.get("options", [])
    code = parsed.get("code_snippet", "")
    constraints = parsed.get("constraints", "")

    user_prompt = f"QUESTION:\n{question_text}"
    if options:
        user_prompt += f"\n\nOPTIONS:\nA) {options[0] if len(options) > 0 else ''}\nB) {options[1] if len(options) > 1 else ''}\nC) {options[2] if len(options) > 2 else ''}\nD) {options[3] if len(options) > 3 else ''}"
    if code:
        user_prompt += f"\n\nCODE:\n```\n{code}\n```"
    if constraints:
        user_prompt += f"\n\nCONSTRAINTS: {constraints}"

    if state.get("retrieved_context"):
        user_prompt = f"REFERENCE (similar solved problem):\n{state['retrieved_context'][:1000]}\n\n{user_prompt}"

    if question_type == "coding":
        user_prompt += f"\n\nPreferred language: {state.get('preferred_language', 'Python')}"

    try:
        result = await solve_with_vision(
            state["screenshot_b64"],
            f"{system_prompt}\n\n{user_prompt}",
        )

        solution = result.get("answer", "") or result.get("explanation", "") or str(result)
        approach = result.get("approach") or result.get("algorithm")
        code_result = result.get("code") or result.get("correct_code")
        time_complexity = result.get("time_complexity")

        if not solution:
            from ..services.claude_service import stream_answer
            tokens = []
            async for token in stream_answer(user_prompt, system_prompt):
                tokens.append(token)
            solution = "".join(tokens)

        base_confidence = QUESTION_TYPE_TO_CONFIDENCE_BASE.get(question_type, 75)
        confidence = base_confidence if state.get("similar_found") else max(60, base_confidence - 10)

        confidence_level = "high" if confidence >= 85 else ("medium" if confidence >= 65 else "low")
        warning = None if confidence >= 65 else "Low confidence — please verify this answer manually."

        return {
            "solution": solution,
            "approach": approach,
            "code": code_result,
            "time_complexity": time_complexity,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "warning": warning,
        }

    except Exception as e:
        logger.error(f"OA solve failed: {e}")
        return {
            "solution": "Could not solve this question automatically. Please attempt manually.",
            "confidence": 0,
            "confidence_level": "low",
            "warning": "Solver encountered an error. Please verify manually.",
            "error": str(e),
        }


def build_oa_graph() -> StateGraph:
    graph = StateGraph(OAState)

    graph.add_node("parse_question", node_capture_parse)
    graph.add_node("retrieve_similar", node_retrieve_similar)
    graph.add_node("solve", node_solve)

    graph.set_entry_point("parse_question")
    graph.add_edge("parse_question", "retrieve_similar")
    graph.add_edge("retrieve_similar", "solve")
    graph.add_edge("solve", END)

    return graph.compile()


oa_graph = build_oa_graph()
