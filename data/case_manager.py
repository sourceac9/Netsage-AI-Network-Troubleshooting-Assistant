import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).parent
CASES_CSV = DATA_DIR / "cases.csv"
AI_PREDICTIONS = DATA_DIR / "ai_predictions.json"
MANUAL_REVIEWS = DATA_DIR / "manual_reviews.json"
ACCOUNTABILITY_LOG = DATA_DIR / "ai_accountability_log.json"

def _ensure_file(path: Path, default_content: str = "[]"):
    if not path.exists():
        path.write_text(default_content, encoding="utf-8")

def get_all_cases() -> List[Dict[str, str]]:
    """Reads all troubleshooting cases from the CSV file."""
    if not CASES_CSV.exists():
        return []
    with open(CASES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def get_case_by_id(case_id: str) -> Optional[Dict[str, str]]:
    for case in get_all_cases():
        if case["case_id"] == case_id:
            return case
    return None

def add_case(case_data: Dict[str, str]) -> str:
    """Appends a new case to cases.csv and returns its assigned case_id."""
    cases = get_all_cases()
    # Auto-generate case_id if not present or empty
    if "case_id" not in case_data or not case_data["case_id"]:
        custom_ids = []
        for c in cases:
            cid = c.get("case_id", "")
            if cid.startswith("CUSTOM-"):
                try:
                    num = int(cid.split("-")[1])
                    custom_ids.append(num)
                except ValueError:
                    pass
        next_num = max(custom_ids) + 1 if custom_ids else 1
        case_data["case_id"] = f"CUSTOM-{next_num:02d}"
    
    headers = [
        "case_id", "title", "symptom", "topology_note", "show_outputs",
        "expected_fault", "osi_layer", "concept_tag", "severity", "suggested_fix"
    ]
    
    # Ensure all headers exist in case_data
    row = {h: case_data.get(h, "") for h in headers}
    
    file_exists = CASES_CSV.exists()
    with open(CASES_CSV, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
        
    return case_data["case_id"]

def update_case_metadata(case_id: str, concept_tag: str, osi_layer: str):
    """Updates a case's concept_tag and osi_layer in cases.csv."""
    cases = get_all_cases()
    updated = False
    for c in cases:
        if c.get("case_id") == case_id:
            c["concept_tag"] = concept_tag
            c["osi_layer"] = osi_layer
            updated = True
            
    if updated:
        headers = [
            "case_id", "title", "symptom", "topology_note", "show_outputs",
            "expected_fault", "osi_layer", "concept_tag", "severity", "suggested_fix"
        ]
        with open(CASES_CSV, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(cases)

def load_json(path: Path) -> Any:
    _ensure_file(path)
    try:
        with open(path, mode="r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_json(path: Path, data: Any):
    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_ai_predictions() -> List[Dict[str, Any]]:
    return load_json(AI_PREDICTIONS)

def save_ai_prediction(case_id: str, prediction_data: Dict[str, Any]):
    preds = get_ai_predictions()
    # Remove existing prediction for this case if it exists
    preds = [p for p in preds if p.get("case_id") != case_id]
    prediction_data["case_id"] = case_id
    preds.append(prediction_data)
    save_json(AI_PREDICTIONS, preds)

def get_prediction_for_case(case_id: str) -> Optional[Dict[str, Any]]:
    for p in get_ai_predictions():
        if p.get("case_id") == case_id:
            return p
    return None

def get_manual_reviews() -> List[Dict[str, Any]]:
    return load_json(MANUAL_REVIEWS)

def save_manual_review(review_data: Dict[str, Any]):
    reviews = get_manual_reviews()
    reviews.append(review_data)
    save_json(MANUAL_REVIEWS, reviews)
    
    # Auto-generate accountability log if edited or rejected
    status = review_data.get("status")
    if status in ["Edited", "Rejected"]:
        case_id = review_data.get("case_id")
        ai_pred = get_prediction_for_case(case_id)
        if ai_pred:
            ai_said = ai_pred.get("ai_diagnosis", {}).get("root_cause", "Unknown")
        else:
            ai_said = "No AI prediction found"
            
        case_details = get_case_by_id(case_id) or {}
        correct_ans = review_data.get("revised_fix") or case_details.get("suggested_fix", "")
        
        log_entry = {
            "case_id": case_id,
            "ai_said": ai_said,
            "correct_answer": correct_ans,
            "why_ai_was_wrong": review_data.get("engineer_note", "No note provided"),
            "timestamp": review_data.get("timestamp", "")
        }
        logs = get_accountability_logs()
        logs.append(log_entry)
        save_json(ACCOUNTABILITY_LOG, logs)

    # Write to responsible_ai_log.csv
    csv_path = DATA_DIR / "responsible_ai_log.csv"
    file_exists = csv_path.exists()
    with open(csv_path, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["case_id", "human_verdict", "safety_rationale_and_learnings", "timestamp"])
        writer.writerow([
            review_data.get("case_id"),
            status,
            review_data.get("engineer_note", "No safety note provided by engineer."),
            review_data.get("timestamp", "")
        ])

def get_accountability_logs() -> List[Dict[str, Any]]:
    return load_json(ACCOUNTABILITY_LOG)

def hide_anchor_links():
    """Injects CSS globally to hide the hover link icons next to headers."""
    import streamlit as st
    st.markdown("""
    <style>
        .anchor-link, a.anchor-link, h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
