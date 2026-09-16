"""
data_store.py
-------------
Data storage interface for TanamTepat.

Owned by: Prototype Member 2 (Coordinator Dashboard, Data and API)

Member 1's farmer form calls save_harvest_record() and never touches
CSV logic directly. Member 2 owns how and where data is stored.

This module now writes to the SHARED harvest_data.csv schema so that the
Farmer Submission form and the Coordinator Dashboard both read and write
the same columns. The scheduling engine (optimizer.py) is NOT connected
here yet — that happens in a later integration stage.

Shared CSV columns (in order):
    harvest_id, farm_id, farm_name, crop_type,
    min_quantity_kg, max_quantity_kg, quantity_kg,
    ready_date, latest_collection_date,
    preferred_slot, storage_allowed, priority,
    confidence, confirmation_status

Key rules handled here (so the form stays simple):
    - harvest_id is auto-generated: H001, H002, H003, ...
    - farm_id is auto-generated: F001, F002, ... and REUSED for a farm
      name we have seen before (case-insensitive match).
    - quantity_kg = max_quantity_kg (conservative capacity planning).
    - latest_collection_date = ready_date + max_delay_days.
    - priority is a FRESHNESS urgency label only (not price/importance):
          0 delay days  -> High
          1 delay day   -> Medium
          2+ delay days -> Low
"""

from pathlib import Path
import pandas as pd

# Resolve the CSV path relative to THIS file, so it works no matter what
# folder the app is launched from.
PROJECT_DIR = Path(__file__).resolve().parent
HARVEST_DATA_FILE = PROJECT_DIR / "harvest_data.csv"

# Capacity data lives in data/capacities.csv. This is the SAME file the
# scheduling engine (optimizer.py) reads, so the coordinator's capacity
# entries feed straight into scheduling in a later stage.
CAPACITIES_FILE = PROJECT_DIR / "data" / "capacities.csv"

# The exact column order expected by optimizer.py for capacities.csv.
CAPACITY_COLUMNS = [
    "date",
    "time_slot",
    "truck_capacity_kg",
    "cold_storage_capacity_kg",
    "labour_capacity_kg",
    "truck_available",
]

# The only statuses a coordinator decision may set.
ALLOWED_STATUSES = ("Pending", "Accepted", "Rejected")

# The single source of truth for the shared column order.
SHARED_COLUMNS = [
    "harvest_id",
    "farm_id",
    "farm_name",
    "crop_type",
    "min_quantity_kg",
    "max_quantity_kg",
    "quantity_kg",
    "ready_date",
    "latest_collection_date",
    "preferred_slot",
    "storage_allowed",
    "priority",
    "confidence",
    "confirmation_status",
]

# Fields the farmer form must provide for a submission to be valid.
REQUIRED_INPUT_FIELDS = [
    "farm_name",
    "crop_type",
    "min_quantity_kg",
    "max_quantity_kg",
    "ready_date",
    "max_delay_days",
    "preferred_slot",
    "storage_allowed",
    "confidence",
]


# --------------------------------------------------------------------------
# load_harvest_data()
# Returns all harvest submissions as a DataFrame using the shared columns.
# Returns an empty DataFrame (with the shared columns) if nothing exists yet.
# --------------------------------------------------------------------------
def load_harvest_data() -> pd.DataFrame:
    if HARVEST_DATA_FILE.exists():
        return pd.read_csv(HARVEST_DATA_FILE)
    return pd.DataFrame(columns=SHARED_COLUMNS)


# --------------------------------------------------------------------------
# _next_harvest_id(existing_df)
# Looks at the harvest_id values already saved and returns the next one,
# e.g. if the highest is H003 this returns "H004". Starts at H001.
# --------------------------------------------------------------------------
def _next_harvest_id(existing_df: pd.DataFrame) -> str:
    if existing_df.empty or "harvest_id" not in existing_df.columns:
        return "H001"

    highest = 0
    for value in existing_df["harvest_id"].dropna():
        text = str(value).strip()
        # Expect the format H<number>; skip anything that does not match
        if text.upper().startswith("H") and text[1:].isdigit():
            number = int(text[1:])
            if number > highest:
                highest = number

    return f"H{highest + 1:03d}"


# --------------------------------------------------------------------------
# _get_or_create_farm_id(existing_df, farm_name)
# Reuses the farm_id for a farm name we have seen before (case-insensitive).
# If the farm name is new, generates the next F### id.
# --------------------------------------------------------------------------
def _get_or_create_farm_id(existing_df: pd.DataFrame, farm_name: str) -> str:
    clean_name = farm_name.strip()

    if not existing_df.empty and "farm_name" in existing_df.columns:
        # Case-insensitive match on farm name -> reuse its farm_id
        for _, row in existing_df.iterrows():
            saved_name = str(row.get("farm_name", "")).strip()
            if saved_name.lower() == clean_name.lower():
                return str(row["farm_id"]).strip()

    # New farm name: find the highest existing F### and add one
    highest = 0
    if not existing_df.empty and "farm_id" in existing_df.columns:
        for value in existing_df["farm_id"].dropna():
            text = str(value).strip()
            if text.upper().startswith("F") and text[1:].isdigit():
                number = int(text[1:])
                if number > highest:
                    highest = number

    return f"F{highest + 1:03d}"


