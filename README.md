YottaFlex Fulfillment Planning System

Overview

A fulfillment planning system that allocates order lines to fulfillment nodes based on inventory availability, warehouse capacity, and carrier rules.

The project includes synthetic data generation, a Python allocation engine, validation checks, automated tests, and a React dashboard.

Key Features

- Generates reproducible data using seed "20261022".
- Processes 50,000 orders and 57,483 order lines.
- Models 20 fulfillment nodes and 10 carriers.
- Generates 100,000 tracking events.
- Allocates order lines and identifies unfulfillable lines.
- Compares allocation results with ground truth.
- Provides a dashboard for orders, fulfillment nodes, and allocation decisions.

Technology Stack

- Python
- pytest
- React
- Vite
- JavaScript
- CSV

Project Structure

yottaflex-fulfillment/
├── public/
│   └── data/
├── src/
│   ├── data/
│   ├── fulfillment/
│   │   └── allocator.py
│   ├── scripts/
│   │   ├── generate_data.py
│   │   └── validate.py
│   ├── tests/
│   │   └── test_allocator.py
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── main.jsx
├── DATA_DICTIONARY.md
├── PROMPT_HISTORY.md
├── package.json
└── README.md

Prerequisites

Install Python, Node.js, and npm.

Install pytest:

python -m pip install pytest

Setup and Run

1. Generate the dataset

python src/scripts/generate_data.py

2. Run the allocation engine

python src/fulfillment/allocator.py

3. Validate the results

python src/scripts/validate.py

4. Run automated tests

python -m pytest -v -p no:cacheprovider

5. Start the dashboard

npm install
npm run dev

Open the local URL displayed in the terminal, usually "http://localhost:5173".

Current Allocation Results

Metric| Result
Orders processed| 50,000
Order lines| 57,483
Allocated lines| 57,065
Unfulfillable lines| 418
Automated tests| 3 passed

These results describe the current generated dataset and should be rechecked after changing the data or allocation logic.

Dashboard

The dashboard includes:

- Orders: Search and inspect order allocation details.
- Fulfillment Nodes: View fulfillment node information.
- Decisions: Review allocation decisions and exceptions.

The dashboard reads CSV files from "public/data/". After regenerating data or allocation results, copy the required updated CSV files into that directory.

Reproducibility

The data generator uses the fixed seed "20261022". Generate the data, run the allocator, and execute the validation script and tests to reproduce the workflow.

Future Improvements

- Add broader tests for inventory and capacity constraints.
- Strengthen delivery-status roll-up and split-shipment validation.
- Improve carrier service-level and delivery-promise checks.
- Add dashboard filters and enhanced error reporting.
