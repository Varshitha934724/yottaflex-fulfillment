YottaFlex Fulfillment Planning System

Overview

This project implements a fulfillment planning system that allocates order lines to fulfillment nodes based on inventory availability, node capacity, and carrier selection rules.

The project includes a synthetic dataset generator, a Python allocation engine, ground-truth validation, automated tests, and a React dashboard.

Key Features

- Generates reproducible synthetic data using seed "20261022".
- Processes 50,000 orders and their order lines.
- Models 20 fulfillment nodes and 10 carriers.
- Generates 100,000 tracking events.
- Produces allocation results for each order line.
- Identifies allocated and unfulfillable order lines.
- Validates allocation results against the supplied ground truth.
- Provides a dashboard for viewing orders, fulfillment nodes, and allocation decisions.

Technology Stack

- Python
- pytest
- React
- Vite
- JavaScript
- CSV datasets

Project Structure

yottaflex-fulfillment/
├── public/
│   └── data/
├── src/
│   ├── data/
│   ├── fulfillment/
│   │   └── allocator.py
│   ├── scripts/
│   │   └── generate_data.py
│   ├── tests/
│   │   └── test_allocator.py
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── main.jsx
├── package.json
└── README.md

Prerequisites

Install Python and Node.js. npm is required to run the React dashboard.

Install pytest:

python -m pip install pytest

Generate the Dataset

From the project root, run:

python src/scripts/generate_data.py

The generator uses a fixed random seed to make data generation reproducible.

Run the Allocation Engine

python src/fulfillment/allocator.py

This generates the allocation results used by the dashboard and validation workflow.

Validate Allocation Results

Compare the generated allocation results against the ground-truth dataset. The current validation results are:

- Orders processed: 50,000
- Allocation result rows: 57,483
- Allocated lines: 57,065
- Unfulfillable lines: 418
- Status mismatches: 0
- Node mismatches: 0
- Carrier mismatches: 0

These counts describe the currently generated dataset and should be verified again after regenerating or changing the allocation logic.

Run Automated Tests

python -m pytest -v

The current automated test suite checks that the allocation results file exists, that allocation statuses are valid, and that every result has an order-line ID.

Run the Dashboard

Install dependencies:

npm install

Start the development server:

npm run dev

Open the local URL printed in the terminal, usually "http://localhost:5173".

The dashboard provides:

- Orders: Search and inspect order allocation details.
- Fulfillment Nodes: View fulfillment node information.
- Decisions: Review allocation decisions and exceptions.

The dashboard reads the CSV files from "public/data/". After regenerating the data or rerunning the allocator, copy the updated dashboard CSV files into that directory.

Reproducibility

The dataset generator uses seed "20261022". For repeatable validation, generate the dataset first, run the allocation engine, and compare its output against the ground truth. Then run the automated tests.

Current Test Status

The current automated test run completed with 3 passed. A pytest cache permission warning was also reported; it did not prevent the tests from passing.

Future Improvements

- Add tests for inventory limits, node capacity, and carrier selection.
- Validate split shipments and delivery-promise constraints.
- Add dashboard filters for allocation status and fulfillment node.
- Improve error handling and reporting for invalid or missing data.