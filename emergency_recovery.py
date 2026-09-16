# emergency_recovery.py
# TanamTepat - AI-Assisted Harvest Logistics Planning
#
# Emergency Recovery Mode
# -----------------------
# When a scheduled truck suddenly becomes unavailable, this module produces an
# ADVISORY recovery schedule and clearly shows which harvests are affected.
#
# This is a decision-support feature only. It does NOT move any farmer
# automatically. Every change must be confirmed by the farmer and the
# collection coordinator before it happens.
#
# What this module does:
#   - Marks a single collection slot as having no truck available
#   - Identifies the harvests that were assigned to that slot
#   - Re-runs the scheduling optimiser on the reduced capacity
#   - Produces a plain-language report comparing the original and recovery plans
#
# What this module does NOT do:
#   - It does not use market prices or try to control supply
#   - It does not split harvest quantities across slots
#   - It does not allocate cold storage
#   - It does not modify the original CSV files

import pandas as pd

# Reuse the existing, tested functions from optimizer.py
from optimizer import load_data, validate_data, optimize_schedule_ga


# --------------------------------------------------------------------------
# apply_truck_breakdown(capacities, emergency_date, emergency_slot)
# Marks one collection slot as having no truck available.
# Works on a copy so the original capacities DataFrame is never changed.
# Returns the updated capacities DataFrame.
# --------------------------------------------------------------------------
def apply_truck_breakdown(capacities, emergency_date, emergency_slot):

    # Work on a copy so the caller's DataFrame is left untouched
    caps = capacities.copy()

    # Make sure the date column and the emergency date are proper datetimes
    caps["date"]   = pd.to_datetime(caps["date"])
    emergency_date = pd.to_datetime(emergency_date)

    # Locate the exact slot the coordinator selected
    slot_mask = (caps["date"] == emergency_date) & (caps["time_slot"] == emergency_slot)

    # If that date + slot does not exist, tell the user clearly
    if not slot_mask.any():
        date_str = emergency_date.strftime("%Y-%m-%d")
        raise ValueError(
            f"No capacity slot exists for {date_str} {emergency_slot}. "
            f"Emergency recovery cannot be applied to a slot that is not in capacities.csv."
        )

    # Set truck_available to "No" for ONLY the selected slot
    caps.loc[slot_mask, "truck_available"] = "No"

    return caps


# --------------------------------------------------------------------------
# identify_affected_harvests(original_schedule, emergency_date, emergency_slot)
# Finds the harvests that were assigned to the disrupted date and time slot.
# Returns a DataFrame with a fixed set of columns (empty if none are affected).
# --------------------------------------------------------------------------
def identify_affected_harvests(original_schedule, emergency_date, emergency_slot):

    # The columns we always return, even when nothing is affected
    output_columns = [
        "harvest_id", "farm_id", "crop_type", "quantity_kg",
        "priority", "recommended_date", "recommended_slot",
    ]

    sched = original_schedule.copy()

    # Normalise the recommended_date column and the emergency date for comparison
    sched["recommended_date"] = pd.to_datetime(sched["recommended_date"], errors="coerce")
    emergency_date            = pd.to_datetime(emergency_date)

    # Keep only the rows that were scheduled into the disrupted slot
    affected = sched[
        (sched["recommended_date"] == emergency_date)
        & (sched["recommended_slot"] == emergency_slot)
    ]

    # If nobody is affected, return an empty frame with the correct columns
    if affected.empty:
        return pd.DataFrame(columns=output_columns)

    return affected[output_columns].reset_index(drop=True)


