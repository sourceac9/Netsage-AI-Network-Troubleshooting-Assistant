import streamlit as st
import pandas as pd
from data.case_manager import get_all_cases, get_manual_reviews, get_ai_predictions

st.set_page_config(
    page_title="NetSage AI Studio",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    
    .anchor-link, a.anchor-link, h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #a78bfa !important;
    }
    
    /* Cards (Using st.container) */
    div.st-emotion-cache-1r6slb0 {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #2563eb !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
</style>
""", unsafe_allow_html=True)

st.title("NetSage AI Studio 🌐")
st.subheader("📊 System Telemetry & KPIs")

cases = get_all_cases()
reviews = get_manual_reviews()
predictions = get_ai_predictions()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Cases Available", len(cases))
with col2:
    st.metric("Total Diagnoses Run", len(predictions))
with col3:
    st.metric("Human Reviews Completed", len(reviews))
with col4:
    accepted = len([r for r in reviews if r.get("status") == "Accepted"])
    rate = (accepted / len(reviews) * 100) if reviews else 0
    st.metric("AI-Human Agreement Rate", f"{rate:.1f}%")

st.divider()

if cases:
    df_cases = pd.DataFrame(cases)
    
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Cases by Domain (Concept Tag)")
        st.bar_chart(df_cases['concept_tag'].value_counts())
        
    with colB:
        st.subheader("Cases by Severity")
        st.bar_chart(df_cases['severity'].value_counts())
else:
    st.warning("No cases found in dataset.")

st.divider()


