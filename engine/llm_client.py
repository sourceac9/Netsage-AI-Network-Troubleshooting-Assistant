import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
try:
    import google.generativeai as genai
except ImportError:
    genai = None

def get_ai_diagnosis(prompt_payload: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return _fallback_offline_response("GEMINI_API_KEY not set or google-generativeai not installed")
    
    try:
        genai.configure(api_key=api_key.strip())
        # Using Gemini 3.5 Flash, configured for JSON
        model = genai.GenerativeModel('gemini-3.5-flash', generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt_payload)
        
        text = response.text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return _fallback_offline_response(f"Gemini returned invalid JSON: {text[:200]}")
            
    except Exception as e:
        logging.error(f"Error calling Gemini: {e}")
        return _fallback_offline_response(f"API Error: {str(e)}")


def _fallback_offline_response(reason: str) -> Dict[str, Any]:
    return {
        "root_cause": f"[AI Unavailable: {reason}] Rely exclusively on deterministic rule findings.",
        "osi_layer": "Unknown",
        "confidence": "Low",
        "evidence": [],
        "concept_tag": "GENERAL",
        "next_command": "",
        "fix_steps": [],
        "safety_assessment": "AI unavailable. Human must review manually.",
        "ai_unavailable": True
    }
