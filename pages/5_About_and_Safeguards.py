"""
pages/5_About_and_Safeguards.py
-------------------------------
About & Safeguards page (Stage 2B).

A plain-language summary of what TanamTepat is and the limits it operates
under. This page has no data logic — it only explains the safeguards.
"""

import streamlit as st

from ui_components import inject_global_css, hero_header

st.set_page_config(
    page_title="About & Safeguards - TanamTepat",
    page_icon="🛡️",
    layout="wide",
)

inject_global_css()

hero_header(
    "🛡️ About & Safeguards",
    "What TanamTepat does, what it does not do, and who decides.",
)

# --------------------------------------------------------------------------
# What TanamTepat Does
# --------------------------------------------------------------------------
st.subheader("What TanamTepat Does")
st.markdown(
    """
- Helps a cooperative coordinator prepare **advisory** harvest collection plans.
- Compares accepted harvests with recorded truck and labour capacity.
- Suggests a collection plan and highlights any changes for review.
- Records cold-storage capacity for future planning.
- Uses **freshness urgency** to decide how soon a crop should be collected.
    """
)

# --------------------------------------------------------------------------
# What TanamTepat Does Not Do
# --------------------------------------------------------------------------
st.subheader("What TanamTepat Does Not Do")
st.markdown(
    """
- It does **not** approve any schedule automatically — every change needs approval.
- It does **not** use crop prices, and does no price targeting.
- It does **not** coordinate or steer market supply.
- It does **not** send real-time notifications or live alerts (a future feature).
- It does **not** automatically allocate crops to cold storage (a future feature).
    """
)

st.info(
    "This prototype uses local files and does not yet include user login or "
    "access control. A production version must keep each cooperative's data "
    "separate and private."
)

# --------------------------------------------------------------------------
# Who Makes the Final Decision
# --------------------------------------------------------------------------
st.subheader("Who Makes the Final Decision")
st.info(
    "The **farmer and the coordinator** make every final decision. "
    "Human approval is required for any change. TanamTepat assists; it does "
    "not decide alone."
)

# --------------------------------------------------------------------------
# Current Prototype Limitations
# --------------------------------------------------------------------------
st.subheader("Current Prototype Limitations")
st.markdown(
    """
- This is an **advisory** planning tool only, not a booking or dispatch system.
- **Priority represents freshness urgency only** — not crop price or a farmer's importance.
- **Cold-storage allocation is not implemented** — capacity is only recorded.
- **Real-time notifications are not implemented.**
- **Results depend on the submitted information** — accuracy reflects what
  farmers and the coordinator enter.
    """
)
