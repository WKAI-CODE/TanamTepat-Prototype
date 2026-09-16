# optimizer.py
# TanamTepat - AI-Assisted Harvest Logistics Planning
#
# This file contains:
#   - Data loading
#   - Data validation
#   - Capacity overload detection
#   - Rescheduling candidate identification
#   - Baseline schedule generation
#   - Schedule evaluation and scoring
#   - Genetic Algorithm optimisation

from pathlib import Path
import random
import pandas as pd

# Build the path to the data folder relative to this file's location.
# This works on any computer regardless of where the project is saved.
DATA_FOLDER = Path(__file__).parent / "data"

# --------------------------------------------------------------------------
# load_data()
# Reads the three CSV files and returns them as pandas DataFrames.
# --------------------------------------------------------------------------
def load_data():
    # Read each CSV file from the data folder
    farms      = pd.read_csv(DATA_FOLDER / "farms.csv")
    harvests   = pd.read_csv(DATA_FOLDER / "harvests.csv")
    capacities = pd.read_csv(DATA_FOLDER / "capacities.csv")

    # Convert date columns from plain text into proper pandas date objects
    harvests["ready_date"]            = pd.to_datetime(harvests["ready_date"])
    harvests["latest_collection_date"] = pd.to_datetime(harvests["latest_collection_date"])
    capacities["date"]                = pd.to_datetime(capacities["date"])

    return farms, harvests, capacities

# --------------------------------------------------------------------------
# validate_data(farms, harvests, capacities)
# Checks that all data is complete and consistent.
# Raises a ValueError if anything is wrong.
# Returns True if everything is valid.
# --------------------------------------------------------------------------
def validate_data(farms, harvests, capacities):

    # --- 1. Check that required columns exist ---
    required_farms      = {"farm_id", "farm_name", "location", "contact_name"}
    required_harvests   = {"harvest_id", "farm_id", "crop_type", "quantity_kg",
                           "ready_date", "latest_collection_date",
                           "preferred_slot", "storage_allowed", "priority"}
    required_capacities = {"date", "time_slot", "truck_capacity_kg",
                           "cold_storage_capacity_kg", "labour_capacity_kg",
                           "truck_available"}

    missing_farms = required_farms - set(farms.columns)
    if missing_farms:
        raise ValueError(f"farms.csv is missing columns: {missing_farms}")

    missing_harvests = required_harvests - set(harvests.columns)
    if missing_harvests:
        raise ValueError(f"harvests.csv is missing columns: {missing_harvests}")

    missing_capacities = required_capacities - set(capacities.columns)
    if missing_capacities:
        raise ValueError(f"capacities.csv is missing columns: {missing_capacities}")

    # --- 2. Check for missing values in required columns ---
    missing_vals_farms = [c for c in required_farms if farms[c].isna().any()]
    if missing_vals_farms:
        raise ValueError(
            f"farms.csv has missing values in column(s): {missing_vals_farms}"
        )

    missing_vals_harvests = [c for c in required_harvests if harvests[c].isna().any()]
    if missing_vals_harvests:
        raise ValueError(
            f"harvests.csv has missing values in column(s): {missing_vals_harvests}"
        )

    missing_vals_capacities = [c for c in required_capacities if capacities[c].isna().any()]
    if missing_vals_capacities:
        raise ValueError(
            f"capacities.csv has missing values in column(s): {missing_vals_capacities}"
        )

    # --- 3. Check for duplicate farm IDs ---
    duplicate_farms = farms[farms.duplicated(subset="farm_id")]
    if not duplicate_farms.empty:
        raise ValueError(
            f"farms.csv has duplicate farm_id values: "
            f"{duplicate_farms['farm_id'].tolist()}"
        )

    # --- 4. Check for duplicate harvest IDs ---
    duplicate_harvests = harvests[harvests.duplicated(subset="harvest_id")]
    if not duplicate_harvests.empty:
        raise ValueError(
            f"harvests.csv has duplicate harvest_id values: "
            f"{duplicate_harvests['harvest_id'].tolist()}"
        )

    # --- 5. Check that capacities time_slot is Morning or Afternoon ---
    valid_slots = {"Morning", "Afternoon"}
    bad_cap_slots = capacities[~capacities["time_slot"].isin(valid_slots)]
    if not bad_cap_slots.empty:
        raise ValueError(
            f"capacities.csv has invalid time_slot values: "
            f"{bad_cap_slots['time_slot'].unique().tolist()}. "
            f"Allowed values: Morning, Afternoon."
        )

    # --- 6. Check for duplicate capacity slots (same date + time_slot) ---
    duplicate_caps = capacities[capacities.duplicated(subset=["date", "time_slot"])]
    if not duplicate_caps.empty:
        dupes = (
            duplicate_caps[["date", "time_slot"]]
            .astype(str)
            .values.tolist()
        )
        raise ValueError(
            f"capacities.csv has duplicate date + time_slot combinations: {dupes}"
        )

    # --- 7. Check that every farm_id in harvests exists in farms ---
    known_farm_ids   = set(farms["farm_id"])
    harvest_farm_ids = set(harvests["farm_id"])
    unknown_ids = harvest_farm_ids - known_farm_ids
    if unknown_ids:
        raise ValueError(
            f"harvests.csv references farm_id values not found in farms.csv: "
            f"{unknown_ids}"
        )

    # --- 8. Check that quantity_kg is greater than zero ---
    bad_quantity = harvests[harvests["quantity_kg"] <= 0]
    if not bad_quantity.empty:
        raise ValueError(
            f"harvests.csv has quantity_kg that is zero or negative: "
            f"{bad_quantity['harvest_id'].tolist()}"
        )

    # --- 9. Check that latest_collection_date is not earlier than ready_date ---
    bad_dates = harvests[harvests["latest_collection_date"] < harvests["ready_date"]]
    if not bad_dates.empty:
        raise ValueError(
            f"harvests.csv has latest_collection_date earlier than ready_date: "
            f"{bad_dates['harvest_id'].tolist()}"
        )

    # --- 10. Check that preferred_slot is Morning or Afternoon ---
    bad_slots = harvests[~harvests["preferred_slot"].isin(valid_slots)]
    if not bad_slots.empty:
        raise ValueError(
            f"harvests.csv has invalid preferred_slot values: "
            f"{bad_slots['preferred_slot'].unique().tolist()}. "
            f"Allowed values: Morning, Afternoon."
        )

    # --- 11. Check that storage_allowed is Yes or No ---
    valid_storage = {"Yes", "No"}
    bad_storage   = harvests[~harvests["storage_allowed"].isin(valid_storage)]
    if not bad_storage.empty:
        raise ValueError(
            f"harvests.csv has invalid storage_allowed values: "
            f"{bad_storage['storage_allowed'].unique().tolist()}. "
            f"Allowed values: Yes, No."
        )

    # --- 12. Check that priority is High, Medium or Low ---
    valid_priority = {"High", "Medium", "Low"}
    bad_priority   = harvests[~harvests["priority"].isin(valid_priority)]
    if not bad_priority.empty:
        raise ValueError(
            f"harvests.csv has invalid priority values: "
            f"{bad_priority['priority'].unique().tolist()}. "
            f"Allowed values: High, Medium, Low."
        )

    # --- 13. Check that capacity values are not negative ---
    capacity_cols = ["truck_capacity_kg", "cold_storage_capacity_kg", "labour_capacity_kg"]
    for col in capacity_cols:
        bad_capacity = capacities[capacities[col] < 0]
        if not bad_capacity.empty:
            raise ValueError(
                f"capacities.csv has negative values in column '{col}'."
            )

    # --- 14. Check that truck_available is Yes or No ---
    valid_truck   = {"Yes", "No"}
    bad_truck     = capacities[~capacities["truck_available"].isin(valid_truck)]
    if not bad_truck.empty:
        raise ValueError(
            f"capacities.csv has invalid truck_available values: "
            f"{bad_truck['truck_available'].unique().tolist()}. "
            f"Allowed values: Yes, No."
        )

    # --- 15. Check that every ready_date + preferred_slot in harvests has a
    #         matching date + time_slot entry in capacities ---
    cap_keys = set(zip(capacities["date"].dt.normalize(), capacities["time_slot"]))
    for _, row in harvests.iterrows():
        key = (row["ready_date"].normalize(), row["preferred_slot"])
        if key not in cap_keys:
            date_str = row["ready_date"].strftime("%Y-%m-%d")
            raise ValueError(
                f"No capacity information exists for "
                f"{date_str} {row['preferred_slot']}."
            )

    # All checks passed
    return True

