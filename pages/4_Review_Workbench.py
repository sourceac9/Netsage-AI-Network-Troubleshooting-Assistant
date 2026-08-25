import streamlit as st
from datetime import datetime
from data.case_manager import get_ai_predictions, get_manual_reviews, save_manual_review, get_case_by_id, save_ai_prediction, hide_anchor_links
from engine.diagnose_runner import execute_diagnosis

st.set_page_config(page_title="Review Workbench", page_icon="⚖️", layout="wide")
hide_anchor_links()
st.title("⚖️ Review Workbench")

predictions = get_ai_predictions()
reviews = get_manual_reviews()
reviewed_ids = {r["case_id"] for r in reviews}

pending_cases = [p for p in predictions if p["case_id"] not in reviewed_ids]

if not pending_cases:
    st.success("All AI predictions have been reviewed!")
    st.stop()
    
st.info(f"{len(pending_cases)} cases awaiting review.")

# Select box to choose which pending case to review
pending_options = [p["case_id"] for p in pending_cases]
selected_case_id = st.selectbox(
    "Choose a case to review:",
    options=pending_options,
    format_func=lambda x: f"{x} - {get_case_by_id(x).get('title', 'Untitled') if get_case_by_id(x) else 'Untitled'}"
)

current_review = next(p for p in pending_cases if p["case_id"] == selected_case_id)
case_id = current_review["case_id"]
ai_diag = current_review.get("ai_diagnosis", {})

case = get_case_by_id(case_id) or {}

# Initialize session state for prompt box
if "prompt_box_val" not in st.session_state or st.session_state.get("current_case_id") != case_id:
    st.session_state.prompt_box_val = ""
    st.session_state.current_case_id = case_id

def prefill_ai_fix():
    st.session_state.prompt_box_val = "\n".join(ai_diag.get("fix_steps", []))

st.subheader(f"Reviewing Case: {case_id} - {case.get('title', 'Untitled')}")

# Collapsible Case Details
with st.expander("🔍 View Raw Case Details (Symptom, Topology, Show Outputs)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Symptom:** {case.get('symptom')}")
    with col2:
        st.markdown(f"**Topology Note:** {case.get('topology_note')}")
    st.markdown("**Show Command Output:**")
    st.code(case.get("show_outputs"), language="text")

st.markdown("### AI Output")
st.json(ai_diag)

# Show previous human guidance if any
prev_guidance = current_review.get("human_guidance", "")
if prev_guidance:
    st.info(f"💬 **Previous Guidance:** {prev_guidance}")

st.divider()

st.markdown("### 🛠️ Workbench Panel")
st.markdown("Use this to type **guidance for re-diagnosis**, or edit the **revised fix steps**, or write the **reason for rejection**.")

# Button to copy AI proposed fix steps
st.button("📋 Prefill with AI Proposed Fix", on_click=prefill_ai_fix)

user_input = st.text_area(
    label="Interactive Prompt Box",
    label_visibility="collapsed",
    key="prompt_box_val",
    placeholder="Type guidance to re-diagnose, edit the fix to submit as Edited, or write rejection reasons to Reject..."
)

st.markdown("---")
colA, colB, colC, colD = st.columns(4)

with colA:
    if st.button("🔄 Re-diagnose", use_container_width=True, type="secondary"):
        if not user_input.strip():
            st.error("Please enter guidance in the prompt box first.")
        else:
            with st.spinner("Re-running diagnosis with human guidance..."):
                result = execute_diagnosis(case, human_guidance=user_input)
                save_ai_prediction(case_id, result)
            st.success("Re-diagnosis complete! Results updated.")
            st.rerun()

with colB:
    if st.button("✅ Accept Diagnosis", use_container_width=True, type="primary"):
        review_data = {
            "case_id": case_id,
            "status": "Accepted",
            "revised_fix": "",
            "engineer_note": "Accepted by human engineer.",
            "timestamp": datetime.now().isoformat()
        }
        save_manual_review(review_data)
        st.success("Review submitted! Case Accepted.")
        st.rerun()

with colC:
    if st.button("✍️ Submit as Edited", use_container_width=True):
        if not user_input.strip():
            st.error("Please enter the Revised Fix in the prompt box.")
        else:
            review_data = {
                "case_id": case_id,
                "status": "Edited",
                "revised_fix": user_input.strip(),
                "engineer_note": "Revised fix applied by engineer.",
                "timestamp": datetime.now().isoformat()
            }
            save_manual_review(review_data)
            st.success("Review submitted! Case Edited.")
            st.rerun()

with colD:
    if st.button("❌ Reject Diagnosis", use_container_width=True):
        if not user_input.strip():
            st.error("Please enter the reason for rejection in the prompt box.")
        else:
            review_data = {
                "case_id": case_id,
                "status": "Rejected",
                "revised_fix": "",
                "engineer_note": user_input.strip(),
                "timestamp": datetime.now().isoformat()
            }
            save_manual_review(review_data)
            st.success("Review submitted! Case Rejected.")
            st.rerun()

