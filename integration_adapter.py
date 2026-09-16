"""
integration_adapter.py
-----------------------
Bridges the coordinator's live data (harvest_data.csv + data/capacities.csv)
into the exact shapes the verified scheduling engine (optimizer.py) expects.

Owned by: Integration layer (Stage 2B)

Why this file exists:
    optimizer.py and emergency_recovery.py were written and verified against
    fixed sample CSVs with columns: farms(farm_id, farm_name, location,
    contact_name), harvests(...), capacities(...). The live app instead stores
    farmer submissions and capacity in the shared Stage 1/2A schemas. This
    adapter converts the live data into those engine shapes WITHOUT touching
    the engine or changing any numbers.

Key rule:
    Only submissions with confirmation_status == "Accepted" may enter
    scheduling. Pending and Rejected submissions are excluded here.

This file does NOT:
    - reimplement validation (it calls the existing validate_data())
    - invent fake capacity rows
    - change any farmer submission or capacity record on disk
"""

import pandas as pd

# Live data access (Stage 1 / 2A shared schema)
from data_store import load_harvest_data, load_capacities

# The verified validator from the scheduling engine — reused, never copied.
from optimizer import validate_data


# The columns the harvests DataFrame must expose for the engine, in order.
HARVEST_ENGINE_COLUMNS = [
    "harvest_id",
    "farm_id",
    "crop_type",
    "quantity_kg",
    "ready_date",
    "latest_collection_date",
    "preferred_slot",
    "storage_allowed",
    "priority",
]


def load_live_scheduling_data():
    """
    Build (farms, harvests, capacities) from the live coordinator data,
    validate them with the engine's own validator, and return them.

    Returns:
        farms, harvests, capacities  (all pandas DataFrames)

    Raises:
        ValueError with a clear, plain-language message when the data is not
        ready for scheduling (no Accepted submissions, no capacity, missing
        capacity slot, missing columns, or unconvertible dates).
    """

    # ------------------------------------------------------------------
    # Step 1: Load the live data through the shared data_store helpers.
    # ------------------------------------------------------------------
    submissions = load_harvest_data()
    capacities = load_capacities()

    # ------------------------------------------------------------------
    # Step 2: Keep ONLY Accepted submissions. Pending/Rejected are excluded.
    # ------------------------------------------------------------------
    if submissions.empty or "confirmation_status" not in submissions.columns:
        raise ValueError(
            "There are no Accepted submissions to schedule yet. "
            "Accept at least one submission on the Coordinator Dashboard first."
        )

    accepted = submissions[
        submissions["confirmation_status"].astype(str) == "Accepted"
    ].copy()

    if accepted.empty:
        raise ValueError(
            "There are no Accepted submissions to schedule yet. "
            "Accept at least one submission on the Coordinator Dashboard first."
        )

    # ------------------------------------------------------------------
    # Step 3: Make sure there is capacity data at all.
    # ------------------------------------------------------------------
    if capacities.empty:
        raise ValueError(
            "There are no capacity records yet. "
            "Add date-specific capacity on the Coordinator Dashboard first."
        )

    # ------------------------------------------------------------------
    # Step 4: Check the accepted submissions have the columns we need.
    # ------------------------------------------------------------------
    missing_cols = [c for c in HARVEST_ENGINE_COLUMNS if c not in accepted.columns]
    if missing_cols:
        raise ValueError(
            f"Accepted submissions are missing required columns: {missing_cols}."
        )

    # ------------------------------------------------------------------
    # Step 5: Build the harvests DataFrame in the exact engine shape.
    # ------------------------------------------------------------------
    harvests = accepted[HARVEST_ENGINE_COLUMNS].copy()

    # Convert the two date columns to real datetimes. If any value cannot be
    # parsed, tell the coordinator clearly instead of failing deep inside GA.
    for date_col in ["ready_date", "latest_collection_date"]:
        harvests[date_col] = pd.to_datetime(harvests[date_col], errors="coerce")
        if harvests[date_col].isna().any():
            raise ValueError(
                f"Some Accepted submissions have an unreadable {date_col}. "
                f"Please correct the date format (YYYY-MM-DD)."
            )

    # ------------------------------------------------------------------
    # Step 6: Build the farms DataFrame from unique farm_id + farm_name.
    # location and contact_name are required by the validator but are not
    # used by the scheduling maths, so we fill safe placeholder text.
    # ------------------------------------------------------------------
    if "farm_name" not in accepted.columns:
        raise ValueError("Accepted submissions are missing the 'farm_name' column.")

    farms = (
        accepted[["farm_id", "farm_name"]]
        .drop_duplicates(subset="farm_id")
        .reset_index(drop=True)
    )
    farms["location"] = "Not provided in prototype"
    farms["contact_name"] = "Not provided in prototype"

    # ------------------------------------------------------------------
    # Step 7: Prepare capacities — convert the date column to datetime.
    # ------------------------------------------------------------------
    capacities = capacities.copy()
    if "date" not in capacities.columns:
        raise ValueError("Capacity records are missing the 'date' column.")

    capacities["date"] = pd.to_datetime(capacities["date"], errors="coerce")
    if capacities["date"].isna().any():
        raise ValueError(
            "Some capacity records have an unreadable date. "
            "Please correct the date format (YYYY-MM-DD)."
        )

    # ------------------------------------------------------------------
    # Step 8: Pre-check that every Accepted (ready_date, preferred_slot)
    # has a matching capacity slot. The engine's validator also checks this,
    # but catching it here lets us give a friendlier, more specific message.
    # ------------------------------------------------------------------
    capacity_keys = set(
        zip(capacities["date"].dt.normalize(), capacities["time_slot"].astype(str))
    )
    for _, row in harvests.iterrows():
        key = (row["ready_date"].normalize(), str(row["preferred_slot"]))
        if key not in capacity_keys:
            date_text = row["ready_date"].strftime("%Y-%m-%d")
            raise ValueError(
                f"No capacity record exists for {date_text} {row['preferred_slot']} "
                f"(needed by harvest {row['harvest_id']}). "
                f"Add that capacity slot on the Coordinator Dashboard."
            )

    # ------------------------------------------------------------------
    # Step 9: Run the engine's own validator. We do NOT duplicate its logic;
    # we simply trust it and surface any error it raises.
    # ------------------------------------------------------------------
    validate_data(farms, harvests, capacities)

    return farms, harvests, capacities
