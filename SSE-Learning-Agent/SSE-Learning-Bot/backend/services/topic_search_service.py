"""Topic Search and Content Synthesis service using Tavily Web Search and OpenRouter LLMs."""
import os
import httpx
from dotenv import load_dotenv
from backend.config import settings

load_dotenv()


MODEL_MAP = {
    "gemma": "google/gemma-2-27b-it:free",
    "gemma-27b": "google/gemma-2-27b-it:free",
    "gemma-29b": "google/gemma-2-27b-it:free",
    "nemotron": "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "free_router": "openrouter/auto",
    "auto": "openrouter/auto",
}



def _get_openrouter_key() -> str:
    """Retrieve OpenRouter API key from settings or environment."""
    key = getattr(settings, "openrouter_api_key", "") or os.getenv("OPENROUTER_API_KEY", "")
    return key.strip().strip('"').strip("'")


def _get_tavily_key() -> str:
    """Retrieve Tavily API key from settings or environment."""
    key = getattr(settings, "tavily_api_key", "") or os.getenv("TAVILY_API_KEY", "")
    return key.strip().strip('"').strip("'")


async def search_tavily(topic: str) -> dict:
    """Search live web for topic details using Tavily REST API."""
    tavily_key = _get_tavily_key()
    if not tavily_key:
        print("[Tavily] No TAVILY_API_KEY configured. Skipping web search.", flush=True)
        return {"answer": "", "results": [], "sources": []}

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_key,
        "query": f"comprehensive guide study notes {topic}",
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": 5,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                answer = data.get("answer", "")
                sources = [{"title": r.get("title"), "url": r.get("url")} for r in results if r.get("url")]
                return {
                    "answer": answer,
                    "results": results,
                    "sources": sources,
                }
            else:
                print(f"[Tavily Error] HTTP {response.status_code}: {response.text}", flush=True)
    except Exception as e:
        print(f"[Tavily Search Exception] {e}", flush=True)

    return {"answer": "", "results": [], "sources": []}


