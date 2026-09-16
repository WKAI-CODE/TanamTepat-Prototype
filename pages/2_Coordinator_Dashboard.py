"""
pages/2_Coordinator_Dashboard.py
--------------------------------
Coordinator Dashboard for TanamTepat.

Owned by: Prototype Member 2 (Coordinator Dashboard, Data and API)

This dashboard reads farmer submissions ONLY through load_harvest_data()
and writes decisions/capacity ONLY through data_store.py helpers, so it
always uses the shared schemas.

Stage 2C reorganises this page into three tabs (Review Submissions,
Record Capacity, Capacity Check) for clarity. All data logic and the
verified validation/save behaviour are unchanged. No scheduling runs here.
"""

import pandas as pd
import streamlit as st

from ui_components import (
    inject_global_css, hero_header, status_label, workflow_steps, info_card, esc,
)
from data_store import (
    load_harvest_data,
    update_confirmation_status,
    load_capacities,
    save_capacity_slot,
)

st.set_page_config(
    page_title="Coordinator Dashboard - TanamTepat",
    page_icon="📊",
    layout="wide",
)

inject_global_css()

# Friendly headings so the coordinator sees plain words, not raw column names.
FRIENDLY_HEADINGS = {
    "harvest_id":             "Harvest ID",
    "farm_id":                "Farm ID",
    "farm_name":              "Farm Name",
    "crop_type":              "Crop",
    "min_quantity_kg":        "Min Quantity (kg)",
    "max_quantity_kg":        "Max Quantity (kg)",
    "quantity_kg":            "Planning Quantity (kg)",
    "ready_date":             "Ready Date",
    "latest_collection_date": "Latest Collection Date",
    "preferred_slot":         "Preferred Slot",
    "storage_allowed":        "Cold Storage Allowed",
    "priority":               "Freshness Priority",
    "confidence":             "Confidence",
    "confirmation_status":    "Status",
}


