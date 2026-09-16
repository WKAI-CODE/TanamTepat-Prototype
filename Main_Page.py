"""
Main_Page.py
------------
Main entry point / landing page for TanamTepat.

Owned by: Prototype Member 1 (Farmer Module and Front-End)
Responsibility covered here: main page layout and navigation.

This file is intentionally light on LOGIC - it sets shared page config
and lays out the landing page using components from ui_components.py.
Actual screens live under pages/, and Streamlit's built-in multipage
navigation (the "pages/" folder) handles routing between them.

    pages/1_Farmer_Submission.py       -> Farmer harvest submission
    pages/2_Coordinator_Dashboard.py   -> Coordinator review & capacity
    pages/3_AI_Schedule.py             -> AI-assisted schedule
    pages/4_Emergency_Recovery.py      -> Emergency recovery simulation
    pages/5_About_and_Safeguards.py    -> About & safeguards

Run with: streamlit run Main_Page.py
"""

import streamlit as st
import pandas as pd
from ui_components import (
    inject_global_css, hero_header, stat_pill, workflow_steps, role_card_header,
)
from data_store import load_harvest_data

st.set_page_config(
    page_title="TanamTepat",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="expanded"
)

inject_global_css()

hero_header(
    "🌱 TanamTepat",
    "Plan farm harvest collection together — farmers share what is coming, "
    "the coordinator arranges the trucks."
)

# =============================================================
# What would you like to do?  (large, obvious role cards)
# =============================================================
st.markdown("### What would you like to do?")

role_farmer, role_coord = st.columns(2)

with role_farmer:
    role_card_header(
        "🧑‍🌾",
        "I am a Farmer",
        "Submit information about an upcoming harvest.",
        kind="farmer",
    )
    st.page_link(
        "pages/1_Farmer_Submission.py",
        label="Continue as Farmer →",
        use_container_width=True,
    )

with role_coord:
    role_card_header(
        "📋",
        "I am a Coordinator",
        "Review harvests, record capacity and create a collection plan.",
        kind="coord",
    )
    st.page_link(
        "pages/2_Coordinator_Dashboard.py",
        label="Continue as Coordinator →",
        use_container_width=True,
    )

# Secondary link, kept smaller below the two role cards.
st.caption("Learn more about how TanamTepat is meant to be used:")
st.page_link(
    "pages/5_About_and_Safeguards.py",
    label="🛡️ About & Safeguards",
)

st.write("")

# =============================================================
# Normal workflow (five steps). Emergency Recovery is separate.
# No step is highlighted because the user has not started yet.
# =============================================================
st.markdown("### How it works")
workflow_steps(
    ["Farmer Submits", "Coordinator Reviews", "Capacity Recorded",
     "System Plans", "People Approve"],
    current_index=-1,
)
st.info("Choose your role above to begin.")
st.caption(
    "TanamTepat recommends collection plans. Farmers and coordinators make the "
    "final decision. Emergency Recovery is an optional feature, used only when "
    "a truck becomes unavailable — it is not part of the normal workflow above."
)

st.write("")

# =============================================================
# Live snapshot (placed BELOW the workflow, as a quick status)
# =============================================================
st.markdown("### Current snapshot")

try:
    df = load_harvest_data()
except Exception:
    df = pd.DataFrame()

if len(df) > 0:
    # Uses the shared snake_case columns written by data_store.py.
    pending_df = df[df["confirmation_status"] == "Pending"]

    upcoming_cutoff = pd.Timestamp.now().normalize() + pd.Timedelta(days=7)
    ready_dates = pd.to_datetime(df["ready_date"], errors="coerce")
    upcoming_df = df[
        (ready_dates >= pd.Timestamp.now().normalize()) &
        (ready_dates <= upcoming_cutoff)
    ]

    pending_count = len(pending_df)
    upcoming_count = len(upcoming_df)

    # quantity_kg is the conservative (maximum) planning quantity.
    pending_est_kg = int(
        pd.to_numeric(pending_df["quantity_kg"], errors="coerce").fillna(0).sum()
    )

    s1, s2, s3 = st.columns(3)
    with s1:
        stat_pill(str(pending_count), "Awaiting coordinator review")
    with s2:
        stat_pill(str(upcoming_count), "Harvests ready in next 7 days")
    with s3:
        stat_pill(f"{pending_est_kg:,} kg", "Volume pending collection")
    st.caption("Live snapshot - updates as farmers submit or the coordinator confirms.")
else:
    st.info("No harvest submissions yet - a farmer can add the first one.")

st.divider()
st.caption(
    "TanamTepat - built by Team TerraMind. This is a working prototype. "
    "Figures shown reflect prototype data only, not production metrics."
)

with st.sidebar:
    st.markdown("### 🧑‍🌾 About TanamTepat")
    st.caption(
        "Built by Team TerraMind. The coordinator approves every "
        "final decision - this engine assists, it doesn't decide alone."
    )