# --------------------------------------------------------------------------
# build_recovery_change_report(original_schedule, recovery_schedule,
#                              affected_harvest_ids)
# Compares the original and recovery schedules harvest by harvest and explains,
# in plain language, what changed and whether approval is needed.
# --------------------------------------------------------------------------
def build_recovery_change_report(original_schedule, recovery_schedule, affected_harvest_ids):

    orig = original_schedule.copy()
    rec  = recovery_schedule.copy()

    # Make date columns comparable
    orig["recommended_date"] = pd.to_datetime(orig["recommended_date"], errors="coerce")
    rec["recommended_date"]  = pd.to_datetime(rec["recommended_date"],  errors="coerce")

    # Build quick lookups keyed by harvest_id so we can match the two schedules
    orig_by_id = {row["harvest_id"]: row for _, row in orig.iterrows()}
    rec_by_id  = {row["harvest_id"]: row for _, row in rec.iterrows()}

    affected_set = set(affected_harvest_ids)

    report_rows = []

    # Walk through every harvest in the original schedule
    for harvest_id, o_row in orig_by_id.items():
        r_row = rec_by_id.get(harvest_id)

        # Original assignment values
        original_date = o_row["recommended_date"]
        original_slot = o_row["recommended_slot"]

        # Recovery assignment values (a harvest should always appear in both,
        # but guard against a missing row just in case)
        if r_row is not None:
            recovery_date       = r_row["recommended_date"]
            recovery_slot       = r_row["recommended_slot"]
            recovery_status     = r_row["recommendation_status"]
        else:
            recovery_date   = pd.NaT
            recovery_slot   = ""
            recovery_status = "Unscheduled"

        # Was this harvest sitting inside the disrupted slot?
        directly_affected = "Yes" if harvest_id in affected_set else "No"

        # Did the recovery plan move this harvest to a different date or slot?
        is_unscheduled = (recovery_status == "Unscheduled")
        date_changed   = (original_date != recovery_date)
        slot_changed   = (original_slot != recovery_slot)
        schedule_changed = "Yes" if (is_unscheduled or date_changed or slot_changed) else "No"

        # Approval is needed whenever the plan changed or the harvest is unscheduled
        approval_required = "Yes" if (schedule_changed == "Yes" or is_unscheduled) else "No"

        # Write a simple explanation
        if is_unscheduled:
            recovery_explanation = (
                "This harvest could not be placed in the recovery plan. "
                "The coordinator must arrange another truck, add capacity, "
                "or find another safe option. This is a suggestion only."
            )
        elif schedule_changed == "Yes":
            o_date_str = original_date.strftime("%Y-%m-%d") if pd.notna(original_date) else "unscheduled"
            r_date_str = recovery_date.strftime("%Y-%m-%d") if pd.notna(recovery_date) else "unscheduled"
            if directly_affected == "Yes":
                recovery_explanation = (
                    f"Originally planned for {o_date_str} {original_slot}, which lost its truck. "
                    f"Suggested new slot: {r_date_str} {recovery_slot}. "
                    f"Farmer and coordinator approval required."
                )
            else:
                recovery_explanation = (
                    f"Suggested move from {o_date_str} {original_slot} to "
                    f"{r_date_str} {recovery_slot} to keep the recovery plan feasible. "
                    f"Farmer and coordinator approval required."
                )
        else:
            recovery_explanation = "No change. The original collection slot still applies."

        report_rows.append({
            "harvest_id":           harvest_id,
            "crop_type":            o_row["crop_type"],
            "quantity_kg":          o_row["quantity_kg"],
            "priority":             o_row["priority"],
            "original_date":        original_date,
            "original_slot":        original_slot,
            "recovery_date":        recovery_date,
            "recovery_slot":        recovery_slot,
            "directly_affected":    directly_affected,
            "schedule_changed":     schedule_changed,
            "approval_required":    approval_required,
            "recovery_explanation": recovery_explanation,
        })

    change_report = pd.DataFrame(report_rows)

    # Sort so directly affected harvests appear first, then by harvest_id
    if not change_report.empty:
        change_report["_affected_rank"] = change_report["directly_affected"].map(
            {"Yes": 0, "No": 1}
        )
        change_report = change_report.sort_values(
            by=["_affected_rank", "harvest_id"]
        ).drop(columns=["_affected_rank"]).reset_index(drop=True)

    return change_report


