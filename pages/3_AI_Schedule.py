"""
pages/3_AI_Schedule.py
----------------------
AI-Assisted Schedule page (Stage 2B).

Loads the coordinator's Accepted submissions + capacity records through
integration_adapter.load_live_scheduling_data(), then runs the EXISTING,
verified scheduling functions from optimizer.py. Nothing about the algorithm,
its default parameters, or its penalty weights is changed here.

Advisory only: every changed or unscheduled collection needs farmer and
coordinator approval.
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from ui_components import (
    inject_global_css, hero_header, schedule_status_label,
    info_card, change_card, workflow_steps, esc,
)
from integration_adapter import load_live_scheduling_data

# Verified engine functions — used as-is.
from optimizer import (
    detect_capacity_overloads,
    generate_baseline_schedule,
    evaluate_schedule,
    optimize_schedule_ga,
)

st.set_page_config(
    page_title="AI Schedule - TanamTepat",
    page_icon="🤖",
    layout="wide",
)

inject_global_css()


# Friendly headings for schedule tables.
SCHEDULE_HEADINGS = {
    "harvest_id":              "Harvest ID",
    "farm_id":                 "Farm ID",
    "crop_type":               "Crop",
    "quantity_kg":             "Planning Quantity (kg)",
    "ready_date":              "Ready Date",
    "latest_collection_date":  "Latest Collection Date",
    "preferred_slot":          "Preferred Slot",
    "recommended_date":        "Recommended Date",
    "recommended_slot":        "Recommended Slot",
    "delay_days":              "Delay (days)",
    "slot_changed":            "Slot Changed",
    "recommendation_status":   "Status",
    "human_approval_required": "Approval Needed",
    "recommendation_reason":   "Reason",
    # capacity analysis / utilisation headings
    "date":                    "Date",
    "time_slot":               "Time Slot",
    "scheduled_quantity_kg":   "Scheduled (kg)",
    "truck_capacity_kg":       "Truck Capacity (kg)",
    "labour_capacity_kg":      "Labour Capacity (kg)",
    "effective_capacity_kg":   "Effective Capacity (kg)",
    "assigned_quantity_kg":    "Assigned (kg)",
    "remaining_capacity_kg":   "Remaining (kg)",
    "overload_kg":             "Overload (kg)",
    "utilisation_percentage":  "Utilisation (%)",
    "status":                  "Status",
    "explanation":             "Explanation",
}


def friendly(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with friendly headings and YYYY-MM-DD dates for display."""
    display = df.copy()
    for col in ["ready_date", "latest_collection_date", "recommended_date", "date"]:
        if col in display.columns:
            display[col] = pd.to_datetime(display[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return display.rename(
        columns={k: v for k, v in SCHEDULE_HEADINGS.items() if k in display.columns}
    )


def data_fingerprint(harvests: pd.DataFrame, capacities: pd.DataFrame) -> str:
    """
    Build a deterministic SHA-256 fingerprint of the current scheduling inputs.
    If either DataFrame changes (submissions accepted/rejected, capacity edited),
    the fingerprint changes too. This is used to detect stale saved results.
    """
    import hashlib

    # Sort columns and rows so the fingerprint does not depend on ordering,
    # then serialise to a stable CSV string.
    def stable_csv(df: pd.DataFrame) -> str:
        d = df.copy()
        d = d.reindex(sorted(d.columns), axis=1)
        d = d.sort_values(by=list(d.columns)).reset_index(drop=True)
        return d.to_csv(index=False)

    combined = stable_csv(harvests) + "||" + stable_csv(capacities)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def utilisation_from_ga_schedule(ga_schedule: pd.DataFrame, capacities: pd.DataFrame) -> pd.DataFrame:
    """
    Display-only capacity utilisation for the GA RECOMMENDED schedule.

    This recomputes utilisation from ga_schedule using recommended_date and
    recommended_slot, so it reflects where the GA actually placed each harvest
    (not the baseline placement). It does NOT touch optimizer.py or change any
    scheduling logic — it is purely for display.

    Rules:
      - Unscheduled records are excluded.
      - Effective capacity = min(truck_capacity_kg, labour_capacity_kg) when
        truck_available == "Yes", otherwise 0.
    """
    caps = capacities.copy()
    caps["date"] = pd.to_datetime(caps["date"], errors="coerce")

    # Assigned kg per (recommended_date, recommended_slot), excluding Unscheduled
    sched = ga_schedule.copy()
    scheduled = sched[sched["recommendation_status"] != "Unscheduled"].copy()
    scheduled["recommended_date"] = pd.to_datetime(
        scheduled["recommended_date"], errors="coerce"
    )

    assigned_lookup = {}
    for _, row in scheduled.iterrows():
        key = (row["recommended_date"], str(row["recommended_slot"]))
        assigned_lookup[key] = assigned_lookup.get(key, 0) + int(row["quantity_kg"])

    # Build one utilisation row per capacity slot
    util_rows = []
    for _, cap in caps.iterrows():
        if cap["truck_available"] == "Yes":
            effective = int(min(cap["truck_capacity_kg"], cap["labour_capacity_kg"]))
        else:
            effective = 0

        key = (cap["date"], str(cap["time_slot"]))
        assigned = int(assigned_lookup.get(key, 0))
        remaining = effective - assigned
        utilisation = round((assigned / effective) * 100, 1) if effective > 0 else 0.0

        util_rows.append({
            "date":                   cap["date"],
            "time_slot":              cap["time_slot"],
            "effective_capacity_kg":  effective,
            "assigned_quantity_kg":   assigned,
            "remaining_capacity_kg":  remaining,
            "utilisation_percentage": utilisation,
        })

    return pd.DataFrame(util_rows)


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
    # %-d is not portable on Windows; strip a leading zero manually.
    day = str(int(d.strftime("%d")))
    date_text = f"{day} {d.strftime('%b %Y')}"
    slot_text = str(slot_value) if str(slot_value).strip() not in ("", "nan") else ""
    return f"{date_text} {slot_text}".strip()


def build_attention_table(ga_schedule: pd.DataFrame) -> pd.DataFrame:
    """
    Build a friendly, display-only table of the collections that need review:
    only Rescheduled and Unscheduled records. Combines the ready/preferred and
    recommended date+slot into single readable columns. Does not change data.
    """
    attention_statuses = ["Rescheduled", "Unscheduled"]
    subset = ga_schedule[
        ga_schedule["recommendation_status"].isin(attention_statuses)
    ].copy()

    if subset.empty:
        return pd.DataFrame(columns=[
            "Harvest", "Crop", "Quantity", "Original Collection",
            "Recommended Collection", "Status", "Reason", "Approval Needed",
        ])

    rows = []
    for _, r in subset.iterrows():
        rows.append({
            "Harvest":                r["harvest_id"],
            "Crop":                   r["crop_type"],
            "Quantity":               f"{int(r['quantity_kg'])} kg",
            "Original Collection":    _combine_slot(r["ready_date"], r["preferred_slot"]),
            "Recommended Collection": _combine_slot(r["recommended_date"], r["recommended_slot"]),
            "Status":                 schedule_status_label(r["recommendation_status"]),
            "Reason":                 r["recommendation_reason"],
            "Approval Needed":        r["human_approval_required"],
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
hero_header(
    "🤖 AI-Assisted Schedule",
    "Turn accepted harvests and recorded capacity into a suggested collection plan.",
)


# --------------------------------------------------------------------------
# Load live scheduling data. If it is not ready, show the clear adapter
# message instead of crashing, and stop the page cleanly.
# --------------------------------------------------------------------------
try:
    farms, harvests, capacities = load_live_scheduling_data()
except ValueError as error:
    st.warning(str(error))
    st.stop()
except Exception as error:  # unexpected — still avoid a raw crash
    st.error(f"Could not prepare scheduling data: {error}")
    st.stop()

# Fingerprint of the current inputs — used to detect stale saved results.
current_fingerprint = data_fingerprint(harvests, capacities)


# --------------------------------------------------------------------------
# Progress guide + three "what goes in" cards
# --------------------------------------------------------------------------
# Normal workflow. "System Plans" (step 4) is the step happening on this page.
workflow_steps(
    ["Farmer Submits", "Coordinator Reviews", "Capacity Recorded",
     "System Plans", "People Approve"],
    current_index=3,
)
st.caption(
    "Emergency Recovery is an optional feature, used only when a truck becomes "
    "unavailable. It is not a normal workflow step."
)

st.subheader("What goes into the plan")

in_harvests = len(harvests)
in_slots = len(capacities)
freshness_dates = pd.to_datetime(
    harvests["latest_collection_date"], errors="coerce"
).dropna()
if not freshness_dates.empty:
    freshness_text = (
        f"Latest safe collection from "
        f"{_nice_slot(freshness_dates.min(), '')} to "
        f"{_nice_slot(freshness_dates.max(), '')}."
    )
else:
    freshness_text = "Latest safe collection dates come from each submission."

card1, card2, card3 = st.columns(3)
with card1:
    info_card("🌾 Harvests", f"{in_harvests} accepted farmer submission(s).")
with card2:
    info_card("🚚 Capacity", f"{in_slots} truck & labour slot(s) recorded.")
with card3:
    info_card("⏳ Freshness", freshness_text)


# --------------------------------------------------------------------------
# Original capacity analysis (based on preferred slots, before scheduling).
# Kept, but tucked into an expander to keep the main page simple.
# --------------------------------------------------------------------------
with st.expander("Capacity before planning (based on preferred slots)"):
    try:
        capacity_report = detect_capacity_overloads(harvests, capacities)
        st.dataframe(friendly(capacity_report), use_container_width=True)
    except Exception as error:
        st.error(f"Could not run the capacity analysis: {error}")


# --------------------------------------------------------------------------
# Create the collection plan
# --------------------------------------------------------------------------
st.divider()
st.write(
    "TanamTepat will compare accepted harvests with available truck and labour "
    "capacity."
)

if st.button("Create Collection Plan"):
    try:
        with st.spinner("Running the baseline schedule and Genetic Algorithm..."):
            # Original capacity report (based on preferred slots) — used to
            # explain the problem the plan is solving. Verified function, as-is.
            problem_report = detect_capacity_overloads(harvests, capacities)

            # Baseline schedule + its score (verified functions, unchanged).
            # The baseline's own capacity_util is intentionally not stored:
            # utilisation shown below is recomputed from the GA schedule.
            baseline_schedule, _baseline_capacity_util = generate_baseline_schedule(harvests, capacities)
            baseline_score, baseline_breakdown = evaluate_schedule(baseline_schedule, capacities)

            # Genetic Algorithm with its EXISTING default settings (no changes)
            ga_schedule, ga_score, ga_breakdown, ga_history = optimize_schedule_ga(
                harvests, capacities
            )

        # Keep results across reruns, tagged with the fingerprint of the
        # inputs they were generated from (so we can detect stale results).
        st.session_state["ai_schedule_results"] = {
            "fingerprint":      current_fingerprint,
            "problem_report":   problem_report,
            "baseline_score":   baseline_score,
            "ga_schedule":      ga_schedule,
            "ga_score":         ga_score,
            "ga_breakdown":     ga_breakdown,
            "ga_history":       ga_history,
        }
    except Exception as error:
        st.error(f"The schedule could not be generated: {error}")


# --------------------------------------------------------------------------
# Show results if we have them
# --------------------------------------------------------------------------
if "ai_schedule_results" in st.session_state and \
        st.session_state["ai_schedule_results"].get("fingerprint") != current_fingerprint:
    # The submissions or capacities changed since these results were generated.
    # Remove the stale results and ask the user to generate again.
    del st.session_state["ai_schedule_results"]
    st.warning(
        "The submissions or capacity records have changed since the last run. "
        "Please click **Create Collection Plan** again."
    )

if "ai_schedule_results" in st.session_state:
    results        = st.session_state["ai_schedule_results"]
    problem_report = results["problem_report"]
    baseline_score = results["baseline_score"]
    ga_schedule    = results["ga_schedule"]
    ga_score       = results["ga_score"]
    ga_breakdown   = results["ga_breakdown"]
    ga_history     = results["ga_history"]

    status_series     = ga_schedule["recommendation_status"].astype(str)
    changes_count     = int((status_series == "Rescheduled").sum())
    unchanged_count   = int((status_series == "Kept Original").sum())
    unscheduled_count = int((status_series == "Unscheduled").sum())

    # ======================================================================
    # 1. What problem did TanamTepat find?
    # ======================================================================
    st.divider()
    st.subheader("1. What problem did TanamTepat find?")

    # Both "Overloaded" and "Truck Unavailable" are problems the plan must solve.
    problem_statuses = ["Overloaded", "Truck Unavailable"]
    problems = problem_report[problem_report["status"].isin(problem_statuses)]

    if problems.empty:
        st.success(
            "🟢 No capacity problems found. Every harvest fits its preferred "
            "collection slot within the recorded capacity."
        )
    else:
        st.caption(
            "🟡 These preferred slots have a capacity problem. The recommended "
            "solution below moves crops to fix this."
        )
        for _, r in problems.iterrows():
            when = esc(_nice_slot(r["date"], r["time_slot"]))
            status = str(r["status"])
            if status == "Truck Unavailable":
                # No truck means effective capacity is 0 for this slot.
                requested = int(r["scheduled_quantity_kg"])
                info_card(
                    when,
                    f"Problem: <b>No truck available</b> for this slot<br>"
                    f"Requested: <b>{requested:,} kg</b><br>"
                    f"Available: <b>0 kg</b> (no collection possible here)",
                    accent="#D9534F",
                )
            else:  # Overloaded
                requested = int(r["scheduled_quantity_kg"])
                available = int(r["effective_capacity_kg"])
                overload = int(r["overload_kg"])
                info_card(
                    when,
                    f"Problem: <b>Overloaded</b><br>"
                    f"Requested: <b>{requested:,} kg</b><br>"
                    f"Available: <b>{available:,} kg</b><br>"
                    f"Overload: <b>{overload:,} kg</b>",
                    accent="#E6A23C",
                )

    # ======================================================================
    # 2. Recommended Solution
    # ======================================================================
    st.divider()
    st.subheader("2. Recommended Solution")

    changed = ga_schedule[status_series.isin(["Rescheduled", "Unscheduled"])]
    if changed.empty:
        st.success(
            "🟢 All collections fit their original slots. "
            "No schedule changes are required."
        )
    else:
        for _, r in changed.iterrows():
            is_unscheduled = str(r["recommendation_status"]) == "Unscheduled"
            heading = (
                f"{esc(r['crop_type'])} — {esc(r['harvest_id'])} "
                f"· {int(r['quantity_kg'])} kg"
            )
            original_text = esc(_nice_slot(r["ready_date"], r["preferred_slot"]))
            recommended_text = esc(_nice_slot(r["recommended_date"], r["recommended_slot"]))
            if is_unscheduled:
                status_line = "🔴 Cannot schedule — coordinator must add capacity"
                accent = "#D9534F"
            else:
                status_line = "🟡 Farmer and coordinator approval required"
                accent = "#E6A23C"
            change_card(
                heading,
                original_text,
                recommended_text,
                f"Why it changed: {esc(r['recommendation_reason'])}",
                status_line,
                accent=accent,
            )

    # Advisory / approval disclaimer (Step 5 — People Approve), kept visible
    # outside expanders.
    st.info(
        "**Step 5 — People Approve.** These are suggestions only. Every "
        "rescheduled or unscheduled collection now requires farmer and "
        "coordinator approval. Nothing is approved automatically inside this "
        "prototype."
    )

    # ======================================================================
    # 3. Plan Result
    # ======================================================================
    st.divider()
    st.subheader("3. Plan Result")

    feasible = bool(ga_breakdown.get("is_feasible", False))
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Feasible", "Yes" if feasible else "No")
    r2.metric("Changes requiring review", changes_count)
    r3.metric("Unchanged collections", unchanged_count)
    r4.metric("Unscheduled collections", unscheduled_count)
    st.caption(
        "**Feasible** — Yes means every accepted harvest has a collection slot "
        "within its freshness limit and available capacity."
    )

    # ======================================================================
    # 4. What should the coordinator do next?
    # ======================================================================
    st.divider()
    st.subheader("4. What should the coordinator do next?")
    st.markdown(
        """
1. Review suggested changes.
2. Discuss them with affected farmers.
3. Confirm collection arrangements outside this prototype.
        """
    )

    # ---- Full detail, tucked into collapsed expanders ----
    with st.expander("Full Schedule"):
        st.dataframe(friendly(ga_schedule), use_container_width=True)

    with st.expander("Capacity Details"):
        st.caption(
            "Utilisation recomputed from where the plan actually places each "
            "harvest (recommended date and slot). Unscheduled harvests are excluded."
        )
        ga_utilisation = utilisation_from_ga_schedule(ga_schedule, capacities)
        st.dataframe(friendly(ga_utilisation), use_container_width=True)

    with st.expander("Technical Details"):
        t1, t2, t3 = st.columns(3)
        t1.metric("Baseline score", baseline_score)
        t2.metric("Genetic Algorithm score", ga_score)
        t3.metric("Feasible?", "Yes" if feasible else "No")

        if ga_score == baseline_score:
            st.info(
                "The Genetic Algorithm matched the baseline score. For this "
                "dataset the baseline plan was already optimal or equally good."
            )
        elif ga_score < baseline_score:
            st.success(
                f"The Genetic Algorithm improved the baseline by "
                f"{baseline_score - ga_score} point(s)."
            )
        else:
            st.warning("The Genetic Algorithm did not improve on the baseline this run.")

        st.caption(
            "A **lower** penalty score is better — it is **not** an accuracy "
            "percentage. It simply adds up the cost of delays, slot changes and "
            "any unscheduled harvests."
        )

        history_fig = px.line(
            ga_history,
            x="generation",
            y="best_score",
            markers=True,
            labels={"generation": "Generation", "best_score": "Best penalty score"},
        )
        st.plotly_chart(history_fig, use_container_width=True)

    st.caption(
        "Notes: Cold storage is recorded but not automatically allocated in this "
        "prototype. Crop prices are not used anywhere in the scheduling."
    )
else:
    st.info("Click **Create Collection Plan** above to generate a plan.")