# --------------------------------------------------------------------------
# _freshness_priority(delay_days)
# Turns the farmer's safe-delay window into a freshness urgency label.
# This is ONLY about how soon the crop must be collected, never about
# crop price or how important a farmer is.
# --------------------------------------------------------------------------
def _freshness_priority(delay_days: int) -> str:
    if delay_days <= 0:
        return "High"      # must be collected on the ready date
    elif delay_days == 1:
        return "Medium"
    else:
        return "Low"       # 2 or more days of flexibility


# --------------------------------------------------------------------------
# _validate_input(record)
# Checks the raw submission from the farmer form before we save it.
# Raises ValueError with a clear message if something is missing or invalid.
# --------------------------------------------------------------------------
def _validate_input(record: dict) -> None:
    # 1. All required fields must be present and not blank
    for field in REQUIRED_INPUT_FIELDS:
        if field not in record or record[field] is None or str(record[field]).strip() == "":
            raise ValueError(f"Missing required field: {field}")

    # 2. Quantities must be sensible numbers
    try:
        min_qty = float(record["min_quantity_kg"])
        max_qty = float(record["max_quantity_kg"])
    except (TypeError, ValueError):
        raise ValueError("Quantities must be numbers.")

    if max_qty <= 0:
        raise ValueError("Maximum quantity must be greater than 0.")
    if min_qty < 0:
        raise ValueError("Minimum quantity cannot be negative.")
    if min_qty > max_qty:
        raise ValueError("Minimum quantity cannot be greater than maximum quantity.")

    # 3. Delay days must be a whole number that is not negative
    try:
        delay = int(record["max_delay_days"])
    except (TypeError, ValueError):
        raise ValueError("Maximum safe delay must be a whole number of days.")
    if delay < 0:
        raise ValueError("Maximum safe delay cannot be negative.")

    # 4. Slot and storage flag must use the agreed values
    if record["preferred_slot"] not in ("Morning", "Afternoon"):
        raise ValueError("Preferred slot must be 'Morning' or 'Afternoon'.")
    if record["storage_allowed"] not in ("Yes", "No"):
        raise ValueError("Cold storage allowed must be 'Yes' or 'No'.")


# --------------------------------------------------------------------------
# save_harvest_record(record)
# Accepts a RAW submission from the farmer form, fills in the derived fields
# (ids, quantity_kg, latest_collection_date, priority), validates it, and
# appends it to harvest_data.csv using the shared column order.
#
# Expected raw fields from the form:
#   farm_name, crop_type, min_quantity_kg, max_quantity_kg,
#   ready_date, max_delay_days, preferred_slot, storage_allowed, confidence
# (confirmation_status is optional and defaults to "Pending".)
# --------------------------------------------------------------------------
def save_harvest_record(record: dict) -> dict:
    # Step 1: Validate the raw input first
    _validate_input(record)

    # Step 2: Load what we already have so we can generate unique ids
    existing_df = load_harvest_data()

    # Step 3: Generate the ids
    harvest_id = _next_harvest_id(existing_df)
    farm_id    = _get_or_create_farm_id(existing_df, record["farm_name"])

    # Safety check: never allow a duplicate harvest_id
    if not existing_df.empty and harvest_id in set(existing_df["harvest_id"].astype(str)):
        raise ValueError(f"Duplicate harvest_id generated: {harvest_id}")

    # Step 4: Compute the derived fields
    max_qty     = int(float(record["max_quantity_kg"]))
    min_qty     = int(float(record["min_quantity_kg"]))
    delay_days  = int(record["max_delay_days"])

    # quantity_kg uses the MAXIMUM for conservative (safe) capacity planning
    quantity_kg = max_qty

    # latest_collection_date = ready_date + max_delay_days
    ready_date = pd.to_datetime(record["ready_date"])
    latest_collection_date = ready_date + pd.Timedelta(days=delay_days)

    priority = _freshness_priority(delay_days)

    confirmation_status = record.get("confirmation_status", "Pending")
    if str(confirmation_status).strip() == "":
        confirmation_status = "Pending"

    # Step 5: Build the full row in the shared schema
    full_row = {
        "harvest_id":             harvest_id,
        "farm_id":                farm_id,
        "farm_name":              record["farm_name"].strip(),
        "crop_type":              record["crop_type"].strip(),
        "min_quantity_kg":        min_qty,
        "max_quantity_kg":        max_qty,
        "quantity_kg":            quantity_kg,
        "ready_date":             ready_date.strftime("%Y-%m-%d"),
        "latest_collection_date": latest_collection_date.strftime("%Y-%m-%d"),
        "preferred_slot":         record["preferred_slot"],
        "storage_allowed":        record["storage_allowed"],
        "priority":               priority,
        "confidence":             record["confidence"],
        "confirmation_status":    confirmation_status,
    }

    # Step 6: Append and write back, keeping the shared column order
    new_df = pd.DataFrame([full_row], columns=SHARED_COLUMNS)
    if existing_df.empty:
        final_df = new_df
    else:
        final_df = pd.concat([existing_df, new_df], ignore_index=True)

    final_df = final_df[SHARED_COLUMNS]  # enforce column order
    final_df.to_csv(HARVEST_DATA_FILE, index=False)

    # Return the saved row so the form can show a confirmation
    return full_row