# --------------------------------------------------------------------------
# detect_capacity_overloads(harvests, capacities)
# Groups harvest records by date and time slot, then compares the total
# scheduled quantity against available capacity for each slot.
# Returns a DataFrame summarising the capacity status of every slot.
# --------------------------------------------------------------------------
def detect_capacity_overloads(harvests, capacities):

    # --- Step 1: Total up the harvest quantity for each date + slot pair ---
    # Group by ready_date and preferred_slot, then sum quantity_kg
    grouped = (
        harvests
        .groupby(["ready_date", "preferred_slot"], as_index=False)["quantity_kg"]
        .sum()
        .rename(columns={
            "ready_date":     "date",
            "preferred_slot": "time_slot",
            "quantity_kg":    "scheduled_quantity_kg"
        })
    )

    # --- Step 2: Merge with the capacities table on date and time_slot ---
    # A left join keeps all capacity slots, even those with no harvest assigned
    analysis = capacities.merge(grouped, on=["date", "time_slot"], how="left")

    # Slots with no harvest assigned get a scheduled quantity of 0
    analysis["scheduled_quantity_kg"] = (
        analysis["scheduled_quantity_kg"].fillna(0)
    )

    # --- Step 3: Calculate effective_capacity_kg ---
    # If a truck is available, use the smaller of truck and labour capacity.
    # If no truck is available, effective capacity is 0 (nothing can move).
    def calc_effective(row):
        if row["truck_available"] == "Yes":
            return min(row["truck_capacity_kg"], row["labour_capacity_kg"])
        return 0

    analysis["effective_capacity_kg"] = analysis.apply(calc_effective, axis=1)

    # --- Step 4: Calculate overload_kg ---
    # How many kg exceed the effective capacity? Cannot be negative.
    analysis["overload_kg"] = (
        analysis["scheduled_quantity_kg"] - analysis["effective_capacity_kg"]
    ).clip(lower=0)

    # --- Step 4b: Convert calculated columns to integers for clean display ---
    analysis["scheduled_quantity_kg"] = analysis["scheduled_quantity_kg"].astype(int)
    analysis["effective_capacity_kg"] = analysis["effective_capacity_kg"].astype(int)
    analysis["overload_kg"]           = analysis["overload_kg"].astype(int)

    # --- Step 5: Assign a status label to each slot ---
    def assign_status(row):
        if row["truck_available"] == "No" and row["scheduled_quantity_kg"] > 0:
            return "Truck Unavailable"
        elif row["overload_kg"] > 0:
            return "Overloaded"
        else:
            return "Within Capacity"

    analysis["status"] = analysis.apply(assign_status, axis=1)

    # --- Step 6: Write a plain-English explanation for each slot ---
    def write_explanation(row):
        if row["status"] == "Truck Unavailable":
            return "A truck is unavailable for this collection slot."
        elif row["status"] == "Overloaded":
            overload = int(row["overload_kg"])
            return f"{row['time_slot']} slot is overloaded by {overload:,} kg."
        else:
            return "All scheduled crops are within capacity."

    analysis["explanation"] = analysis.apply(write_explanation, axis=1)

    # --- Step 7: Return only the required columns in a clean order ---
    result = analysis[[
        "date",
        "time_slot",
        "scheduled_quantity_kg",
        "truck_capacity_kg",
        "labour_capacity_kg",
        "effective_capacity_kg",
        "overload_kg",
        "status",
        "explanation"
    ]]

    return result