def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with friendly column headings (only for columns present)."""
    return df.rename(
        columns={k: v for k, v in FRIENDLY_HEADINGS.items() if k in df.columns}
    )


# --------------------------------------------------------------------------
# Header + one-sentence explanation
# --------------------------------------------------------------------------
hero_header(
    "📊 Coordinator Dashboard",
    "Review farmer submissions, record collection capacity, and check the "
    "data is ready before creating a plan.",
)

# Flash message: stored in session_state before an st.rerun() so it still
# appears once the page has refreshed with the updated data.
if "flash_message" in st.session_state:
    st.success(st.session_state.pop("flash_message"))

# Top-of-page explanation + shared workflow guide.
st.write("You are managing the information needed to create a collection plan.")
workflow_steps(
    ["Farmer Submits", "Coordinator Reviews", "Capacity Recorded",
     "System Plans", "People Approve"],
    current_index=[1, 2],
)
st.caption(
    "This dashboard covers Coordinator Reviews and Capacity Recorded (steps 2–3). "
    "The collection plan itself is created on the AI Schedule page (step 4). "
    "Emergency Recovery is a separate optional feature, used only when a truck "
    "becomes unavailable."
)

# Load the shared data once for all tabs.
harvest_df = load_harvest_data()
capacities_df = load_capacities()

tab_review, tab_capacity, tab_check = st.tabs(
    ["1. Review Submissions", "2. Record Capacity", "3. Capacity Check"]
)


# ==========================================================================
# TAB 1 — REVIEW SUBMISSIONS
# ==========================================================================
with tab_review:
    st.subheader("Step 1 — Review farmer information")
    st.caption(
        "Accepted means the submission may enter scheduling. It does not "
        "confirm a collection time."
    )

    if harvest_df.empty:
        st.info("No farmer harvest submissions yet.")
    else:
        # Quick counts
        total_submissions = len(harvest_df)
        pending_submissions = int(
            (harvest_df["confirmation_status"].astype(str) == "Pending").sum()
        )
        total_planned_qty = int(
            pd.to_numeric(harvest_df["quantity_kg"], errors="coerce").fillna(0).sum()
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Total submissions", total_submissions)
        c2.metric("Pending submissions", pending_submissions)
        c3.metric("Total planned quantity (kg)", f"{total_planned_qty:,}")

        # Show Pending submissions first in the selection list.
        pending_ids = harvest_df.loc[
            harvest_df["confirmation_status"].astype(str) == "Pending", "harvest_id"
        ].astype(str).tolist()
        other_ids = harvest_df.loc[
            harvest_df["confirmation_status"].astype(str) != "Pending", "harvest_id"
        ].astype(str).tolist()
        ordered_ids = pending_ids + other_ids

        st.markdown("**Pending submissions need your decision** (listed first below)")
        selected_id = st.selectbox("Select a submission to review", ordered_ids)

        selected_row = harvest_df[
            harvest_df["harvest_id"].astype(str) == selected_id
        ].iloc[0]

        # A clear coloured status label so the current decision is obvious.
        current_status = str(selected_row["confirmation_status"])
        status_icon = {"Accepted": "🟢", "Rejected": "🔴", "Pending": "🟡"}.get(
            current_status, "🔵"
        )

        # Bordered summary card for the selected submission. All dynamic,
        # user/CSV-provided values are HTML-escaped before insertion.
        info_card(
            f"{esc(selected_row['crop_type'])} — {esc(selected_row['harvest_id'])} "
            f"({esc(selected_row['farm_name'])})",
            f"Planning quantity: <b>{esc(selected_row['quantity_kg'])} kg</b><br>"
            f"Ready date: <b>{esc(selected_row['ready_date'])}</b> · "
            f"Preferred slot: <b>{esc(selected_row['preferred_slot'])}</b><br>"
            f"Latest collection: <b>{esc(selected_row['latest_collection_date'])}</b><br>"
            f"Current status: <b>{status_icon} {esc(current_status)}</b>",
        )

        # Default the radio to the submission's current decision. Pending
        # defaults to Accepted. A widget key tied to selected_id keeps each
        # harvest's choice separate when the selection changes.
        decision_options = ["Accepted", "Rejected"]
        default_index = 1 if current_status == "Rejected" else 0

        new_status = st.radio(
            "Set decision",
            decision_options,
            index=default_index,
            horizontal=True,
            key=f"decision_{selected_id}",
        )

        if st.button("Save Decision"):
            try:
                updated = update_confirmation_status(selected_id, new_status)
                st.session_state["flash_message"] = (
                    f"Submission {updated['harvest_id']} is now "
                    f"'{updated['confirmation_status']}'. "
                    f"Next: Record collection capacity (tab 2)."
                )
                st.rerun()
            except ValueError as error:
                st.error(f"Could not update the submission: {error}")

        st.caption("Next: Record collection capacity.")

        # Full table hidden inside an expander to keep the tab tidy.
        with st.expander("View all submissions"):
            st.dataframe(rename_for_display(harvest_df), use_container_width=True)


# ==========================================================================
# TAB 2 — RECORD CAPACITY
# ==========================================================================
with tab_capacity:
    st.subheader("Step 2 — Tell TanamTepat what resources are available")
    st.caption(
        "Record how much can be collected on each date and time slot. "
        "This is saved for the plan; it does not create a plan by itself."
    )

    st.markdown(
        """