# --------------------------------------------------------------------------
# run_emergency_recovery(harvests, capacities, emergency_date, emergency_slot)
# Runs the full advisory recovery process end to end and returns all the
# pieces the coordinator needs to review.
# --------------------------------------------------------------------------
def run_emergency_recovery(harvests, capacities, emergency_date, emergency_slot):

    # --- Step 1: Generate the original schedule (before the breakdown) ---
    original_schedule, _orig_score, _orig_breakdown, _orig_history = (
        optimize_schedule_ga(harvests, capacities)
    )

    # --- Step 2: Identify which harvests were in the disrupted slot ---
    affected_harvests = identify_affected_harvests(
        original_schedule, emergency_date, emergency_slot
    )
    affected_harvest_ids = affected_harvests["harvest_id"].tolist()

    # --- Step 3: Apply the truck breakdown to a copy of capacities ---
    updated_capacities = apply_truck_breakdown(
        capacities, emergency_date, emergency_slot
    )

    # --- Step 4: Generate a new recovery schedule with reduced capacity ---
    recovery_schedule, recovery_score, recovery_breakdown, _rec_history = (
        optimize_schedule_ga(harvests, updated_capacities)
    )

    # --- Step 5: Build the plain-language change report ---
    change_report = build_recovery_change_report(
        original_schedule, recovery_schedule, affected_harvest_ids
    )

    # --- Step 6: Count what happened for the summary ---
    if change_report.empty:
        changed_harvest_count = 0
    else:
        changed_harvest_count = int(
            (change_report["schedule_changed"] == "Yes").sum()
        )

    # Count harvests left unscheduled in the recovery plan
    unscheduled_harvest_count = int(
        (recovery_schedule["recommendation_status"] == "Unscheduled").sum()
    )

    recovery_is_feasible = bool(recovery_breakdown.get("is_feasible", False))

    # The coordinator must act if anything changed, anything is unscheduled,
    # or the recovery schedule is not feasible.
    coordinator_action_required = (
        "Yes"
        if (changed_harvest_count > 0
            or unscheduled_harvest_count > 0
            or not recovery_is_feasible)
        else "No"
    )

    # --- Step 7: Build the summary dictionary ---
    summary = {
        "emergency_date":              pd.to_datetime(emergency_date).strftime("%Y-%m-%d"),
        "emergency_slot":              emergency_slot,
        "affected_harvest_count":      len(affected_harvest_ids),
        "changed_harvest_count":       changed_harvest_count,
        "unscheduled_harvest_count":   unscheduled_harvest_count,
        "recovery_score":              recovery_score,
        "recovery_is_feasible":        recovery_is_feasible,
        "coordinator_action_required": coordinator_action_required,
    }

    return (
        original_schedule,
        updated_capacities,
        affected_harvests,
        recovery_schedule,
        change_report,
        recovery_breakdown,
        summary,
    )


# --------------------------------------------------------------------------
# Run this file directly to test Emergency Recovery Mode.
# Example: python emergency_recovery.py
# --------------------------------------------------------------------------
if __name__ == "__main__":

    # Load and validate the sample data using the existing functions
    farms, harvests, capacities = load_data()
    validate_data(farms, harvests, capacities)

    # Test scenario: the morning truck on 2026-09-29 breaks down
    emergency_date = "2026-09-29"
    emergency_slot = "Morning"

    (
        original_schedule,
        updated_capacities,
        affected_harvests,
        recovery_schedule,
        change_report,
        recovery_breakdown,
        summary,
    ) = run_emergency_recovery(harvests, capacities, emergency_date, emergency_slot)

    # --- Emergency summary ---
    print("\n--- Emergency Summary ---")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # --- Directly affected harvests ---
    print("\n--- Directly Affected Harvests ---")
    if affected_harvests.empty:
        print("No harvests were assigned to the disrupted slot.")
    else:
        print(affected_harvests.to_string(index=False))

    # --- Recovery schedule ---
    print("\n--- Recovery Schedule ---")
    print(recovery_schedule.to_string(index=False))

    # --- Schedule change report ---
    print("\n--- Schedule Change Report ---")
    print(change_report.to_string(index=False))

    # --- Recovery score breakdown ---
    print("\n--- Recovery Score Breakdown ---")
    for key, value in recovery_breakdown.items():
        print(f"  {key}: {value}")

    # A final reminder that this is advisory only
    print(
        "\nNote: This is an advisory recovery plan. All changes require "
        "farmer and coordinator confirmation before collection."
    )