# --------------------------------------------------------------------------
# identify_rescheduling_candidates(harvests, capacity_report)
# Finds individual harvest records that sit in overloaded or truck-unavailable
# slots and assesses whether each one can safely be considered for movement.
# Does not reschedule or allocate cold storage — assessment only.
# --------------------------------------------------------------------------
def identify_rescheduling_candidates(harvests, capacity_report):

    # --- Step 1: Isolate the problem slots from the capacity report ---
    problem_statuses = {"Overloaded", "Truck Unavailable"}
    problem_slots = capacity_report[
        capacity_report["status"].isin(problem_statuses)
    ][["date", "time_slot"]].copy()

    # Define the output columns once so the empty-return and the real return
    # always have the same structure.
    output_columns = [
        "harvest_id", "farm_id", "crop_type", "quantity_kg",
        "ready_date", "preferred_slot", "latest_collection_date",
        "flexibility_days", "can_delay_collection", "can_use_cold_storage",
        "priority", "movement_order", "mobility_status", "explanation"
    ]

    # If there are no problem slots, return an empty DataFrame with all
    # required columns so the caller always gets a predictable structure.
    if problem_slots.empty:
        return pd.DataFrame(columns=output_columns)

    # --- Step 2: Match harvest records to problem slots ---
    # Rename capacity report columns to align with harvest column names.
    problem_slots = problem_slots.rename(columns={
        "date":      "ready_date",
        "time_slot": "preferred_slot"
    })

    candidates = harvests.merge(problem_slots, on=["ready_date", "preferred_slot"])

    # --- Step 3: Calculate flexibility_days ---
    # How many days lie between ready_date and latest_collection_date?
    # Stored as a whole number (integer).
    candidates["flexibility_days"] = (
        (candidates["latest_collection_date"] - candidates["ready_date"])
        .dt.days
    )

    # --- Step 4: Determine whether collection can be delayed ---
    # "Yes" if there is at least one day of flexibility, otherwise "No".
    candidates["can_delay_collection"] = candidates["flexibility_days"].apply(
        lambda d: "Yes" if d > 0 else "No"
    )

    # --- Step 5: Copy storage_allowed into can_use_cold_storage ---
    candidates["can_use_cold_storage"] = candidates["storage_allowed"]

    # --- Step 6: Assign movement_order based on priority ---
    # Low = 1 (consider moving first), Medium = 2, High = 3.
    # This is only a ranking aid — priority alone does not force movement.
    priority_order = {"Low": 1, "Medium": 2, "High": 3}
    candidates["movement_order"] = candidates["priority"].map(priority_order)

    # --- Step 7: Assign mobility_status ---
    # "Flexible" if collection can be delayed, "Urgent" if it cannot.
    candidates["mobility_status"] = candidates["can_delay_collection"].apply(
        lambda v: "Flexible" if v == "Yes" else "Urgent"
    )

    # --- Step 8: Write a plain-English explanation for each candidate ---
    def write_candidate_explanation(row):
        if row["can_delay_collection"] == "No":
            return "Collection must be completed on its ready date."
        days = int(row["flexibility_days"])
        day_word = "day" if days == 1 else "days"
        if row["can_use_cold_storage"] == "Yes":
            return (
                f"Collection can be delayed by {days} {day_word} "
                f"and cold storage is allowed."
            )
        else:
            return (
                f"Collection can be delayed by {days} {day_word}, "
                f"but cold storage is not allowed."
            )

    candidates["explanation"] = candidates.apply(
        write_candidate_explanation, axis=1
    )

    # --- Step 9: Sort the results ---
    # 1. movement_order ascending   — Low priority candidates listed first
    # 2. flexibility_days descending — most flexible first within same priority
    # 3. quantity_kg ascending       — smaller loads first within same flexibility
    candidates = candidates.sort_values(
        by=["movement_order", "flexibility_days", "quantity_kg"],
        ascending=[True, False, True]
    ).reset_index(drop=True)

    # --- Step 10: Return only the required columns ---
    return candidates[output_columns]



