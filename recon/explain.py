"""
explain.py — AI Document Intelligence powered by Groq (qwen/qwen3.8-27b & openai/gpt-oss-120b).

Generates 2-sentence document summaries and entity extractions for recovered text & document artifacts.
All LLM responses are strictly tagged with ai_generated=True for forensic transparency.
"""

import os
import json
import time
import logging
from typing import Dict, List, Tuple, Any, Optional
from dotenv import load_dotenv

import groq
from recon.db import get_connection

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"

def get_groq_client() -> Optional[groq.Groq]:
    """Retrieves Groq API client instance from environment variables."""
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key.startswith("gsk_...") and len(api_key) < 20:
        logger.warning("GROQ_API_KEY environment variable not configured. Groq AI summaries will operate in mock mode.")
        return None
    try:
        return groq.Groq(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Groq API client: {e}")
        return None

def summarize_artifact(
    text: str,
    file_type: str,
    artifact_name: str,
    client: Optional[groq.Groq] = None
) -> Dict[str, Any]:
    """
    Sends extracted artifact text payload to Groq API for document intelligence:
    Returns dict: {summary: str, entities: dict, model: str, ai_generated: True}
    """
    if not text or len(text.strip()) == 0:
        return {
            'summary': 'Empty document content.',
            'entities': {},
            'model': 'none',
            'ai_generated': True
        }

    if client is None:
        client = get_groq_client()

    if client is None:
        snippet = text[:150].replace("\n", " ")
        return {
            'summary': f"Recovered {file_type} document '{artifact_name}'. Preview: {snippet}...",
            'entities': {'names': [], 'dates': [], 'amounts': []},
            'model': 'mock-mode',
            'ai_generated': True
        }

    prompt = f"""You are a digital forensics AI assistant analyzing recovered evidence.
Analyze the following recovered text payload from file '{artifact_name}' (Type: {file_type}).

Provide a structured JSON response with:
1. "summary": A concise 2-sentence executive summary of the document contents.
2. "entities": An object containing arrays of "names", "dates", "amounts", and "emails" mentioned.

Document text:
\"\"\"
{text[:4000]}
\"\"\"

Respond ONLY with valid JSON.
"""

    try:
        response = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a digital forensics investigator assistant. Respond strictly in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500
        )
        content = response.choices[0].message.content
        res_data = json.loads(content)
        res_data['model'] = DEFAULT_GROQ_MODEL
        res_data['ai_generated'] = True
        return res_data
        
    except groq.RateLimitError:
        logger.warning("Groq API rate limit encountered. Waiting 5s...")
        time.sleep(5)
        return summarize_artifact(text, file_type, artifact_name, client)
    except Exception as e:
        logger.error(f"Error invoking Groq API: {e}")
        return {
            'summary': f"Failed to generate AI summary: {e}",
            'entities': {},
            'model': DEFAULT_GROQ_MODEL,
            'ai_generated': True
        }

def recovery_report_paragraph(stats: Dict[str, Any], client: Optional[groq.Groq] = None) -> str:
    """Generates plain-language forensic recovery assessment paragraph for report headers."""
    if client is None:
        client = get_groq_client()

    if client is None:
        return (
            f"Forensic analysis recovered {stats.get('total_artifacts', 0)} evidence artifacts "
            f"({stats.get('full_count', 0)} fully intact, {stats.get('partial_count', 0)} partial). "
            f"Integrity check verified {stats.get('encrypted_count', 0)} ransomware encrypted files."
        )

    prompt = f"""Write a professional 3-sentence digital forensic executive recovery report paragraph based on these statistics:
{json.dumps(stats, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=250
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Analysis summary completed. Recovered {stats.get('total_artifacts', 0)} evidence artifacts."

def batch_summarize(
    artifact_ids: List[int],
    db_path: str,
    image_path: str,
    max_chars: int = 4000
) -> List[Dict[str, Any]]:
    """Iterates over top-N priority artifacts, calls Groq LLM, and persists results into case.db `summaries` table."""
    conn = get_connection(db_path)
    client = get_groq_client()
    
    summaries = []
    
    for art_id in artifact_ids:
        cursor = conn.execute("SELECT name, source_offset, size, mime_type FROM artifacts WHERE id = ?;", (art_id,))
        row = cursor.fetchone()
        if not row or not os.path.exists(image_path):
            continue
            
        offset = row['source_offset']
        size = row['size']
        name = row['name']
        mime = row['mime_type'] or ''
        
        with open(image_path, 'rb') as f:
            f.seek(offset)
            raw_bytes = f.read(min(size, max_chars))
            
        try:
            text = raw_bytes.decode('utf-8', errors='ignore')
        except Exception:
            text = ""
            
        summary_data = summarize_artifact(text, mime, name, client)
        
        conn.execute(
            "INSERT OR REPLACE INTO summaries (artifact_id, summary, entities) VALUES (?, ?, ?);",
            (art_id, summary_data['summary'], json.dumps(summary_data['entities']))
        )
        conn.commit()
        
        summary_data['artifact_id'] = art_id
        summaries.append(summary_data)
        
    conn.close()
    return summaries
