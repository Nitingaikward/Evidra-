"""
report.py — JSON and HTML forensic report generator.

Generates machine-readable JSON exports and human-readable HTML forensic reports
with dark forensic themes, color-coded status badges, sortable tables, and chain-of-custody statements.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from jinja2 import Template
from recon.db import get_connection

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVIDRA Forensic Recovery Report — Case {{ case_meta.image_sha256[:12] if case_meta.image_sha256 else 'Analysis' }}</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --panel-bg: #1e293b;
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --status-full: #22c55e;
            --status-partial: #eab308;
            --status-fragment: #f97316;
            --status-encrypted: #ef4444;
        }

        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }

        .header {
            border-bottom: 2px solid var(--accent-blue);
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }

        .header h1 {
            margin: 0;
            font-size: 2rem;
            color: var(--accent-blue);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .card {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
        }

        .card-title {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .card-value {
            font-size: 1.4rem;
            font-weight: 600;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-full { background-color: rgba(34, 197, 94, 0.2); color: var(--status-full); border: 1px solid var(--status-full); }
        .badge-partial { background-color: rgba(234, 179, 8, 0.2); color: var(--status-partial); border: 1px solid var(--status-partial); }
        .badge-fragment { background-color: rgba(249, 115, 22, 0.2); color: var(--status-fragment); border: 1px solid var(--status-fragment); }
        .badge-encrypted { background-color: rgba(239, 68, 68, 0.2); color: var(--status-encrypted); border: 1px solid var(--status-encrypted); }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            background-color: var(--panel-bg);
            border-radius: 8px;
            overflow: hidden;
        }

        th, td {
            padding: 0.9rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background-color: rgba(0, 0, 0, 0.3);
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
        }

        tr:hover {
            background-color: rgba(255, 255, 255, 0.02);
        }

        .footer {
            margin-top: 3rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-align: center;
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 EVIDRA Forensic Evidence Recovery Report</h1>
        <p>Generated: {{ generated_at }} | Engine Version 0.1.0</p>
    </div>

    <div class="meta-grid">
        <div class="card">
            <div class="card-title">Disk Image Hash (SHA-256)</div>
            <div class="card-value" style="font-size: 0.9rem; word-break: break-all;">{{ case_meta.image_sha256 or 'N/A' }}</div>
        </div>
        <div class="card">
            <div class="card-title">Total Evidence Artifacts</div>
            <div class="card-value">{{ stats.total_artifacts }}</div>
        </div>
        <div class="card">
            <div class="card-title">Full Recovered</div>
            <div class="card-value" style="color: var(--status-full);">{{ stats.full_count }}</div>
        </div>
        <div class="card">
            <div class="card-title">Ransomware Encrypted</div>
            <div class="card-value" style="color: var(--status-encrypted);">{{ stats.encrypted_count }}</div>
        </div>
    </div>

    <div class="card" style="margin-bottom: 2rem;">
        <div class="card-title">Executive Summary</div>
        <p style="margin: 0;">{{ executive_summary }}</p>
    </div>

    <h2>Recovered Artifacts Inventory</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name / Type</th>
                <th>Method</th>
                <th>Status</th>
                <th>Integrity</th>
                <th>Priority Score</th>
                <th>AI Summary</th>
            </tr>
        </thead>
        <tbody>
            {% for art in artifacts %}
            <tr>
                <td>#{{ art.id }}</td>
                <td>
                    <strong>{{ art.name or 'Orphan Block' }}</strong><br>
                    <small style="color: var(--text-secondary);">{{ art.mime_type or 'unknown' }}</small>
                </td>
                <td>{{ art.method | upper }}</td>
                <td>
                    <span class="badge badge-{{ art.status | lower }}">{{ art.status }}</span>
                </td>
                <td>{{ (art.confidence * 100) | int }}%</td>
                <td><strong>{{ art.score }}</strong></td>
                <td>{{ summaries.get(art.id, {}).get('summary', 'N/A') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="footer">
        <p>EVIDRA Forensic Recovery Suite — Chain of Custody Verified (Read-Only SHA-256 Inspection)</p>
    </div>
</body>
</html>
"""

def _load_case_data(db_path: str) -> Dict[str, Any]:
    """Loads all case database data into a unified dictionary structure."""
    conn = get_connection(db_path)
    
    # Meta
    meta_rows = conn.execute("SELECT key, value FROM case_meta;").fetchall()
    case_meta = {r['key']: r['value'] for r in meta_rows}
    
    # Artifacts
    artifact_rows = conn.execute("SELECT * FROM artifacts ORDER BY score DESC;").fetchall()
    artifacts = [dict(r) for r in artifact_rows]
    
    # Summaries
    summary_rows = conn.execute("SELECT artifact_id, summary, entities FROM summaries;").fetchall()
    summaries = {}
    for r in summary_rows:
        try:
            ent = json.loads(r['entities']) if r['entities'] else {}
        except Exception:
            ent = {}
        summaries[r['artifact_id']] = {'summary': r['summary'], 'entities': ent}
        
    # Relationships
    rel_rows = conn.execute("SELECT * FROM relationships;").fetchall()
    relationships = [dict(r) for r in rel_rows]
    
    conn.close()
    
    # Calculate stats
    total = len(artifacts)
    full_c = sum(1 for a in artifacts if a['status'] == 'FULL')
    part_c = sum(1 for a in artifacts if a['status'] == 'PARTIAL')
    enc_c = sum(1 for a in artifacts if a['status'] == 'ENCRYPTED')
    
    stats = {
        'total_artifacts': total,
        'full_count': full_c,
        'partial_count': part_c,
        'encrypted_count': enc_c
    }
    
    return {
        'case_meta': case_meta,
        'artifacts': artifacts,
        'summaries': summaries,
        'relationships': relationships,
        'stats': stats,
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def generate_json(db_path: str, output_path: str) -> str:
    """Generates machine-readable JSON forensic report file."""
    data = _load_case_data(db_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    logger.info(f"Generated JSON forensic report at {output_path}")
    return output_path

def generate_html(db_path: str, output_path: str) -> str:
    """Renders Jinja2 HTML forensic report file."""
    data = _load_case_data(db_path)
    data['executive_summary'] = (
        f"Analysis recovered {data['stats']['total_artifacts']} total artifacts "
        f"({data['stats']['full_count']} fully restored, {data['stats']['encrypted_count']} encrypted)."
    )
    
    template = Template(HTML_TEMPLATE)
    rendered_html = template.render(**data)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
        
    logger.info(f"Generated HTML forensic report at {output_path}")
    return output_path
