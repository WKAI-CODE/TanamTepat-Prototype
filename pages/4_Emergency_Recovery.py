"""
pages/4_Emergency_Recovery.py
-----------------------------
Emergency Recovery page (Stage 2B).

Reuses the verified run_emergency_recovery() from emergency_recovery.py on the
coordinator's live Accepted submissions + capacity records (via the adapter).
Nothing about the recovery calculation is changed here.

Advisory simulation only: it does NOT change the approved schedule. Farmer and
coordinator approval is required for any real change.
"""

import pandas as pd
import streamlit as st

from ui_components import (
    inject_global_css, hero_header, info_card, change_card, workflow_steps, esc,
)
from integration_adapter import load_live_scheduling_data
from emergency_recovery import run_emergency_recovery

st.set_page_config(
    page_title="Emergency Recovery - TanamTepat",
    page_icon="🚨",
    layout="wide",
)

inject_global_css()


# Friendly headings for the tables shown on this page.
HEADINGS = {
    "harvest_id":              "Harvest ID",
    "farm_id":                 "Farm ID",
    "crop_type":               "Crop",
    "quantity_kg":             "Planning Quantity (kg)",
    "ready_date":              "Ready Date",
    "latest_collection_date":  "Latest Collection Date",
    "preferred_slot":          "Preferred Slot",
    "recommended_date":        "Recommended Date",
    "recommended_slot":        "Recommended Slot",
    "original_date":           "Original Date",
    "original_slot":           "Original Slot",
    "new_date":                "New Date",
    "new_slot":                "New Slot",
    "recovery_date":           "Recovery Date",
    "recovery_slot":           "Recovery Slot",
    "delay_days":              "Delay (days)",
    "slot_changed":            "Slot Changed",
    "schedule_changed":        "Schedule Changed",
    "recommendation_status":   "Status",
    "status":                  "Status",
    "directly_affected":       "Directly Affected",
    "approval_required":       "Approval Required",
    "human_approval_required": "Approval Needed",
    "recommendation_reason":   "Reason",
    "recovery_explanation":    "Recovery Explanation",
    "change_reason":           "Reason",
    "reason":                  "Reason",
}


