import streamlit as st
import json
from data.case_manager import get_all_cases, save_ai_prediction, add_case, update_case_metadata, hide_anchor_links
from engine.rule_checker import validate_network_state
from engine.diagnose_runner import execute_diagnosis

st.set_page_config(page_title="Live Diagnosis", page_icon="🩺", layout="wide")
hide_anchor_links()
st.title("🩺 Run Live Diagnosis")

st.subheader("📝 Enter Case Details")
st.markdown("Provide the symptoms and diagnostic command output, and the local rule checker will analyze it first to check for common mistakes before sending to the AI.")

# We use session state to persist form inputs between reruns when buttons are clicked
if "case_title" not in st.session_state:
    st.session_state.case_title = ""
if "case_symptom" not in st.session_state:
    st.session_state.case_symptom = ""
if "case_topology" not in st.session_state:
    st.session_state.case_topology = ""
if "case_show_outputs" not in st.session_state:
    st.session_state.case_show_outputs = ""

title = st.text_input("Case Title", value=st.session_state.case_title, placeholder="e.g. OSPF Neighbors Not Forming on R1-R2 Link")
symptom = st.text_area("Symptom", value=st.session_state.case_symptom, placeholder="e.g. R1 cannot ping R2 loopback interface and OSPF is stuck in INIT state")
topology_note = st.text_area("Topology Note (Optional)", value=st.session_state.case_topology, placeholder="e.g. R1 Fa0/0 is connected to R2 Fa0/0. Both are in OSPF Area 0. R1 IP is 10.1.1.1/30.")
show_outputs = st.text_area("Show Command Output (Optional)", value=st.session_state.case_show_outputs, placeholder="Paste Cisco CLI command outputs here...")

# Save values to session state on change
st.session_state.case_title = title
st.session_state.case_symptom = symptom
st.session_state.case_topology = topology_note
st.session_state.case_show_outputs = show_outputs

# Track heuristic execution state
if "heuristics_run" not in st.session_state:
    st.session_state.heuristics_run = False
if "findings" not in st.session_state:
    st.session_state.findings = []
if "ai_result" not in st.session_state:
    st.session_state.ai_result = None

# Button 1: Run Deterministic Heuristic Check
if st.button("🔍 Analyze Configuration (Run Heuristics)", type="primary"):
    if not title.strip():
        st.error("Please enter a Case Title.")
    elif not symptom.strip():
        st.error("Please enter the Symptom.")
    else:
        with st.spinner("Running local deterministic rules..."):
            findings = validate_network_state(symptom, topology_note, show_outputs)
            heuristic_dicts = [h.__dict__ for h in findings]
            st.session_state.findings = heuristic_dicts
            st.session_state.heuristics_run = True
            st.session_state.ai_result = None  # Reset AI result on new heuristic run
        st.success("Configuration analysis complete!")
        st.rerun()

# Display Heuristic findings if run
if st.session_state.heuristics_run:
    st.divider()
    st.subheader("📋 Heuristic Analysis Findings")
    
    findings = st.session_state.findings
    if findings:
        st.warning(f"⚠️ Local rule checker detected {len(findings)} common configuration issue(s):")
        for h in findings:
            st.markdown(f"**[{h.get('rule_key')}] {h.get('summary')}**")
            st.markdown(f"- **Network Layer:** {h.get('network_layer')} | **Domain:** {h.get('domain')}")
            st.markdown(f"- **Remediation Recommendation:**")
            st.code(h.get('remediation'), language="text")
            st.markdown("---")
    else:
        st.success("✅ No common configuration mistakes detected by local rules.")
        
    st.info("💡 Review the deterministic checks above. If the issue is already resolved by these local rules, you do not need to call the AI. Otherwise, click the button below to run full AI analysis.")
    
    # Button 2: Proceed to AI Diagnosis
    if st.button("🚀 Run AI Diagnosis "):
        custom_case_data = {
            "title": title.strip(),
            "symptom": symptom.strip(),
            "topology_note": topology_note.strip(),
            "show_outputs": show_outputs.strip(),
            "concept_tag": "GENERAL",
            "severity": "Medium",
            "osi_layer": "Unknown",
            "expected_fault": "",
            "suggested_fix": ""
        }
        
        with st.spinner("Saving case and invoking AI..."):
            assigned_case_id = add_case(custom_case_data)
            result = execute_diagnosis(custom_case_data)
            
            # Retrieve the concept tag and OSI layer determined by the AI analysis
            ai_concept = result.get("ai_diagnosis", {}).get("concept_tag", "GENERAL")
            ai_layer = result.get("ai_diagnosis", {}).get("osi_layer", "Unknown")
            
            # Update the case file with details proposed by the AI analysis
            update_case_metadata(assigned_case_id, ai_concept, ai_layer)
            
            custom_case_data["concept_tag"] = ai_concept
            custom_case_data["osi_layer"] = ai_layer
            result["case_id"] = assigned_case_id
            
            save_ai_prediction(assigned_case_id, result)
            
            st.session_state.ai_result = result
            st.session_state.assigned_case_id = assigned_case_id
            
        st.success(f"Case saved with ID **{assigned_case_id}** and live diagnosis complete!")
        st.rerun()

# Display AI results if available
if st.session_state.ai_result:
    result = st.session_state.ai_result
    assigned_case_id = st.session_state.assigned_case_id
    
    st.divider()
    st.info(f"👈 Case successfully saved as **{assigned_case_id}**. Go to the **Review Workbench** in the sidebar to review and Accept/Edit/Reject this diagnosis.")
    
    st.subheader("AI Diagnosis Response")
    st.json(result.get("ai_diagnosis", {}))
    
    st.subheader("Evaluation Scores")
    eval_scores = result.get("evaluation", {})
    colA, colB = st.columns(2)
    with colA:
        st.metric("Evidence Grounding", f"{eval_scores.get('evidence_grounded_pct')}%")
    with colB:
        st.metric("Fault Overlap Score", "N/A (Ad-hoc Case)")