# --------------------------------------------------------------------------
# generate_baseline_schedule(harvests, capacities)
# Produces an advisory recommended collection schedule using deterministic
# greedy rules. No changes are applied automatically — every deviation from
# the original schedule is flagged for human approval.
# Returns two DataFrames: schedule_result and capacity_utilisation.
# --------------------------------------------------------------------------
def generate_baseline_schedule(harvests, capacities):

    # --- Step 1: Work on copies so originals are never modified ---
    hv   = harvests.copy()
    caps = capacities.copy()

    # --- Step 2: Calculate effective_capacity_kg for every slot ---
    # If a truck is available: use the smaller of truck and labour capacity.
    # If no truck is available: nothing can move, so effective capacity is 0.
    def calc_effective(row):
        if row["truck_available"] == "Yes":
            return min(row["truck_capacity_kg"], row["labour_capacity_kg"])
        return 0

    caps["effective_capacity_kg"] = caps.apply(calc_effective, axis=1)

    # --- Step 3: Initialise remaining_capacity_kg for every slot ---
    caps["remaining_capacity_kg"] = caps["effective_capacity_kg"].copy()

    # Build a lookup dict keyed by (date, time_slot) so we can update
    # remaining capacity quickly without searching the whole DataFrame each time.
    remaining = {
        (row["date"], row["time_slot"]): row["remaining_capacity_kg"]
        for _, row in caps.iterrows()
    }

    # --- Step 4: Assign a numeric priority rank ---
    # High urgency = rank 1 (scheduled first), Low urgency = rank 3.
    priority_rank_map = {"High": 1, "Medium": 2, "Low": 3}
    hv["priority_rank"] = hv["priority"].map(priority_rank_map)

    # --- Step 5: Calculate flexibility (days between ready and latest date) ---
    hv["flexibility_days"] = (
        (hv["latest_collection_date"] - hv["ready_date"]).dt.days
    )

    # --- Step 6: Sort harvests to protect urgent crops first ---
    # Order: earliest deadline → highest priority → least flexible → largest load
    hv = hv.sort_values(
        by=["latest_collection_date", "priority_rank",
            "flexibility_days", "quantity_kg"],
        ascending=[True, True, True, False]
    ).reset_index(drop=True)

    # --- Step 7: Helper — return the other time slot ---
    def get_alternative_slot(slot):
        return "Afternoon" if slot == "Morning" else "Morning"

    # --- Step 8: Helper — build the ordered list of candidate slots ---
    # Rule: preferred slot on ready_date first, alternative slot on ready_date
    # second, then future dates (preferred slot before alternative, earlier
    # dates before later dates).
    def ranked_slots(ready_date, latest_date, preferred_slot):
        alt_slot    = get_alternative_slot(preferred_slot)
        candidates  = []
        all_dates   = sorted(caps["date"].unique())
        window_dates = [
            d for d in all_dates
            if ready_date <= d <= latest_date
        ]
        for d in window_dates:
            candidates.append((d, preferred_slot))
            candidates.append((d, alt_slot))
        return candidates

    # --- Step 9: Assign each harvest to its best available slot ---
    results = []

    for _, row in hv.iterrows():
        qty       = row["quantity_kg"]
        ready     = row["ready_date"]
        latest    = row["latest_collection_date"]
        preferred = row["preferred_slot"]
        assigned  = False

        for slot_date, slot_name in ranked_slots(ready, latest, preferred):
            key = (slot_date, slot_name)

            # Skip if this slot is not in the capacity table
            if key not in remaining:
                continue

            # Skip if no truck is available for this slot
            cap_row = caps[
                (caps["date"] == slot_date) & (caps["time_slot"] == slot_name)
            ].iloc[0]
            if cap_row["truck_available"] == "No":
                continue

            # Assign only if the full harvest quantity fits (no splitting)
            if remaining[key] >= qty:
                remaining[key] -= qty

                delay_days = int((slot_date - ready).days)
                same_date  = (slot_date == ready)
                same_slot  = (slot_name == preferred)

                if same_date and same_slot:
                    status   = "Kept Original"
                    slot_chg = "No"
                    approval = "No"
                    reason   = (
                        "Original collection slot fits within available capacity."
                    )
                elif same_date and not same_slot:
                    status   = "Rescheduled"
                    slot_chg = "Yes"
                    approval = "Yes"
                    reason   = (
                        "Alternative time slot recommended to prevent capacity "
                        "overload. Farmer and coordinator approval required."
                    )
                else:
                    # Date has changed. slot_changed only if slot also differs.
                    status   = "Rescheduled"
                    slot_chg = "Yes" if not same_slot else "No"
                    approval = "Yes"
                    reason   = (
                        "Later collection slot recommended within the stated "
                        "freshness limit. Farmer and coordinator approval required."
                    )

                results.append({
                    "harvest_id":              row["harvest_id"],
                    "farm_id":                 row["farm_id"],
                    "crop_type":               row["crop_type"],
                    "quantity_kg":             qty,
                    "ready_date":              ready,
                    "preferred_slot":          preferred,
                    "latest_collection_date":  latest,
                    "priority":                row["priority"],
                    "recommended_date":        slot_date,
                    "recommended_slot":        slot_name,
                    "delay_days":              delay_days,
                    "slot_changed":            slot_chg,
                    "recommendation_status":   status,
                    "human_approval_required": approval,
                    "recommendation_reason":   reason,
                })
                assigned = True
                break  # Move on to the next harvest once assigned

        # No suitable slot was found for this harvest
        if not assigned:
            results.append({
                "harvest_id":              row["harvest_id"],
                "farm_id":                 row["farm_id"],
                "crop_type":               row["crop_type"],
                "quantity_kg":             qty,
                "ready_date":              ready,
                "preferred_slot":          preferred,
                "latest_collection_date":  latest,
                "priority":                row["priority"],
                "recommended_date":        pd.NaT,
                "recommended_slot":        "",
                "delay_days":              None,
                "slot_changed":            "Not Assigned",
                "recommendation_status":   "Unscheduled",
                "human_approval_required": "Yes",
                "recommendation_reason": (
                    "No complete collection slot has enough capacity. "
                    "The coordinator must add capacity, consider a split "
                    "collection, or review cold-storage options."
                ),
            })

    # --- Step 10: Build the schedule_result DataFrame ---
    schedule_result = pd.DataFrame(results)

    # Sort: scheduled records by date → Morning before Afternoon → harvest_id;
    # unscheduled records are placed last.
    # A temporary numeric column is used so Morning (1) sorts before
    # Afternoon (2) instead of alphabetically.
    slot_order = {"Morning": 1, "Afternoon": 2}

    scheduled = schedule_result[
        schedule_result["recommendation_status"] != "Unscheduled"
    ].copy()
    scheduled["slot_sort_order"] = scheduled["recommended_slot"].map(slot_order)

    unscheduled = schedule_result[
        schedule_result["recommendation_status"] == "Unscheduled"
    ].copy()
    unscheduled["slot_sort_order"] = 3  # Unscheduled rows always go last

    schedule_result = pd.concat(
        [scheduled, unscheduled], ignore_index=True
    )
    schedule_result = schedule_result.sort_values(
        by=["recommended_date", "slot_sort_order", "harvest_id"]
    ).reset_index(drop=True)

    # Remove the temporary sort column before returning
    schedule_result = schedule_result.drop(columns=["slot_sort_order"])

    # --- Step 11: Build the capacity_utilisation DataFrame ---
    # assigned_quantity_kg = effective_capacity_kg − remaining_capacity_kg
    util_rows = []
    for _, cap_row in caps.iterrows():
        key       = (cap_row["date"], cap_row["time_slot"])
        effective = cap_row["effective_capacity_kg"]
        rem       = remaining[key]
        assigned  = effective - rem

        # Avoid division by zero when effective capacity is 0
        utilisation = round((assigned / effective) * 100, 1) if effective > 0 else 0.0

        util_rows.append({
            "date":                   cap_row["date"],
            "time_slot":              cap_row["time_slot"],
            "effective_capacity_kg":  int(effective),
            "assigned_quantity_kg":   int(assigned),
            "remaining_capacity_kg":  int(rem),
            "utilisation_percentage": utilisation,
        })

    capacity_utilisation = pd.DataFrame(util_rows)

    return schedule_result, capacity_utilisation


