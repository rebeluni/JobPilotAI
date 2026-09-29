"""
UI Styling and Theme Utilities for JobPilot AI Dashboard.
Provides modern, premium dark-mode CSS and component helpers for Streamlit.
"""

import streamlit as st


def apply_theme():
    """Injects custom CSS for sleek, modern aesthetics."""
    st.markdown(
        """
        <style>
        /* Modern Typography and Layout */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Top Header Styling */
        .main-header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            padding: 24px;
            border-radius: 12px;
            color: white;
            margin-bottom: 24px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        .main-header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            color: #ffffff !important;
        }
        .main-header p {
            margin: 6px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
            color: #e0e7ff;
        }

        /* Metric Cards */
        .metric-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 13px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #38bdf8;
            margin-top: 4px;
        }

        /* Status Badges */
        .badge-strong {
            background-color: #065f46;
            color: #34d399;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-good {
            background-color: #1e3a8a;
            color: #60a5fa;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-stretch {
            background-color: #78350f;
            color: #fbbf24;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-warning {
            background-color: #831843;
            color: #f472b6;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            border-right: 1px solid #334155;
        }

        /* Button Styling */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str):
    """Renders a stylish gradient banner header."""
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
