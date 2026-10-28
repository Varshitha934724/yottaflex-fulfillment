import csv
import random
from pathlib import Path
from datetime import datetime, timedelta

SEED = 20261022
ORDER_COUNT = 50000
TRACKING_EVENT_COUNT = 100000

random.seed(SEED)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(filename, rows):
    if not rows:
        print(f"Skipped empty file: {filename}")
        return

    with open(DATA_DIR / filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def next_business_day(value, holiday_dates):
    while value.weekday() >= 5 or value.date().isoformat() in holiday_dates:
        value = (value + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
    return value


zones = ["South", "West", "North", "East"]

skus = [
    {
        "sku_id": f"SKU-{i:04d}",
        "name": f"Product {i}",
        "unit_weight_kg": random.randint(1, 10),
    }
    for i in range(1, 51)
]

nodes = [
    {
        "node_id": f"FUL-{i:03d}",
        "node_name": f"{zones[(i - 1) % 4]} Fulfillment Center {i}",
        "zone": zones[(i - 1) % 4],
        "daily_capacity": random.randint(500, 1500),
    }
    for i in range(1, 21)
]

inventory = [
    {
        "inventory_id": f"INV-{i:06d}",
        "node_id": node["node_id"],
        "sku_id": sku["sku_id"],
        "stock": random.randint(500, 800),
    }
    for i, (node, sku) in enumerate(
        ((n, s) for n in nodes for s in skus), start=1
    )
]

# Keep original inventory unchanged for the CSV output.
# Use a separate copy for allocation calculations.
inventory_state = [dict(item) for item in inventory]

inventory_lookup = {
    (item["node_id"], item["sku_id"]): item
    for item in inventory_state
}

carriers = [
    {
        "carrier_id": f"CAR-{i:03d}",
        "carrier_name": f"Carrier {i}",
        "cutoff_hour": random.choice([14, 16, 18]),
        "base_transit_days": random.randint(1, 4),
        "service_zones": random.choice([
            "South,West,North,East",
            "South,West",
            "North,East",
            "South,East",
            "West,North",
        ]),
    }
    for i in range(1, 11)
]

holidays = [
    {"holiday_date": "2026-10-02", "holiday_name": "Gandhi Jayanti"},
    {"holiday_date": "2026-10-20", "holiday_name": "Diwali"},
    {"holiday_date": "2026-10-21", "holiday_name": "Regional Holiday"},
    {"holiday_date": "2026-11-08", "holiday_name": "Regional Holiday"},
]

holiday_dates = {item["holiday_date"] for item in holidays}

start = datetime(2026, 10, 1, 9, 0)
end = datetime(2026, 10, 30, 23, 59)

capacity_rows = []

for node in nodes:
    day = start.date()
    while day <= end.date():
        capacity_rows.append({
            "capacity_id": f"CAP-{node['node_id']}-{day.isoformat()}",
            "node_id": node["node_id"],
            "capacity_date": day.isoformat(),
            "daily_capacity": node["daily_capacity"],
            "used_capacity": 0,
        })
        day += timedelta(days=1)

capacity_lookup = {
    (row["node_id"], row["capacity_date"]): row
    for row in capacity_rows
}

orders = []
lines = []
shipments = []
tracking = []
promises = []
ground_truth = []

for i in range(1, ORDER_COUNT + 1):
    order_id = f"ORD-2026-{i:06d}"

    created = start + timedelta(
        minutes=random.randint(
            0, int((end - start).total_seconds() // 60)
        )
    )

    zone = random.choice(zones)
    line_count = 2 if random.random() < 0.15 else 1
    order_skus = random.sample(skus, line_count)

    orders.append({
        "order_id": order_id,
        "order_time": created.isoformat(),
        "destination_zone": zone,
        "status": "CREATED",
    })

    order_promises = []
    allocated_count = 0

    for line_no, sku in enumerate(order_skus, start=1):
        qty = random.randint(1, 15)

        line = {
            "order_line_id": f"LINE-{i:06d}-{line_no:02d}",
            "order_id": order_id,
            "sku_id": sku["sku_id"],
            "quantity": qty,
        }
        lines.append(line)

        candidates = []

        for node in nodes:
            if node["zone"] != zone:
                continue

            inv = inventory_lookup[(node["node_id"], sku["sku_id"])]
            cap = capacity_lookup.get(
                (node["node_id"], created.date().isoformat())
            )

            if (
                cap
                and int(inv["stock"]) >= qty
                and cap["used_capacity"] + qty <= cap["daily_capacity"]
            ):
                candidates.append((cap["used_capacity"], node, inv, cap))

        candidates.sort(key=lambda item: (item[0], item[1]["node_id"]))

        if not candidates:
            order_promises.append({
                "promise_id": f"PROM-{order_id}-{line_no:02d}",
                "order_id": order_id,
                "promised_delivery_date": "",
                "ground_truth": "UNFULFILLABLE",
            })

            ground_truth.append({
                "order_id": order_id,
                "order_line_id": line["order_line_id"],
                "allocation_status": "UNFULFILLABLE",
                "selected_node_id": "",
                "selected_carrier_id": "",
                "expected_delivery_date": "",
            })
            continue

        _, selected, inv, cap = candidates[0]

        # Reserve stock and warehouse capacity.
        inv["stock"] = int(inv["stock"]) - qty
        cap["used_capacity"] += qty

        eligible_carriers = [
            carrier for carrier in carriers
            if zone in [z.strip() for z in carrier["service_zones"].split(",")]
        ]

        if not eligible_carriers:
            ground_truth.append({
                "order_id": order_id,
                "order_line_id": line["order_line_id"],
                "allocation_status": "UNFULFILLABLE",
                "selected_node_id": "",
                "selected_carrier_id": "",
                "expected_delivery_date": "",
            })
            continue

        carrier = min(
            eligible_carriers,
            key=lambda item: (
                int(item["base_transit_days"]),
                int(item["cutoff_hour"]),
                item["carrier_id"],
            ),
        )

        dispatch = created + timedelta(hours=2)
        dispatch = dispatch.replace(minute=0, second=0, microsecond=0)

        if dispatch.hour >= int(carrier["cutoff_hour"]):
            dispatch = (dispatch + timedelta(days=1)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        dispatch = next_business_day(dispatch, holiday_dates)

        promised = dispatch + timedelta(
            days=int(carrier["base_transit_days"])
        )
        promised = next_business_day(promised, holiday_dates)

        shipment_id = f"SHP-{i:06d}-{line_no:02d}"

        shipments.append({
            "shipment_id": shipment_id,
            "order_id": order_id,
            "order_line_id": line["order_line_id"],
            "node_id": selected["node_id"],
            "carrier_id": carrier["carrier_id"],
            "sku_id": sku["sku_id"],
            "quantity": qty,
            "dispatch_time": dispatch.isoformat(),
        })

        order_promises.append({
            "promise_id": f"PROM-{order_id}-{line_no:02d}",
            "order_id": order_id,
            "promised_delivery_date": promised.date().isoformat(),
            "ground_truth": "BASELINE",
        })

        ground_truth.append({
            "order_id": order_id,
            "order_line_id": line["order_line_id"],
            "allocation_status": "ALLOCATED",
            "selected_node_id": selected["node_id"],
            "selected_carrier_id": carrier["carrier_id"],
            "expected_delivery_date": promised.date().isoformat(),
        })

        allocated_count += 1

    promises.extend(order_promises)

    if allocated_count == 0:
        orders[-1]["status"] = "UNFULFILLABLE"
    elif allocated_count < line_count:
        orders[-1]["status"] = "PARTIALLY_FULFILLED"
    else:
        orders[-1]["status"] = "ALLOCATED"

event_types = [
    "ORDER_CREATED",
    "PICKED",
    "PACKED",
    "DISPATCHED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "DELAYED",
]

if not shipments:
    raise RuntimeError("No shipments generated.")

for event_no in range(1, TRACKING_EVENT_COUNT + 1):
    shipment = shipments[(event_no - 1) % len(shipments)]
    event_type = event_types[(event_no - 1) % len(event_types)]

    dispatch_time = datetime.fromisoformat(shipment["dispatch_time"])
    event_time = dispatch_time + timedelta(hours=(event_no % 120))

    tracking.append({
        "tracking_event_id": f"TRK-{event_no:06d}",
        "shipment_id": shipment["shipment_id"],
        "event_type": event_type,
        "event_time": event_time.isoformat(),
        "is_anomaly": "TRUE" if random.random() < 0.02 else "FALSE",
    })

write_csv("orders.csv", orders)
write_csv("order_lines.csv", lines)
write_csv("skus.csv", skus)
write_csv("fulfillment_nodes.csv", nodes)
write_csv("inventory.csv", inventory)
write_csv("carriers.csv", carriers)
write_csv("warehouse_capacity.csv", capacity_rows)
write_csv("holidays.csv", holidays)
write_csv("shipments.csv", shipments)
write_csv("tracking_events.csv", tracking)
write_csv("delivery_promises.csv", promises)
write_csv("ground_truth.csv", ground_truth)

print(f"Generated {len(orders)} orders using seed {SEED}")
print(f"Generated {len(lines)} order lines")
print(f"Generated {len(nodes)} fulfillment nodes")
print(f"Generated {len(inventory)} inventory rows")
print(f"Generated {len(shipments)} shipments")
print(f"Generated {len(tracking)} tracking events")
print(f"Generated {len(ground_truth)} ground-truth rows")
print(f"Output directory: {DATA_DIR}")