# --------------------------------------------------------------------------
# evaluate_schedule(schedule_result, capacities)
# Calculates a penalty score for a recommended schedule.
# A lower score means a better schedule.
# This score will be used by the Genetic Algorithm to compare candidates.
# --------------------------------------------------------------------------
def evaluate_schedule(schedule_result, capacities):

    # Work on copies so the originals are never changed
    sched = schedule_result.copy()
    caps  = capacities.copy()

    # Ensure date columns are proper datetime objects
    sched["recommended_date"]       = pd.to_datetime(sched["recommended_date"],       errors="coerce")
    sched["ready_date"]             = pd.to_datetime(sched["ready_date"],             errors="coerce")
    sched["latest_collection_date"] = pd.to_datetime(sched["latest_collection_date"], errors="coerce")
    caps["date"]                    = pd.to_datetime(caps["date"],                    errors="coerce")

    # ------------------------------------------------------------------
    # Penalty weights — change these constants to tune the scoring model
    # ------------------------------------------------------------------
    UNSCHEDULED_BASE    = 10_000  # Base cost per unscheduled harvest × priority + qty
    FRESHNESS_VIOLATION = 50_000  # Cost per harvest collected outside freshness window
    CAPACITY_OVERLOAD   = 100     # Cost per kg that exceeds effective slot capacity
    MISSING_CAPACITY    = 50_000  # Cost per harvest assigned to a non-existent slot
    DELAY_PER_DAY       = 10      # Cost per day of delay × priority multiplier
    SLOT_CHANGE_PENALTY = 5       # Cost per time-slot change × priority multiplier

    # Higher-priority harvests carry a larger penalty when things go wrong
    priority_multiplier = {"High": 3, "Medium": 2, "Low": 1}

    # ------------------------------------------------------------------
    # Initialise penalty accumulators
    # ------------------------------------------------------------------
    unscheduled_penalty         = 0
    freshness_violation_penalty = 0
    capacity_overload_penalty   = 0
    missing_capacity_penalty    = 0
    delay_penalty               = 0
    time_slot_change_penalty    = 0

    unscheduled_count           = 0
    freshness_violation_count   = 0
    overloaded_slot_count       = 0
    missing_capacity_count      = 0
    delayed_harvest_count       = 0
    changed_time_slot_count     = 0

    # Quick lookup of all valid (date, time_slot) pairs from capacities
    valid_slots = set(zip(caps["date"], caps["time_slot"]))

    # Separate assigned and unscheduled rows once for reuse below
    unscheduled_rows = sched[sched["recommendation_status"] == "Unscheduled"]
    assigned_rows    = sched[sched["recommendation_status"] != "Unscheduled"]

    # ------------------------------------------------------------------
    # A. Unscheduled penalty
    # Strong penalty because the crop has received no collection slot at all.
    # Formula: (UNSCHEDULED_BASE × priority_multiplier) + quantity_kg
    # ------------------------------------------------------------------
    for _, row in unscheduled_rows.iterrows():
        multiplier           = priority_multiplier.get(row["priority"], 1)
        unscheduled_penalty += (UNSCHEDULED_BASE * multiplier) + row["quantity_kg"]
        unscheduled_count   += 1

    # ------------------------------------------------------------------
    # B. Freshness violation penalty
    # Applied when a harvest is assigned to a date outside its valid window.
    # Formula: FRESHNESS_VIOLATION × priority_multiplier
    # ------------------------------------------------------------------
    for _, row in assigned_rows.iterrows():
        rec_date = row["recommended_date"]
        if pd.isna(rec_date):
            continue
        if rec_date < row["ready_date"] or rec_date > row["latest_collection_date"]:
            multiplier                   = priority_multiplier.get(row["priority"], 1)
            freshness_violation_penalty += FRESHNESS_VIOLATION * multiplier
            freshness_violation_count   += 1

    # ------------------------------------------------------------------
    # C. Capacity overload penalty
    # Group assigned harvests by slot and compare totals against capacity.
    # Formula: CAPACITY_OVERLOAD × overload_kg per slot
    # ------------------------------------------------------------------
    assigned_grouped = (
        assigned_rows
        .groupby(["recommended_date", "recommended_slot"])["quantity_kg"]
        .sum()
        .reset_index()
        .rename(columns={"quantity_kg": "total_assigned_kg"})
    )

    seen_overloaded = set()

    for _, grp in assigned_grouped.iterrows():
        slot_date = grp["recommended_date"]
        slot_name = grp["recommended_slot"]
        key       = (slot_date, slot_name)

        cap_match = caps[
            (caps["date"] == slot_date) & (caps["time_slot"] == slot_name)
        ]
        if cap_match.empty:
            continue  # Handled by the missing-capacity check

        cap_row = cap_match.iloc[0]

        # Effective capacity: smaller of truck and labour, or 0 if no truck
        if cap_row["truck_available"] == "Yes":
            effective = min(cap_row["truck_capacity_kg"], cap_row["labour_capacity_kg"])
        else:
            effective = 0

        overload_kg = max(0, grp["total_assigned_kg"] - effective)
        if overload_kg > 0:
            capacity_overload_penalty += CAPACITY_OVERLOAD * overload_kg
            if key not in seen_overloaded:
                overloaded_slot_count += 1
                seen_overloaded.add(key)

    # ------------------------------------------------------------------
    # D. Missing capacity penalty
    # Applied when an assigned harvest uses a slot not in capacities,
    # OR when recommended_date is missing or recommended_slot is empty
    # (which means the scheduler could not place the harvest at all —
    # treated as a hard constraint failure for GA evaluation purposes).
    # Formula: MISSING_CAPACITY per affected harvest
    # ------------------------------------------------------------------
    for _, row in assigned_rows.iterrows():
        rec_date = row["recommended_date"]
        rec_slot = row["recommended_slot"]
        # Treat a missing date or empty slot as a hard missing-capacity problem
        if pd.isna(rec_date) or rec_slot == "" or str(rec_slot).strip() == "":
            missing_capacity_penalty += MISSING_CAPACITY
            missing_capacity_count   += 1
            continue
        if (rec_date, rec_slot) not in valid_slots:
            missing_capacity_penalty += MISSING_CAPACITY
            missing_capacity_count   += 1

    # ------------------------------------------------------------------
    # E. Delay penalty
    # Calculate delay directly from recommended_date minus ready_date so
    # the GA can evaluate any schedule without relying on the delay_days
    # column that was pre-filled by the scheduler.
    # Formula: DELAY_PER_DAY × delay_days × priority_multiplier
    # ------------------------------------------------------------------
    for _, row in assigned_rows.iterrows():
        rec_date = row["recommended_date"]
        if pd.isna(rec_date):
            continue
        delay = int((rec_date - row["ready_date"]).days)
        if delay <= 0:
            continue
        multiplier     = priority_multiplier.get(row["priority"], 1)
        delay_penalty += DELAY_PER_DAY * delay * multiplier
        delayed_harvest_count += 1

    # ------------------------------------------------------------------
    # F. Time-slot change penalty
    # Applied when the recommended slot differs from the farmer's preference.
    # Formula: SLOT_CHANGE_PENALTY × priority_multiplier
    # ------------------------------------------------------------------
    for _, row in assigned_rows.iterrows():
        if row["recommended_slot"] != row["preferred_slot"]:
            multiplier                = priority_multiplier.get(row["priority"], 1)
            time_slot_change_penalty += SLOT_CHANGE_PENALTY * multiplier
            changed_time_slot_count  += 1

    # ------------------------------------------------------------------
    # Total score
    # ------------------------------------------------------------------
    total_score = (
        unscheduled_penalty
        + freshness_violation_penalty
        + capacity_overload_penalty
        + missing_capacity_penalty
        + delay_penalty
        + time_slot_change_penalty
    )

    # ------------------------------------------------------------------
    # Feasibility check
    # A schedule is feasible only when all hard constraints are satisfied.
    # Delay and slot changes are soft constraints — they lower quality but
    # do not make a schedule infeasible.
    # ------------------------------------------------------------------
    is_feasible = (
        unscheduled_count         == 0
        and freshness_violation_count == 0
        and overloaded_slot_count     == 0
        and missing_capacity_count    == 0
    )

    # ------------------------------------------------------------------
    # Breakdown dictionary
    # ------------------------------------------------------------------
    breakdown = {
        "unscheduled_penalty":         unscheduled_penalty,
        "freshness_violation_penalty": freshness_violation_penalty,
        "capacity_overload_penalty":   capacity_overload_penalty,
        "missing_capacity_penalty":    missing_capacity_penalty,
        "delay_penalty":               delay_penalty,
        "time_slot_change_penalty":    time_slot_change_penalty,
        "total_score":                 total_score,
        "unscheduled_count":           unscheduled_count,
        "freshness_violation_count":   freshness_violation_count,
        "overloaded_slot_count":       overloaded_slot_count,
        "missing_capacity_count":      missing_capacity_count,
        "delayed_harvest_count":       delayed_harvest_count,
        "changed_time_slot_count":     changed_time_slot_count,
        "is_feasible":                 is_feasible,
    }

    return total_score, breakdown


