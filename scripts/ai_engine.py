#!/usr/bin/env python3
"""
Multi-Tier Free AI Fallback Engine for Second Brain.
Features:
1. Automatic Model Cascade across all available free Gemini models:
   gemini-3.8-flash -> gemini-3.7-flash -> gemini-3.6-flash -> gemini-3.5-flash-lite -> gemini-flash-latest
2. Optional Groq Free Tier integration (Whisper-large-v3 for audio + Llama-3.3-70b for text).
3. Zero-Failure Local Deterministic Fallback if all cloud providers fail.
Pure Python 3 Standard Library (Zero external pip dependencies).
"""

import os
import re
import json
import time
import base64
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Ordered list of free Gemini models to try automatically
GEMINI_CASCADE = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

def load_env():
    """Loads variables from .env."""
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v

load_env()

def clean_json_response(raw_text: str) -> dict:
    """Strips Markdown fences from LLM response and parses JSON."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text).strip()
    return json.loads(raw_text)

def call_gemini_with_fallback(payload: dict, gemini_key: str, preferred_model: str = None) -> tuple[dict, str]:
    """Tries preferred model, then automatically cascades through all available free models."""
    models_to_try = []
    if preferred_model and preferred_model in GEMINI_CASCADE:
        models_to_try.append(preferred_model)
    for m in GEMINI_CASCADE:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = clean_json_response(raw_text)
                return parsed, model_name
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            print(f"[-] Model {model_name} returned HTTP {e.code}. Attempting fallback...")
            last_error = f"{model_name} HTTP {e.code}: {err_body}"
            # Sleep briefly before switching model to respect burst limits
            time.sleep(1)
            continue
        except Exception as e:
            print(f"[-] Model {model_name} error: {e}. Attempting fallback...")
            last_error = f"{model_name}: {e}"
            time.sleep(1)
            continue

    raise RuntimeError(f"All Gemini cascade models failed. Last error: {last_error}")

def call_groq_api(prompt: str, groq_key: str) -> dict:
    """Fallback to Groq free tier (Llama-3.3-70b-versatile)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are an executive knowledge engineer. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        raw_text = body["choices"][0]["message"]["content"]
        return clean_json_response(raw_text)

def parse_text_with_ai(raw_content: str, filename: str) -> tuple[dict, str]:
    """Parses text note with automatic multi-tier free model cascade."""
    prompt = f"""
You are the AI Cognitive Ingestion Engine for an AI Systems Engineer & Knowledge Architecture Specialist.
Cognitive profile:
- deliverable-first ("buatkan X", clear concrete output)
- high concurrency (multi-lane: core_work vs side_builder vs meta_system)
- statistically grounded, executive-ready, structured tables/checklists
- language: Indonesian default, English for technical terms
- ideas pushed to deployment.

Analyze the raw dump from `{filename}`.
Produce a JSON response with:
1. "title": Crisp deliverable title.
2. "slug": kebab-case slug.
3. "stream": One of ["core_work", "side_builder", "meta_system"].
4. "target_folder": One of ["in_motion/core_work", "in_motion/side_builder", "lattices/mental_models", "lattices/playbooks"].
5. "type": One of ["in_motion", "lattice"].
6. "status": One of ["active", "incubating", "evergreen"].
7. "tags": Array of strings.
8. "core_insights": Array of 2-4 grounded bullet points.
9. "key_entities": Array of wikilinks (e.g. ["[[eval-harness-v1]]"]).
10. "action_items": Array of checklist items starting with "- [ ]".
11. "formatted_markdown": Complete GitHub Flavored Markdown note string including YAML frontmatter.

Content:
\"\"\"
{raw_content}
\"\"\"
"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    groq_key = os.getenv("GROQ_API_KEY")

    # Tier 1: Gemini Cascade
    if gemini_key:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }
        try:
            return call_gemini_with_fallback(payload, gemini_key, preferred_model)
        except Exception as e:
            print(f"[!] Gemini cascade exhausted: {e}")

    # Tier 2: Groq Free Tier
    if groq_key:
        try:
            print("[*] Switching to Groq Free Tier (Llama-3.3-70b)...")
            return call_groq_api(prompt, groq_key), "groq/llama-3.3-70b"
        except Exception as e:
            print(f"[!] Groq free tier failed: {e}")

    # Tier 3: Local Deterministic Heuristic
    import ingest
    print("[*] Switching to Local Deterministic Fallback Engine...")
    return ingest.local_heuristic_parse(raw_content, filename), "local_heuristic"

def process_audio_with_ai(audio_bytes: bytes, mime_type: str = "audio/ogg") -> tuple[dict, str]:
    """Transcribes and structures voice note with automatic free model cascade."""
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    prompt = """
You are the AI Cognitive Ingestion Engine for an AI Systems Engineer & Knowledge Architecture Specialist.
The user sent a VOICE NOTE / AUDIO DUMP.
1. Accurately transcribe the spoken thoughts (Indonesian/English).
2. Analyze the transcript according to the user's cognitive profile (deliverable-first, high concurrency, executive tables, action checklists).
Produce a JSON response with:
1. "transcription": Full verbatim transcription.
2. "title": Crisp executive title.
3. "slug": kebab-case identifier.
4. "stream": One of ["core_work", "side_builder", "meta_system"].
5. "target_folder": One of ["in_motion/core_work", "in_motion/side_builder", "lattices/mental_models", "lattices/playbooks"].
6. "type": One of ["in_motion", "lattice"].
7. "status": One of ["active", "incubating", "evergreen"].
8. "tags": Array of strings.
9. "core_insights": Array of 2-4 grounded bullet points.
10. "key_entities": Array of wikilinks.
11. "action_items": Array of checklist items starting with "- [ ]".
12. "formatted_markdown": Complete GitHub Flavored Markdown note string including YAML frontmatter.
"""
    gemini_key = os.getenv("GEMINI_API_KEY")
    preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is required for multimodal audio processing.")

    payload = {
        "contents": [
            {
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": b64_audio}},
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    return call_gemini_with_fallback(payload, gemini_key, preferred_model)