# --------------------------------------------------------------------------
# update_confirmation_status(harvest_id, new_status)
# Coordinator decision: change ONLY the confirmation_status of one record.
#
# Rules:
#   - new_status must be one of: Pending, Accepted, Rejected.
#   - the harvest_id must exist, otherwise a clear ValueError is raised.
#   - nothing else in the row is changed.
# Returns the updated row as a dict.
# --------------------------------------------------------------------------
def update_confirmation_status(harvest_id: str, new_status: str) -> dict:
    # Check the status is one we allow
    if new_status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status: {new_status}. "
            f"Allowed statuses are: {', '.join(ALLOWED_STATUSES)}."
        )

    df = load_harvest_data()

    # Find the matching record by harvest_id (compared as text to be safe)
    match_mask = df["harvest_id"].astype(str) == str(harvest_id)
    if not match_mask.any():
        raise ValueError(f"Harvest ID not found: {harvest_id}.")

    # Update only the confirmation_status column for that row
    df.loc[match_mask, "confirmation_status"] = new_status

    # Keep the shared column order and write back
    df = df[SHARED_COLUMNS]
    df.to_csv(HARVEST_DATA_FILE, index=False)

    # Return the updated row so the caller can confirm the change
    updated_row = df.loc[match_mask].iloc[0].to_dict()
    return updated_row


# --------------------------------------------------------------------------
# load_capacities()
# Returns all capacity slots from data/capacities.csv as a DataFrame.
# Returns an empty DataFrame (with the capacity columns) if the file is
# missing, so callers always get a predictable structure.
# --------------------------------------------------------------------------
def load_capacities() -> pd.DataFrame:
    if CAPACITIES_FILE.exists():
        return pd.read_csv(CAPACITIES_FILE)
    return pd.DataFrame(columns=CAPACITY_COLUMNS)


# --------------------------------------------------------------------------
# save_capacity_slot(record)
# Adds a new capacity slot, or UPDATES the existing row when the same
# (date, time_slot) already exists — never creates a duplicate.
#
# Expected fields in record:
#   date (string or date), time_slot ("Morning"/"Afternoon"),
#   truck_capacity_kg, cold_storage_capacity_kg, labour_capacity_kg,
#   truck_available ("Yes"/"No")
#
# Rules:
#   - capacity values cannot be negative
#   - date is stored as YYYY-MM-DD
#   - time_slot must be Morning or Afternoon
#   - truck_available must be Yes or No
# Returns the saved row as a dict.
# --------------------------------------------------------------------------
def save_capacity_slot(record: dict) -> dict:
    # Validate the time slot and truck flag use the agreed values
    if record.get("time_slot") not in ("Morning", "Afternoon"):
        raise ValueError("Time slot must be 'Morning' or 'Afternoon'.")
    if record.get("truck_available") not in ("Yes", "No"):
        raise ValueError("Truck available must be 'Yes' or 'No'.")

    # Validate the three capacity numbers are not negative
    numeric_fields = ["truck_capacity_kg", "cold_storage_capacity_kg", "labour_capacity_kg"]
    clean_numbers = {}
    for field in numeric_fields:
        try:
            value = int(record[field])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"{field} must be a whole number.")
        if value < 0:
            raise ValueError(f"{field} cannot be negative.")
        clean_numbers[field] = value

    # Normalise the date to YYYY-MM-DD text
    date_text = pd.to_datetime(record["date"]).strftime("%Y-%m-%d")

    # Build the row in the exact capacity column order
    new_row = {
        "date":                     date_text,
        "time_slot":                record["time_slot"],
        "truck_capacity_kg":        clean_numbers["truck_capacity_kg"],
        "cold_storage_capacity_kg": clean_numbers["cold_storage_capacity_kg"],
        "labour_capacity_kg":       clean_numbers["labour_capacity_kg"],
        "truck_available":          record["truck_available"],
    }

    df = load_capacities()

    # Look for an existing (date, time_slot) combination to update in place
    if not df.empty:
        # Normalise the stored dates for a reliable comparison
        existing_dates = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        match_mask = (existing_dates == date_text) & (df["time_slot"] == record["time_slot"])
    else:
        match_mask = pd.Series([], dtype=bool)

    if not df.empty and match_mask.any():
        # Update the existing row (no duplicate created)
        for column, value in new_row.items():
            df.loc[match_mask, column] = value
    else:
        # Append a brand-new slot
        df = pd.concat([df, pd.DataFrame([new_row], columns=CAPACITY_COLUMNS)], ignore_index=True)

    # Enforce column order and make sure the data folder exists before saving
    df = df[CAPACITY_COLUMNS]
    CAPACITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CAPACITIES_FILE, index=False)

    return new_row
