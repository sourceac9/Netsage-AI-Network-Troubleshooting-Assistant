import streamlit as st
import pandas as pd
from data.case_manager import get_all_cases, hide_anchor_links

st.set_page_config(page_title="Case Explorer", page_icon="📂", layout="wide")
hide_anchor_links()
st.title("📂 Network Diagnostic Cases")

cases = get_all_cases()
if not cases:
    st.error("No cases found in storage/cases.csv")
else:
    df = pd.DataFrame(cases)
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        domain_filter = st.multiselect("Filter by Concept Tag", options=df['concept_tag'].unique())
    with col2:
        severity_filter = st.multiselect("Filter by Severity", options=df['severity'].unique())
        
    filtered_df = df
    if domain_filter:
        filtered_df = filtered_df[filtered_df['concept_tag'].isin(domain_filter)]
    if severity_filter:
        filtered_df = filtered_df[filtered_df['severity'].isin(severity_filter)]
        
    st.dataframe(filtered_df, width="stretch")