- **Truck capacity** — how many kilograms the trucks can carry in this slot.
- **Labour capacity** — how many kilograms the workers can handle in this slot.
- **Cold-storage capacity** — cold-storage space recorded for the future (not allocated automatically yet).
        """
    )

    with st.form("capacity_form"):
        cap_col1, cap_col2 = st.columns(2)
        with cap_col1:
            cap_date = st.date_input("Date")
        with cap_col2:
            cap_slot = st.selectbox("Time Slot", ["Morning", "Afternoon"])

        # Three capacity inputs arranged in clear columns.
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            truck_capacity_kg = st.number_input(
                "Total Truck Capacity (kg)", min_value=0, value=0, step=100
            )
        with res_col2:
            labour_capacity_kg = st.number_input(
                "Labour Handling Capacity (kg)", min_value=0, value=0, step=100
            )
        with res_col3:
            cold_storage_capacity_kg = st.number_input(
                "Cold-Storage Capacity (kg)", min_value=0, value=0, step=100
            )

        truck_available = st.selectbox("Truck Available", ["Yes", "No"])

        # Display-only explanation of what this slot can handle.
        if truck_available == "No":
            st.warning(status_label("cannot", "No collection can use this slot."))
        else:
            effective_kg = min(int(truck_capacity_kg), int(labour_capacity_kg))
            st.info(f"🔵 This slot can handle up to {effective_kg:,} kg.")

        save_capacity_button = st.form_submit_button("Save Capacity Slot")

    if save_capacity_button:
        capacity_record = {
            "date": str(cap_date),
            "time_slot": cap_slot,
            "truck_capacity_kg": int(truck_capacity_kg),
            "cold_storage_capacity_kg": int(cold_storage_capacity_kg),
            "labour_capacity_kg": int(labour_capacity_kg),
            "truck_available": truck_available,
        }
        try:
            saved = save_capacity_slot(capacity_record)
            st.session_state["flash_message"] = (
                f"Capacity saved for {saved['date']} {saved['time_slot']} "
                f"(truck {saved['truck_capacity_kg']} kg, labour "
                f"{saved['labour_capacity_kg']} kg). Next: Open Capacity Check (tab 3)."
            )
            st.rerun()
        except ValueError as error:
            st.error(f"Could not save the capacity slot: {error}")

    st.caption(
        "Cold-storage capacity is recorded for future expansion. The current "
        "scheduling engine does not automatically allocate crops to cold storage."
    )
    st.caption("Next: Open Capacity Check.")

    with st.expander("View saved capacity records"):
        if capacities_df.empty:
            st.info("No capacity records saved yet.")
        else:
            st.dataframe(capacities_df, use_container_width=True)


# ==========================================================================
# TAB 3 — CAPACITY CHECK
# ==========================================================================
with tab_check:
    st.subheader("Step 3 — Check whether all required information exists")
    st.caption(
        "This checklist only confirms that the needed records exist. It does "
        "not check whether the capacity is large enough — the plan does that."
    )

    accepted_df = (
        harvest_df[harvest_df["confirmation_status"].astype(str) == "Accepted"]
        if not harvest_df.empty
        else pd.DataFrame(columns=harvest_df.columns)
    )

    # --- Readiness checklist (three items, each icon + text) ---
    has_accepted = not accepted_df.empty
    has_capacity = not capacities_df.empty

    # Item 3: does every accepted harvest have a matching ready-date + slot record?
    missing_actions = []
    all_slots_matched = False
    if has_accepted and has_capacity:
        cap_dates = pd.to_datetime(capacities_df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        capacity_keys = set(zip(cap_dates, capacities_df["time_slot"].astype(str)))
        capacity_date_set = set(cap_dates)

        for _, row in accepted_df.iterrows():
            ready = pd.to_datetime(row["ready_date"], errors="coerce")
            ready_text = ready.strftime("%Y-%m-%d") if pd.notna(ready) else str(row["ready_date"])
            nice_date = ready.strftime("%d %b %Y") if pd.notna(ready) else str(row["ready_date"])
            slot = str(row["preferred_slot"])
            if (ready_text, slot) not in capacity_keys:
                missing_actions.append(f"Add capacity for {nice_date}, {slot}, before creating the plan.")
        all_slots_matched = (len(missing_actions) == 0)

    st.markdown("**Readiness checklist**")
    st.write(("✅" if has_accepted else "⬜") + " Accepted submissions exist")
    st.write(("✅" if has_capacity else "⬜") + " Capacity records exist")
    st.write(
        ("✅" if all_slots_matched else "⬜")
        + " Every accepted harvest has a matching ready-date capacity slot"
    )

    # --- Guidance / next action ---
    if not has_accepted:
        st.info(status_label("info", "There are no accepted submissions to check yet."))
    elif not has_capacity:
        st.warning(
            status_label("cannot", "No capacity records exist yet. Record capacity in tab 2 first.")
        )
    elif missing_actions:
        st.warning(status_label("review", "Some capacity slots still need to be recorded:"))
        for message in sorted(set(missing_actions)):
            st.write(f"- {message}")
    else:
        st.info(
            status_label(
                "info",
                "Required capacity records exist. You can now create a "
                "collection plan to check whether the available capacity is "
                "sufficient.",
            )
        )
        st.page_link(
            "pages/3_AI_Schedule.py",
            label="Continue to Create Collection Plan",
            use_container_width=True,
        )

    st.caption(
        "This is a records check only. No collection schedule is generated on "
        "this page — use the AI Schedule page for that."
    )