def friendly(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with friendly headings and YYYY-MM-DD dates for display."""
    display = df.copy()
    for col in ["ready_date", "latest_collection_date", "recommended_date",
                "original_date", "new_date", "recovery_date"]:
        if col in display.columns:
            display[col] = pd.to_datetime(display[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return display.rename(
        columns={k: v for k, v in HEADINGS.items() if k in display.columns}
    )


def data_fingerprint(harvests: pd.DataFrame, capacities: pd.DataFrame) -> str:
    """
    Deterministic SHA-256 fingerprint of the current scheduling inputs.
    If submissions or capacities change, the fingerprint changes, which lets us
    treat a previously computed recovery result as stale.
    """
    import hashlib

    def stable_csv(df: pd.DataFrame) -> str:
        d = df.copy()
        d = d.reindex(sorted(d.columns), axis=1)
        d = d.sort_values(by=list(d.columns)).reset_index(drop=True)
        return d.to_csv(index=False)

    combined = stable_csv(harvests) + "||" + stable_csv(capacities)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _combine_slot(date_value, slot_value) -> str:
    """Combine a date and a slot into one friendly 'YYYY-MM-DD Slot' string."""
    d = pd.to_datetime(date_value, errors="coerce")
    date_text = d.strftime("%Y-%m-%d") if pd.notna(d) else "Not scheduled"
    slot_text = str(slot_value) if str(slot_value).strip() not in ("", "nan") else ""
    return f"{date_text} {slot_text}".strip()


def _nice_slot(date_value, slot_value) -> str:
    """
    User-facing 'D Mon YYYY Slot' string, e.g. '5 Oct 2026 Morning'.
    Display only — the underlying stored dates are never changed.
    """
    d = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(d):
        return "Not scheduled"
    day = str(int(d.strftime("%d")))  # %-d is not portable on Windows
    date_text = f"{day} {d.strftime('%b %Y')}"
    slot_text = str(slot_value) if str(slot_value).strip() not in ("", "nan") else ""
    return f"{date_text} {slot_text}".strip()


def _nice_date(date_value) -> str:
    """User-facing 'D Mon YYYY' string, e.g. '5 Oct 2026'."""
    d = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(d):
        return str(date_value)
    return f"{int(d.strftime('%d'))} {d.strftime('%b %Y')}"


def build_actions_table(change_report: pd.DataFrame) -> pd.DataFrame:
    """
    Build a friendly, display-only table of rows that need coordinator action:
    where schedule_changed is 'Yes' OR approval_required is 'Yes'. Combines the
    original and recovery date+slot into single readable columns. The change
    report itself is not modified.
    """
    friendly_cols = [
        "Harvest", "Crop", "Original Collection", "Recovery Collection",
        "Status", "Directly Affected", "Approval Required", "Explanation",
    ]
    if change_report is None or change_report.empty:
        return pd.DataFrame(columns=friendly_cols)

    df = change_report.copy()

    # Rows needing action: schedule changed OR approval required (either column
    # may be absent depending on the report shape, so guard for both).
    changed = df["schedule_changed"].astype(str) == "Yes" if "schedule_changed" in df.columns else False
    appr = df["approval_required"].astype(str) == "Yes" if "approval_required" in df.columns else False
    mask = changed | appr
    subset = df[mask] if hasattr(mask, "__len__") else df

    if subset.empty:
        return pd.DataFrame(columns=friendly_cols)

    rows = []
    for _, r in subset.iterrows():
        # Status is derived only for display: a missing recovery date or blank
        # recovery slot means the collection could not be placed.
        rec_date = r.get("recovery_date")
        rec_slot = r.get("recovery_slot")
        date_missing = pd.isna(pd.to_datetime(rec_date, errors="coerce"))
        slot_blank = str(rec_slot).strip() in ("", "nan")
        if date_missing or slot_blank:
            row_status = "🔴 Cannot schedule"
        else:
            row_status = "🟡 Review and approval required"

        rows.append({
            "Harvest":             r.get("harvest_id", ""),
            "Crop":                r.get("crop_type", ""),
            "Original Collection": _combine_slot(r.get("original_date"), r.get("original_slot")),
            "Recovery Collection": _combine_slot(rec_date, rec_slot),
            "Status":              row_status,
            "Directly Affected":   r.get("directly_affected", ""),
            "Approval Required":   r.get("approval_required", ""),
            "Explanation":         r.get("recovery_explanation", ""),
        })
    return pd.DataFrame(rows, columns=friendly_cols)


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
hero_header(
    "🚨 Emergency Recovery",
    "Create a suggested recovery plan when a truck becomes unavailable.",
)


# --------------------------------------------------------------------------
# Load live scheduling data. Show the clear adapter message if not ready.
# --------------------------------------------------------------------------
try:
    farms, harvests, capacities = load_live_scheduling_data()
except ValueError as error:
    st.warning(str(error))
    st.stop()
except Exception as error:
    st.error(f"Could not prepare scheduling data: {error}")
    st.stop()

# Fingerprint of the current inputs — combined with the chosen date/slot so a
# result becomes stale if submissions or capacities change too.
current_fingerprint = data_fingerprint(harvests, capacities)


# --------------------------------------------------------------------------
# Explain what this page does
# --------------------------------------------------------------------------
# Normal workflow shown for context; Emergency Recovery is a SEPARATE optional
# feature, so no normal step is highlighted here.
workflow_steps(
    ["Farmer Submits", "Coordinator Reviews", "Capacity Recorded",
     "System Plans", "People Approve"],
    current_index=-1,
)
st.warning(
    "🟠 Optional Emergency Mode — use when a truck becomes unavailable."
)
st.caption(
    "This is not a normal workflow step. It creates a suggested recovery plan "
    "without changing the approved plan."
)
st.caption(
    "This is a simulation. Farmer and coordinator approval is required for any "
    "real change. No crop-price information is used."
)


# --------------------------------------------------------------------------
# Report the Problem: only offer dates and slots that exist in capacities.csv
# --------------------------------------------------------------------------
st.subheader("Report the Problem")

# Look up each slot's original truck capacity so we can show it in the preview.
cap_lookup = {}
for _, cr in capacities.iterrows():
    key = (pd.to_datetime(cr["date"]).strftime("%Y-%m-%d"), str(cr["time_slot"]))
    cap_lookup[key] = int(cr["truck_capacity_kg"])

with st.container(border=True):
    st.write("Select the date and collection slot where the truck is unavailable.")

    cap_dates = sorted(pd.to_datetime(capacities["date"]).dt.date.unique())
    date_options = [d.strftime("%Y-%m-%d") for d in cap_dates]

    col1, col2 = st.columns(2)
    with col1:
        chosen_date = st.selectbox("Emergency date", date_options)
    with col2:
        # Only show slots that actually exist for the chosen date
        slots_for_date = sorted(
            capacities.loc[
                pd.to_datetime(capacities["date"]).dt.strftime("%Y-%m-%d") == chosen_date,
                "time_slot",
            ].astype(str).unique()
        )
        chosen_slot = st.selectbox("Emergency time slot", slots_for_date)

    # Disruption preview for the current selection.
    original_truck_kg = cap_lookup.get((chosen_date, chosen_slot), 0)
    st.warning(
        f"Selected disruption: {_nice_slot(chosen_date, chosen_slot)}. "
        f"The truck capacity for this simulation will become 0 kg "
        f"(originally {original_truck_kg:,} kg)."
    )


# --------------------------------------------------------------------------
# Run the simulation
# --------------------------------------------------------------------------
if st.button("Create Recovery Plan"):
    try:
        with st.spinner("Recalculating an advisory recovery plan..."):
            (
                original_schedule,
                updated_capacities,
                affected_harvests,
                recovery_schedule,
                change_report,
                recovery_breakdown,
                summary,
            ) = run_emergency_recovery(harvests, capacities, chosen_date, chosen_slot)

        # Store the result together with the exact selection AND the input
        # fingerprint it belongs to. A change to either the selection or the
        # underlying submissions/capacities makes the result stale.
        st.session_state["emergency_results"] = {
            "selection_key":      (chosen_date, chosen_slot, current_fingerprint),
            "chosen_date":        chosen_date,
            "chosen_slot":        chosen_slot,
            "original_truck_kg":  cap_lookup.get((chosen_date, chosen_slot), 0),
            "affected_harvests":  affected_harvests,
            "recovery_schedule":  recovery_schedule,
            "change_report":      change_report,
            "recovery_breakdown": recovery_breakdown,
            "summary":            summary,
        }
    except Exception as error:
        st.error(f"The recovery simulation could not be completed: {error}")


# --------------------------------------------------------------------------
# Show results ONLY if they match the current selection
# --------------------------------------------------------------------------
results = st.session_state.get("emergency_results")

if results is None:
    st.info("Choose a date and slot, then click **Create Recovery Plan**.")
elif results["selection_key"] != (chosen_date, chosen_slot, current_fingerprint):
    # The selection changed OR the underlying submissions/capacities changed
    # since the last run — do not show an old result as if it still applied.
    st.info(
        "The selection or the underlying submissions/capacity records changed. "
        "Click **Create Recovery Plan** again to see the current recovery plan."
    )
else:
    summary            = results["summary"]
    affected_harvests  = results["affected_harvests"]
    recovery_schedule  = results["recovery_schedule"]
    change_report      = results["change_report"]
    res_date           = results["chosen_date"]
    res_slot           = results["chosen_slot"]
    res_original_kg    = results["original_truck_kg"]

    # ======================================================================
    # 1. What happened?
    # ======================================================================
    st.divider()
    st.subheader("1. What happened?")
    info_card(
        f"Disrupted slot: {esc(_nice_slot(res_date, res_slot))}",
        f"Original truck capacity: <b>{res_original_kg:,} kg</b><br>"
        f"Simulated truck capacity: <b>0 kg</b><br>"
        f"Collections directly affected: <b>{int(summary['affected_harvest_count'])}</b>",
        accent="#D9534F",
    )

    # ======================================================================
    # 2. Recommended Recovery Actions
    # ======================================================================
    st.divider()
    st.subheader("2. Recommended Recovery Actions")

    # Show every changed OR unscheduled row as an individual card.
    rep = change_report.copy()
    if "schedule_changed" in rep.columns:
        changed_mask = rep["schedule_changed"].astype(str) == "Yes"
    else:
        changed_mask = pd.Series([False] * len(rep))
    if "approval_required" in rep.columns:
        appr_mask = rep["approval_required"].astype(str) == "Yes"
    else:
        appr_mask = pd.Series([False] * len(rep))
    action_rows = rep[changed_mask | appr_mask]

    if action_rows.empty:
        st.success(
            "🟢 No action required. The recovery plan keeps every collection in "
            "its original slot."
        )
    else:
        for _, r in action_rows.iterrows():
            rec_date = r.get("recovery_date")
            rec_slot = r.get("recovery_slot")
            date_missing = pd.isna(pd.to_datetime(rec_date, errors="coerce"))
            slot_blank = str(rec_slot).strip() in ("", "nan")
            if date_missing or slot_blank:
                status_line = "🔴 Cannot schedule"
                accent = "#D9534F"
            else:
                status_line = "🟡 Review and approval required"
                accent = "#E6A23C"

            heading = f"{esc(r.get('crop_type', ''))} — {esc(r.get('harvest_id', ''))}"
            directly = esc(r.get("directly_affected", ""))
            change_card(
                heading,
                esc(_nice_slot(r.get("original_date"), r.get("original_slot"))),
                esc(_nice_slot(rec_date, rec_slot)),
                f"Directly affected: <b>{directly}</b><br>"
                f"{esc(r.get('recovery_explanation', ''))}",
                status_line,
                accent=accent,
            )

    # Advisory disclaimer, kept visible outside expanders.
    st.info(
        "This is a simulation and does not change the approved collection plan. "
        "Farmer and coordinator approval is required for any real change. "
        "Messages are not sent automatically."
    )

    # ======================================================================
    # 3. What should the coordinator do next?
    # ======================================================================
    st.divider()
    st.subheader("3. What should the coordinator do next?")
    st.markdown(
        """
1. Contact the affected farmers.
2. Discuss every suggested change.
3. Arrange another truck or additional capacity if a collection cannot be placed.
4. Confirm the real arrangement outside this prototype.
        """
    )

    # ======================================================================
    # 4. Recovery Result
    # ======================================================================
    st.divider()
    st.subheader("4. Recovery Result")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Recovery feasible", "Yes" if summary["recovery_is_feasible"] else "No")
    q2.metric("Directly affected", summary["affected_harvest_count"])
    q3.metric("Changed collections", summary["changed_harvest_count"])
    q4.metric("Unscheduled collections", summary["unscheduled_harvest_count"])

    # ---- Full detail, tucked into collapsed expanders ----
    with st.expander("Directly Affected Harvests"):
        if affected_harvests.empty:
            st.info("No harvests were assigned to the disrupted slot.")
        else:
            st.dataframe(friendly(affected_harvests), use_container_width=True)

    with st.expander("Full Recovery Schedule"):
        st.dataframe(friendly(recovery_schedule), use_container_width=True)

    with st.expander("Full Change Report"):
        st.dataframe(friendly(change_report), use_container_width=True)

    with st.expander("Technical Recovery Details"):
        rt1, rt2 = st.columns(2)
        rt1.metric("Recovery score", summary["recovery_score"])
        rt2.metric("Recovery feasible?", "Yes" if summary["recovery_is_feasible"] else "No")
        st.caption(
            "A lower penalty score is better — it is not an accuracy percentage. "
            "A truck breakdown sets the effective capacity for that slot to zero."
        )

    st.caption(
        "Advisory only. This simulation does not change the approved plan. "
        "Crop prices are not used."
    )
