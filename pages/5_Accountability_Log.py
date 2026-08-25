import streamlit as st
import pandas as pd
from data.case_manager import get_accountability_logs, hide_anchor_links

st.set_page_config(page_title="Accountability Log", page_icon="📜", layout="wide")
hide_anchor_links()
st.title("📜 Accountability Log")

st.markdown("""
This log is automatically created for every **Edits** or **Rejects** diagnosis.
""")

logs = get_accountability_logs()

if not logs:
    st.success("No AI corrections logged yet. The AI is performing flawlessly (or no reviews have been completed).")
else:
    df = pd.DataFrame(logs)
    st.dataframe(df, width="stretch")
    
    st.subheader("Deep Dive")
    for log in logs:
        with st.expander(f"Case: {log.get('case_id')} ({log.get('timestamp')})"):
            st.markdown(f"**AI Suggested:**\n{log.get('ai_said')}")
            st.markdown(f"**Correct Answer:**\n{log.get('correct_answer')}")
            st.warning(f"**Engineer Note (Why it was wrong):**\n{log.get('why_ai_was_wrong')}")
