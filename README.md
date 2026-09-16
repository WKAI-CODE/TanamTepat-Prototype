# 🌱 TanamTepat

## AI-Assisted Harvest Logistics Planning

TanamTepat is a digital prototype developed by **Team TerraMind** for the **International AgriAccelerateX 2026 Competition**.

It helps an agricultural cooperative review farmer harvest information, record collection capacity, detect overloaded collection slots, and recommend suitable collection schedules.

> **TanamTepat recommends. Farmers and coordinators decide.**

---

## The Problem

Several farmers may need collection at the same time, but the cooperative has limited truck and labour capacity. This may cause overloaded collection periods, delays, and crop-freshness risks.

## Our Solution

TanamTepat compares accepted farmer submissions with available collection capacity. It creates an advisory schedule and recommends alternative dates or time slots when necessary.

If a truck becomes unavailable, the Emergency Recovery feature can also suggest a recovery plan.

---

## Main Workflow

1. **Farmer submits** crop and collection information.
2. **Coordinator reviews** and accepts or rejects the submission.
3. **Coordinator records** truck, labour, and storage capacity.
4. **System generates** an AI-assisted collection schedule.
5. **Farmer and coordinator approve** any suggested changes.

Emergency Recovery is optional and is used when a truck becomes unavailable.

---

## Main Features

- Farmer harvest submission
- Coordinator acceptance and rejection
- Collection-capacity management
- Capacity-overload detection
- Rule-based baseline scheduling
- Genetic Algorithm optimisation
- Recommended date and time-slot changes
- Capacity-utilisation reporting
- Truck-breakdown simulation
- Emergency recovery recommendations
- Human-approval safeguards

---

## Technology Used

- Python
- Streamlit
- pandas
- Plotly
- Genetic Algorithm
- CSV data storage
- GitHub

---

## Project Structure

```text
TanamTepat-Prototype/
├── Main_Page.py
├── ui_components.py
├── data_store.py
├── integration_adapter.py
├── optimizer.py
├── emergency_recovery.py
├── harvest_data.csv
├── requirements.txt
├── data/
│   ├── capacities.csv
│   ├── farms.csv
│   └── harvests.csv
└── pages/
    ├── 1_Farmer_Submission.py
    ├── 2_Coordinator_Dashboard.py
    ├── 3_AI_Schedule.py
    ├── 4_Emergency_Recovery.py
    └── 5_About_and_Safeguards.py
```

---

## Run the Prototype Locally

Install the required packages:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
streamlit run Main_Page.py
```

The application will normally open at:

```text
http://localhost:8501
```

---

## Online Prototype

```text
Deployment link: https://tanamtepat-prototype-terramind.streamlit.app/Emergency_Recovery
```

---

## Important Safeguards

- All schedules are recommendations only.
- Farmers and coordinators must approve collection changes.
- Crop prices are not used.
- Priority represents freshness urgency only.
- Cold-storage capacity is recorded but not automatically allocated.
- The system does not attempt to control market supply.

---

## Prototype Limitation

This is a competition prototype using CSV files for data storage. It is not intended for permanent or large-scale production use.

A future version could use a secure database, user accounts, real-time notifications, and truck tracking.

---

## Team

Developed by **Team TerraMind** for the **International AgriAccelerateX 2026 Competition**.
