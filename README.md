# YottaFlex Fulfillment Planning System

## Overview

This project implements a fulfillment planning system that allocates order lines to fulfillment nodes based on inventory availability, warehouse capacity, and carrier selection rules.

It includes a synthetic dataset generator, a Python allocation engine, validation checks, automated tests, and a React dashboard.

## Key Features

- Reproducible synthetic data using seed `20261022`
- 50,000 orders and 57,483 order lines
- 20 fulfillment nodes and 10 carriers
- 100,000 tracking events
- Allocation and unfulfillable-line detection
- Ground-truth comparison
- Interactive React dashboard

## Technology Stack

- Python
- pytest
- React
- Vite
- JavaScript
- CSV

## Project Structure

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

## Setup and Execution

### 1. Install Dependencies

    python -m pip install pytest
    npm install

### 2. Generate Dataset

    python src/scripts/generate_data.py

### 3. Run Allocation Engine

    python src/fulfillment/allocator.py

### 4. Validate Results

    python src/scripts/validate.py

### 5. Run Tests

    python -m pytest -v -p no:cacheprovider

### 6. Start Dashboard

    npm run dev

Open the local URL displayed in the terminal, usually `http://localhost:5173`.

## Current Results

| Metric | Result |
|---|---:|
| Orders Processed | 50,000 |
| Order Lines | 57,483 |
| Allocated Lines | 57,065 |
| Unfulfillable Lines | 418 |
| Tests Passed | 3 |

## Dashboard Features

- **Orders:** Search and inspect order allocation details.
- **Fulfillment Nodes:** View node information.
- **Decisions:** Review allocation decisions and exceptions.

The dashboard reads CSV files from `public/data/`.

## Reproducibility

The generator uses the fixed seed `20261022`. Regenerate the dataset, run the allocation engine, and execute validation and tests to reproduce the workflow.

## Validation

The validation script checks allocation constraints, carrier-zone compatibility, tracking-event ordering, warehouse capacity, allocation status, and basic foreign-key integrity.

## Future Improvements

- Expand inventory and capacity tests.
- Strengthen split-shipment and delivery-status validation.
- Improve carrier service-level and delivery-promise checks.
- Add dashboard filters and better error reporting.

## Documentation

- `DATA_DICTIONARY.md` — dataset field definitions.
- `PROMPT_HISTORY.md` — AI assistance and prompt history.