async def synthesize_topic_content(topic: str, model_choice: str = "nemotron") -> dict:
    """Intelligently gather content via Tavily search and synthesize study material using OpenRouter or configured LLM."""
    load_dotenv(override=True)
    
    openrouter_key = _get_openrouter_key()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip('"').strip("'")
    gemini_key = getattr(settings, "gemini_api_key", "") or os.getenv("GEMINI_API_KEY", "")

    if not (openrouter_key or openai_key or gemini_key):
        raise ValueError("No LLM API key configured. Please set OPENROUTER_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY in your .env file.")

    # 1. Fetch live search content from Tavily
    tavily_data = await search_tavily(topic)
    tavily_answer = tavily_data.get("answer", "")
    tavily_results = tavily_data.get("results", [])
    sources = tavily_data.get("sources", [])

    # Format web search context
    web_context_blocks = []
    if tavily_answer:
        web_context_blocks.append(f"TAVILY DIRECT SUMMARY:\n{tavily_answer}")

    for idx, item in enumerate(tavily_results, 1):
        title = item.get("title", "Reference")
        snippet = item.get("content", "").strip()
        if snippet:
            web_context_blocks.append(f"Source [{idx}] {title}:\n{snippet}")

    web_context = "\n\n".join(web_context_blocks)
    if not web_context.strip():
        web_context = "No live web search context available. Rely on deep internal technical knowledge."

    # Prompt construction with strict Engineering Guardrail
    system_prompt = (
        "You are an expert Engineering Professor and curriculum designer. "
        "STRICT GUARDRAIL INSTRUCTION: You MUST ONLY synthesize content for topics related to "
        "ENGINEERING and TECHNOLOGY subjects (e.g., Computer Science, Software Engineering, Electrical, "
        "Mechanical, Civil, Chemical, Biomedical, Aerospace, Robotics, Artificial Intelligence/Machine Learning, "
        "Data Science, Data Structures, Applied Mathematics or Physics for Engineering).\n\n"
        "CRITICAL RULE: If the requested topic is NOT related to engineering, technology, mathematics, or applied sciences "
        "(for example: celebrity gossip, pop culture, entertainment, sports trivia, cooking recipes, fashion, fiction, "
        "or political opinions), you MUST respond ONLY with the exact line:\n"
        "[GUARDRAIL_REJECTED: NOT_ENGINEERING]\n"
        "Do NOT write any study guide if the topic is non-engineering."
    )

    user_prompt = f"""Target Study Topic: {topic}

Web Search Context & References:
---
{web_context}
---

INSTRUCTIONS:
First verify if "{topic}" is an engineering/technology/math topic. If NOT, return ONLY [GUARDRAIL_REJECTED: NOT_ENGINEERING].
If YES, create a comprehensive, well-structured, clear study guide on "{topic}".
Organize the material into the following structured sections using Markdown:

# {topic}

## 1. Overview & Core Definition
- Concise definition and real-world importance of {topic}.

## 2. Key Concepts & Principles
- Detailed step-by-step breakdown of fundamental concepts, mechanisms, and rules.

## 3. Practical Examples & Applications
- Clear real-world or technical examples/diagrams/code snippets illustrating the topic in action.

## 4. High-Yield Insights & Common Pitfalls
- Pro-tips, key takeaways, and frequent misconceptions to watch out for.

## 5. Summary Checklist
- Quick recap bullets summarizing the essential points.

Make the material thorough, clear, educational, and easy to learn from.
"""


    model_used = model_choice
    synthesized_text = ""

    # Option A: OpenRouter API
    if openrouter_key:
        model_id = MODEL_MAP.get(model_choice.lower(), model_choice)
        if not model_id or model_id in ("default", "custom"):
            model_id = getattr(settings, "openrouter_model", "") or os.getenv("OPENROUTER_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct:free")

        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://sse-learning-bot.local",
            "X-Title": "SSE Learning Bot",
            "Content-Type": "application/json",
        }
        base_url = (getattr(settings, "openrouter_base_url", "") or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        url = f"{base_url}/chat/completions"

        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2500,
        }

        print(f"[TopicSearch] Calling OpenRouter model={model_id} for topic='{topic}'...", flush=True)
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    synthesized_text = choices[0].get("message", {}).get("content", "").strip()
                    model_used = f"OpenRouter ({model_id})"
            else:
                print(f"[TopicSearch] OpenRouter returned HTTP {res.status_code}. Using fallback LLM...", flush=True)

    # Option B: Fallback to OpenAI / Proxy if OpenRouter not present or failed
    if not synthesized_text and openai_key:
        try:
            print("[TopicSearch] Synthesizing topic using OpenAI/Proxy LLM...", flush=True)
            from backend.services.llm_service import _call_openai_or_proxy
            synthesized_text = await _call_openai_or_proxy(
                system_prompt=system_prompt,
                history=[],
                default_user_prompt=user_prompt,
            )
            model_used = "OpenAI / Proxy LLM"
        except Exception as e:
            print(f"[TopicSearch Proxy Error] {e}", flush=True)

    # Option C: Fallback to Gemini
    if not synthesized_text and gemini_key:
        try:
            print("[TopicSearch] Synthesizing topic using Gemini REST API...", flush=True)
            from backend.services.llm_service import _call_gemini_api
            synthesized_text = await _call_gemini_api(prompt=user_prompt, system_instruction=system_prompt)
            model_used = "Google Gemini"
        except Exception as e:
            print(f"[TopicSearch Gemini Error] {e}", flush=True)

    if not synthesized_text:
        raise RuntimeError("Could not synthesize topic content. Please verify your LLM API keys in .env.")

    # Guardrail Validation Check
    if "[GUARDRAIL_REJECTED" in synthesized_text or "NOT_ENGINEERING" in synthesized_text:
        raise ValueError(
            "🔒 Engineering Guardrail: This SSE Learning Bot is dedicated exclusively to Engineering & Technology subjects "
            "(Computer Science, Software Engineering, Electrical, Mechanical, Civil, AI/ML, Robotics, Mathematics, etc.). "
            "Please enter a valid engineering or computer science topic."
        )

    return {

        "success": True,
        "topic_name": topic,
        "synthesized_text": synthesized_text,
        "sources": sources,
        "model_used": model_used,
    }