# --------------------------------------------------------------------------
# _chromosome_to_schedule(chromosome, harvests)
# Helper used by the Genetic Algorithm.
# Converts a chromosome (list of gene values) into the same schedule_result
# DataFrame structure produced by generate_baseline_schedule(), so that
# evaluate_schedule() can score it directly.
#
# chromosome : list with one entry per harvest row (same order as harvests).
#              Each entry is either a (date, time_slot) tuple or None
#              (None means Unscheduled).
# --------------------------------------------------------------------------
def _chromosome_to_schedule(chromosome, harvests):
    rows = []
    for i, row in harvests.reset_index(drop=True).iterrows():
        gene      = chromosome[i]
        preferred = row["preferred_slot"]
        ready     = row["ready_date"]
        latest    = row["latest_collection_date"]

        if gene is None:
            # No slot was assigned to this harvest
            rows.append({
                "harvest_id":              row["harvest_id"],
                "farm_id":                 row["farm_id"],
                "crop_type":               row["crop_type"],
                "quantity_kg":             row["quantity_kg"],
                "ready_date":              ready,
                "preferred_slot":          preferred,
                "latest_collection_date":  latest,
                "priority":                row["priority"],
                "recommended_date":        pd.NaT,
                "recommended_slot":        "",
                "delay_days":              None,
                "slot_changed":            "Not Assigned",
                "recommendation_status":   "Unscheduled",
                "human_approval_required": "Yes",
                "recommendation_reason": (
                    "No complete collection slot has enough capacity. "
                    "The coordinator must add capacity, consider a split "
                    "collection, or review cold-storage options."
                ),
            })
        else:
            slot_date, slot_name = gene
            delay_days = int((slot_date - ready).days)
            same_date  = (slot_date == ready)
            same_slot  = (slot_name == preferred)

            if same_date and same_slot:
                status   = "Kept Original"
                slot_chg = "No"
                approval = "No"
                reason   = (
                    "Original collection slot fits within available capacity."
                )
            elif same_date and not same_slot:
                status   = "Rescheduled"
                slot_chg = "Yes"
                approval = "Yes"
                reason   = (
                    "Alternative time slot recommended to prevent capacity "
                    "overload. Farmer and coordinator approval required."
                )
            else:
                # Date changed. slot_changed only when the slot also differs.
                status   = "Rescheduled"
                slot_chg = "Yes" if not same_slot else "No"
                approval = "Yes"
                reason   = (
                    "Later collection slot recommended within the stated "
                    "freshness limit. Farmer and coordinator approval required."
                )

            rows.append({
                "harvest_id":              row["harvest_id"],
                "farm_id":                 row["farm_id"],
                "crop_type":               row["crop_type"],
                "quantity_kg":             row["quantity_kg"],
                "ready_date":              ready,
                "preferred_slot":          preferred,
                "latest_collection_date":  latest,
                "priority":                row["priority"],
                "recommended_date":        slot_date,
                "recommended_slot":        slot_name,
                "delay_days":              delay_days,
                "slot_changed":            slot_chg,
                "recommendation_status":   status,
                "human_approval_required": approval,
                "recommendation_reason":   reason,
            })

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# optimize_schedule_ga(harvests, capacities, ...)
# Searches for a collection schedule with a lower penalty score than the
# baseline by evolving a population of candidate schedules.
# Uses only Python standard libraries and pandas — no external GA library.
#
# Parameters
# ----------
# population_size : number of candidate schedules per generation
# generations     : number of evolution cycles to run
# mutation_rate   : probability that any single gene is randomly changed
# random_seed     : fixes randomness so the result is repeatable
#
# Returns
# -------
# best_schedule   : schedule_result DataFrame for the best individual found
# best_score      : penalty score for the best schedule
# best_breakdown  : score breakdown dictionary for the best schedule
# history_df      : DataFrame with columns [generation, best_score]
# --------------------------------------------------------------------------
def optimize_schedule_ga(
    harvests,
    capacities,
    population_size=50,
    generations=100,
    mutation_rate=0.10,
    random_seed=42,
):
    random.seed(random_seed)

    hv = harvests.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Step 1: Build the list of valid gene options for every harvest.
    # A gene is a (date, time_slot) tuple that exists in capacities AND
    # falls within [ready_date, latest_collection_date].
    # None represents the Unscheduled option (always included).
    # ------------------------------------------------------------------
    cap_slots = list(zip(capacities["date"], capacities["time_slot"]))

    valid_options = []   # valid_options[i] = list of genes for harvest i
    for _, row in hv.iterrows():
        options = [
            (slot_date, slot_name)
            for slot_date, slot_name in cap_slots
            if row["ready_date"] <= slot_date <= row["latest_collection_date"]
        ]
        options.append(None)   # Unscheduled is always a legal gene value
        valid_options.append(options)

    n_harvests = len(hv)

    # ------------------------------------------------------------------
    # Step 2: Convert the baseline schedule into the first chromosome so
    # the GA always starts with at least one known-good solution.
    # ------------------------------------------------------------------
    baseline_schedule, _ = generate_baseline_schedule(harvests, capacities)

    baseline_map = dict(
        zip(
            baseline_schedule["harvest_id"],
            zip(
                baseline_schedule["recommended_date"],
                baseline_schedule["recommended_slot"],
            ),
        )
    )
    baseline_chromosome = []
    for _, row in hv.iterrows():
        rec_date, rec_slot = baseline_map[row["harvest_id"]]
        if pd.isna(rec_date) or rec_slot == "":
            baseline_chromosome.append(None)
        else:
            baseline_chromosome.append((rec_date, rec_slot))

    # ------------------------------------------------------------------
    # Step 3: Build the initial population.
    # Individual 0 = baseline. The rest are randomly generated.
    # ------------------------------------------------------------------
    def random_chromosome():
        return [random.choice(opts) for opts in valid_options]

    population = [baseline_chromosome]
    for _ in range(population_size - 1):
        population.append(random_chromosome())

    # ------------------------------------------------------------------
    # Step 4: GA operation helpers
    # ------------------------------------------------------------------

    # Pre-build lookup structures once so the fast scorer can use them
    # without touching pandas inside the tight evaluation loop.

    # Penalty weights (must match evaluate_schedule exactly)
    _UNSCHEDULED_BASE    = 10_000
    _FRESHNESS_VIOLATION = 50_000
    _CAPACITY_OVERLOAD   = 100
    _MISSING_CAPACITY    = 50_000
    _DELAY_PER_DAY       = 10
    _SLOT_CHANGE_PENALTY = 5
    _PRIORITY_MULT       = {"High": 3, "Medium": 2, "Low": 1}

    # Effective capacity per slot: (date, time_slot) → int kg
    _effective_cap = {}
    for _, cr in capacities.iterrows():
        if cr["truck_available"] == "Yes":
            eff = min(cr["truck_capacity_kg"], cr["labour_capacity_kg"])
        else:
            eff = 0
        _effective_cap[(cr["date"], cr["time_slot"])] = eff

    _valid_slot_keys = set(_effective_cap.keys())

    # Harvest metadata indexed by position (matches hv row order)
    _hv_records = [
        {
            "qty":       r["quantity_kg"],
            "ready":     r["ready_date"],
            "latest":    r["latest_collection_date"],
            "preferred": r["preferred_slot"],
            "mult":      _PRIORITY_MULT.get(r["priority"], 1),
        }
        for _, r in hv.iterrows()
    ]

    def _fast_score(chrom):
        """
        Pure-Python penalty calculation — same rules as evaluate_schedule()
        but with no DataFrame overhead. Used for all evaluations inside the
        evolution loop. evaluate_schedule() is still called once at the end
        to produce the full breakdown for the best individual.
        """
        score = 0

        # Track total kg assigned to each slot to check for overloads
        slot_load = {}   # (date, slot) -> total kg assigned

        for i, gene in enumerate(chrom):
            h = _hv_records[i]

            if gene is None:
                # A. Unscheduled penalty
                score += (_UNSCHEDULED_BASE * h["mult"]) + h["qty"]
                continue

            slot_date, slot_name = gene

            # D. Missing capacity — slot not in capacities at all
            key = (slot_date, slot_name)
            if key not in _valid_slot_keys:
                score += _MISSING_CAPACITY
                continue

            # B. Freshness violation — date outside the valid window
            if slot_date < h["ready"] or slot_date > h["latest"]:
                score += _FRESHNESS_VIOLATION * h["mult"]

            # E. Delay penalty
            delay = (slot_date - h["ready"]).days
            if delay > 0:
                score += _DELAY_PER_DAY * delay * h["mult"]

            # F. Time-slot change penalty
            if slot_name != h["preferred"]:
                score += _SLOT_CHANGE_PENALTY * h["mult"]

            # Accumulate load for overload check (C)
            slot_load[key] = slot_load.get(key, 0) + h["qty"]

        # C. Capacity overload penalty — checked once per slot
        for key, total_kg in slot_load.items():
            eff = _effective_cap.get(key, 0)
            overload = total_kg - eff
            if overload > 0:
                score += _CAPACITY_OVERLOAD * overload

        return score

    def tournament_select(pop, scores, tournament_size=3):
        """Return the chromosome with the lowest score among 3 random picks."""
        competitors = random.sample(range(len(pop)), tournament_size)
        winner = min(competitors, key=lambda idx: scores[idx])
        return pop[winner]

    def crossover(parent_a, parent_b):
        """Uniform crossover: each gene is taken from one parent at random."""
        return [
            random.choice([parent_a[i], parent_b[i]])
            for i in range(n_harvests)
        ]

    def mutate(chrom):
        """Replace each gene with a random valid option at the given rate."""
        child = chrom[:]
        for i in range(n_harvests):
            if random.random() < mutation_rate:
                child[i] = random.choice(valid_options[i])
        return child

    # ------------------------------------------------------------------
    # Step 5: Evaluate the initial population (fast scorer)
    # ------------------------------------------------------------------
    scores = [_fast_score(chrom) for chrom in population]

    # Find and store the best individual seen so far
    best_idx   = min(range(len(scores)), key=lambda i: scores[i])
    best_chrom = population[best_idx][:]
    best_score = scores[best_idx]

    history = []   # One entry per generation recording the best score

    # ------------------------------------------------------------------
    # Step 6: Main evolution loop
    # ------------------------------------------------------------------
    for gen in range(generations):

        # Elitism: carry the current best individual into the next generation
        new_population = [best_chrom[:]]

        while len(new_population) < population_size:
            parent_a = tournament_select(population, scores)
            parent_b = tournament_select(population, scores)
            child    = crossover(parent_a, parent_b)
            child    = mutate(child)
            new_population.append(child)

        population = new_population
        scores     = [_fast_score(chrom) for chrom in population]

        # Update the global best if this generation improved the score
        gen_best_idx = min(range(len(scores)), key=lambda i: scores[i])
        if scores[gen_best_idx] < best_score:
            best_chrom = population[gen_best_idx][:]
            best_score = scores[gen_best_idx]

        history.append({"generation": gen + 1, "best_score": best_score})

    # ------------------------------------------------------------------
    # Step 7: Build the final best schedule DataFrame and score it once
    # using the full evaluate_schedule() to get the complete breakdown.
    # Sort the same way as generate_baseline_schedule does:
    # Morning before Afternoon, unscheduled last, then by harvest_id.
    # ------------------------------------------------------------------
    best_schedule = _chromosome_to_schedule(best_chrom, hv)
    best_score, best_breakdown = evaluate_schedule(best_schedule, capacities)

    slot_order = {"Morning": 1, "Afternoon": 2}

    scheduled_part = best_schedule[
        best_schedule["recommendation_status"] != "Unscheduled"
    ].copy()
    scheduled_part["slot_sort_order"] = scheduled_part["recommended_slot"].map(slot_order)

    unscheduled_part = best_schedule[
        best_schedule["recommendation_status"] == "Unscheduled"
    ].copy()
    unscheduled_part["slot_sort_order"] = 3

    best_schedule = pd.concat(
        [scheduled_part, unscheduled_part], ignore_index=True
    )
    best_schedule = best_schedule.sort_values(
        by=["recommended_date", "slot_sort_order", "harvest_id"]
    ).reset_index(drop=True)
    best_schedule = best_schedule.drop(columns=["slot_sort_order"])

    history_df = pd.DataFrame(history)

    return best_schedule, best_score, best_breakdown, history_df


