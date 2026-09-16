
"""
pages/1_Farmer_Submission.py
--------------------------------
Farmer harvest-submission form and confirmation screen.

Owned by: Prototype Member 1 (Farmer Module and Front-End)

This file only handles FORM UI and rendering. It does not contain any
CSV/JSON/database logic - saving is delegated to data_store.py
(Member 2's responsibility) via save_harvest_record(). This keeps the
two members' work in separate files.
"""

import streamlit as st
from ui_components import (
    inject_global_css, hero_header, section_card_open, section_card_close,
    confirmation_card, workflow_steps,
)
from data_store import save_harvest_record

st.set_page_config(page_title="Farmer Submission - TanamTepat", page_icon="🌱", layout="centered")

inject_global_css()

hero_header(
    "🌱 Harvest Submission",
    "Tell the coordinator about an upcoming harvest so collection can be arranged."
)

# Normal workflow — this page is Step 1, "Farmer Submits".
workflow_steps(
    ["Farmer Submits", "Coordinator Reviews", "Capacity Recorded",
     "System Plans", "People Approve"],
    current_index=0,
)

with st.sidebar:
    st.markdown("### 🧑‍🌾 How it works")
    st.markdown(
        "1. Fill in your farm & crop details\n"
        "2. Give an honest quantity range\n"
        "3. Submit - your entry appears on the coordinator dashboard\n"
        "4. The coordinator reviews your submission. Any suggested collection "
        "change must be agreed by both you and the coordinator."
    )
    st.divider()
    st.caption("Need help? Contact your local TanamTepat coordinator.")

CROP_CATEGORIES = {
    "🥬 Leafy Greens": ["Lettuce", "Spinach", "Kangkung", "Pak Choy", "Mustard Greens (Sawi)"],
    "🍅 Fruit Vegetables": ["Tomato", "Chilli", "Cucumber", "Eggplant (Brinjal)", "Okra (Lady's Finger)"],
    "🥔 Root & Tuber": ["Sweet Potato", "Cassava", "Ginger"],
    "🌿 Herbs": ["Basil (Daun Selasih)", "Mint", "Coriander (Daun Ketumbar)"],
}


# -----------------------------------------
# Section 1: Farm and Crop
# -----------------------------------------

# Crop selection stays OUTSIDE the form so that changing
# the category can instantly update the crop list.

section_card_open("1. Farm and Crop")

farm_name = st.text_input(
    "Farm Name",
    placeholder="e.g. Ladang Hijau Sdn Bhd",
    help="The name of your farm.",
)

crop_category = st.selectbox(
    "Crop Category",
    list(CROP_CATEGORIES.keys())
)

crop_options = CROP_CATEGORIES[crop_category] + ["✏️ Other (not listed)"]

crop_choice = st.selectbox(
    "Crop",
    crop_options
)

if crop_choice == "✏️ Other (not listed)":
    custom_crop = st.text_input(
        "Please specify your crop",
        placeholder="e.g. Dragon Fruit"
    )
    crop = custom_crop.strip() if custom_crop.strip() else "Other (unspecified)"
else:
    crop = crop_choice

section_card_close()


# -----------------------------------------
# Harvest Information
# -----------------------------------------

with st.form("harvest_form", clear_on_submit=True):

    # -------------------------------------
    # Section 2: Harvest Estimate
    # -------------------------------------
    section_card_open("2. Harvest Estimate")

    st.write("**How much do you expect to harvest? (kg)**")

    col1, col2 = st.columns(2)

    with col1:
        min_quantity = st.number_input(
            "Minimum Quantity",
            min_value=0,
            value=100,
            step=50,
            help="The lowest amount you expect.",
        )

    with col2:
        max_quantity = st.number_input(
            "Maximum Quantity",
            min_value=0,
            value=500,
            step=50,
            help="The highest amount you expect.",
        )

    st.caption(
        "ℹ️ TanamTepat uses the maximum quantity for safer capacity planning."
    )

    harvest_date = st.date_input(
        "Ready Date",
        help="The first date the crop can be collected.",
    )

    confidence = st.select_slider(
        "Confidence",
        options=["Low", "Medium", "High"],
        value="Medium",
        help="How certain you are about the quantity estimate.",
    )

    section_card_close()

    # -------------------------------------
    # Section 3: Collection Preferences
    # -------------------------------------
    section_card_open("3. Collection Preferences")

    preferred_slot = st.selectbox(
        "Preferred Slot",
        ["Morning", "Afternoon"],
        help="Your preferred collection time.",
    )

    max_safe_delay_days = st.slider(
        "Maximum Safe Delay (days)",
        min_value=0,
        max_value=3,
        value=1,
        help="How many days collection can safely wait. "
             "0 means it must be collected on the ready date.",
    )

    storage_allowed = st.selectbox(
        "Cold Storage Allowed",
        ["Yes", "No"],
        help="Whether this crop may enter cold storage if collection waits.",
    )

    section_card_close()

    # Plain-language note so the farmer understands what submitting does
    st.caption(
        "ℹ️ Submitting this form does **not** confirm a collection time. "
        "The coordinator must review and approve the final plan."
    )

    submitted = st.form_submit_button("🚀 Submit Harvest")


# -----------------------------------------
# Submission
# -----------------------------------------

if submitted:

    if farm_name.strip() == "":
        st.error("Please enter your farm name.")

    elif crop_choice == "✏️ Other (not listed)" and crop == "Other (unspecified)":
        st.error("Please type in your crop name.")

    elif max_quantity <= 0:
        st.error("Please enter a quantity greater than 0.")

    elif min_quantity > max_quantity:
        st.error("Minimum quantity cannot be greater than maximum quantity.")

    else:
        # Build the RAW submission. data_store.py fills in the ids, the
        # planning quantity, the latest collection date and the priority.
        record = {
            "farm_name": farm_name,
            "crop_type": crop,
            "min_quantity_kg": min_quantity,
            "max_quantity_kg": max_quantity,
            "ready_date": str(harvest_date),
            "max_delay_days": max_safe_delay_days,
            "preferred_slot": preferred_slot,
            "storage_allowed": storage_allowed,
            "confidence": confidence,
        }

        try:
            saved_row = save_harvest_record(record)
        except Exception as e:
            st.error(f"Something went wrong saving your submission: {e}")
            st.stop()

        st.success("✅ Harvest submitted successfully!")
        st.balloons()

        # Simple, friendly summary — no raw field names or storage details.
        confirmation_card(
            "📋 Submission Summary",
            rows=[
                ("Submission ID", saved_row["harvest_id"]),
                ("Crop", saved_row["crop_type"]),
                ("Planning Quantity", f"{saved_row['quantity_kg']} kg"),
                ("Ready Date", saved_row["ready_date"]),
            ],
            status="Pending coordinator review",
        )

        st.info(
            "**What happens next?** The coordinator will review your information. "
            "Submission does not confirm a collection time."
        )