# --------------------------------------------------------------------------
# Run this file directly to test that data loads and validates correctly.
# Example: python optimizer.py
# --------------------------------------------------------------------------
if __name__ == "__main__":
    farms, harvests, capacities = load_data()
    validate_data(farms, harvests, capacities)

    print(f"Farms loaded:              {len(farms)} records")
    print(f"Harvest records loaded:    {len(harvests)} records")
    print(f"Capacity slots loaded:     {len(capacities)} records")
    print("All TanamTepat data is valid.")

    # Run capacity overload detection and print the results
    print("\n--- Capacity Analysis ---")
    capacity_report = detect_capacity_overloads(harvests, capacities)
    print(capacity_report.to_string(index=False))

    # Identify and print rescheduling candidates
    print("\n--- Rescheduling Candidates ---")
    candidates = identify_rescheduling_candidates(harvests, capacity_report)
    if candidates.empty:
        print("No rescheduling candidates are required.")
    else:
        print(candidates.to_string(index=False))

    # Generate and print the baseline recommended schedule
    print("\n--- Baseline Recommended Schedule ---")
    schedule_result, capacity_utilisation = generate_baseline_schedule(
        harvests, capacities
    )
    print(schedule_result.to_string(index=False))

    print("\n--- Capacity Utilisation After Recommendation ---")
    print(capacity_utilisation.to_string(index=False))

    # Evaluate and print the baseline schedule score
    print("\n--- Baseline Schedule Score ---")
    baseline_score, baseline_breakdown = evaluate_schedule(schedule_result, capacities)
    for key, value in baseline_breakdown.items():
        print(f"  {key}: {value}")

    # Run the Genetic Algorithm
    print("\n--- Running Genetic Algorithm (this may take a moment) ---")
    best_schedule, best_score, best_breakdown, history_df = optimize_schedule_ga(
        harvests, capacities
    )

    print("\n--- Genetic Algorithm Recommended Schedule ---")
    print(best_schedule.to_string(index=False))

    print("\n--- Genetic Algorithm Score ---")
    for key, value in best_breakdown.items():
        print(f"  {key}: {value}")

    # Compare GA result against the baseline
    if best_score < baseline_score:
        improvement = baseline_score - best_score
        print(f"\n  The Genetic Algorithm improved the baseline score by {improvement} points.")
        print(f"  Baseline: {baseline_score}  →  GA best: {best_score}")
    elif best_score == baseline_score:
        print(f"\n  The Genetic Algorithm matched the baseline score ({baseline_score}). No improvement found.")
    else:
        print(f"\n  The Genetic Algorithm did not improve the baseline score.")
        print(f"  Baseline: {baseline_score}  →  GA best: {best_score}")

    print("\n--- Score History (first and last 5 generations) ---")
    print(history_df.head(5).to_string(index=False))
    print("  ...")
    print(history_df.tail(5).to_string(index=False))

