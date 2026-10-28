import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def read_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")

    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def check(name, errors):
    if errors:
        print(f"FAIL - {name}: {len(errors)} issue(s)")
        for error in errors[:5]:
            print("  -", error)
    else:
        print(f"PASS - {name}")


def main():
    orders = read_csv("orders.csv")
    lines = read_csv("order_lines.csv")
    inventory = read_csv("inventory.csv")
    nodes = read_csv("fulfillment_nodes.csv")
    carriers = read_csv("carriers.csv")
    allocations = read_csv("allocation_results.csv")
    shipments = read_csv("shipments.csv")
    tracking = read_csv("tracking_events.csv")
    promises = read_csv("delivery_promises.csv")

    order_by_id = {o["order_id"]: o for o in orders}
    line_by_id = {x["order_line_id"]: x for x in lines}
    node_by_id = {n["node_id"]: n for n in nodes}
    carrier_by_id = {c["carrier_id"]: c for c in carriers}

    errors = []

    # 1. Promise must not be before the order was created.
    for promise in promises:
        promised = promise.get("promised_delivery_date", "")
        order = order_by_id.get(promise.get("order_id"))

        if promised and order:
            promised_date = datetime.fromisoformat(promised).date()
            order_date = datetime.fromisoformat(
                order["order_time"]
            ).date()

            if promised_date < order_date:
                errors.append(
                    f"{promise['promise_id']}: promise before order date"
                )

    check("Promise date vs order date", errors)

    # 2. Total allocated quantity must not exceed original stock.
    errors = []
    allocated_by_inventory = defaultdict(int)
    stock_by_key = {
        (item["node_id"], item["sku_id"]): int(item["stock"])
        for item in inventory
    }

    for allocation in allocations:
        if allocation.get("status") != "ALLOCATED":
            continue

        line = line_by_id.get(allocation.get("order_line_id"))
        node_id = allocation.get("node_id", "")

        if not line or not node_id:
            errors.append(
                f"Invalid line/node for {allocation.get('order_line_id')}"
            )
            continue

        key = (node_id, line["sku_id"])
        allocated_by_inventory[key] += int(line["quantity"])

    for key, quantity in allocated_by_inventory.items():
        available = stock_by_key.get(key)

        if available is None:
            errors.append(f"Inventory record missing for {key}")
        elif quantity > available:
            errors.append(
                f"{key}: allocated {quantity}, stock {available}"
            )

    check("Allocation does not exceed stock", errors)

    # 3. Selected carrier must support the destination zone.
    errors = []

    for allocation in allocations:
        if allocation.get("status") != "ALLOCATED":
            continue

        line_id = allocation.get("order_line_id")
        order = order_by_id.get(
            line_by_id.get(line_id, {}).get("order_id", "")
        )
        carrier = carrier_by_id.get(allocation.get("carrier_id", ""))

        if not order or not carrier:
            errors.append(f"Missing order/carrier for {line_id}")
            continue

        supported = [
            zone.strip()
            for zone in carrier["service_zones"].split(",")
        ]

        if order["destination_zone"] not in supported:
            errors.append(
                f"{line_id}: carrier does not support destination zone"
            )

    check("Carrier supports destination zone", errors)

    # 4. A shipment cannot be delivered before dispatch.
    errors = []
    shipment_by_id = {
        shipment["shipment_id"]: shipment for shipment in shipments
    }

    for event in tracking:
        if event.get("event_type") != "DELIVERED":
            continue

        shipment = shipment_by_id.get(event.get("shipment_id", ""))

        if not shipment:
            errors.append(
                f"Tracking event {event['tracking_event_id']} "
                "references missing shipment"
            )
            continue

        dispatch_time = datetime.fromisoformat(shipment["dispatch_time"])
        event_time = datetime.fromisoformat(event["event_time"])

        if event_time < dispatch_time:
            errors.append(
                f"{event['tracking_event_id']}: delivered before dispatch"
            )

    check("Delivered event occurs after dispatch", errors)

    # 5. Order status must agree with its allocation-line statuses.
    # This checks allocation roll-up, not delivery roll-up.
    errors = []
    allocation_by_order = defaultdict(list)

    for allocation in allocations:
        allocation_by_order[allocation["order_id"]].append(
            allocation["status"]
        )

    for order_id, statuses in allocation_by_order.items():
        order = order_by_id.get(order_id)
        if not order:
            errors.append(f"Allocation references missing order {order_id}")
            continue

        if all(status == "ALLOCATED" for status in statuses):
            expected = "ALLOCATED"
        elif all(status != "ALLOCATED" for status in statuses):
            expected = "UNFULFILLABLE"
        else:
            expected = "PARTIALLY_FULFILLED"

        if order["status"] != expected:
            errors.append(
                f"{order_id}: order status {order['status']}, "
                f"expected {expected}"
            )

    check("Order allocation status roll-up", errors)

    # Warehouse capacity validation.
    errors = []
    capacity_rows = read_csv("warehouse_capacity.csv")

    capacity_by_key = {
        (row["node_id"], row["capacity_date"]): int(row["daily_capacity"])
        for row in capacity_rows
    }

    used_by_key = defaultdict(int)

    for allocation in allocations:
        if allocation.get("status") != "ALLOCATED":
            continue

        line = line_by_id.get(allocation.get("order_line_id"))
        order = order_by_id.get(allocation.get("order_id"))
        node_id = allocation.get("node_id", "")

        if not line or not order or not node_id:
            continue

        # Capacity is reserved on the order's allocation date
        # in the current allocator implementation.
        capacity_date = datetime.fromisoformat(
            order["order_time"]
        ).date().isoformat()

        key = (node_id, capacity_date)
        used_by_key[key] += int(line["quantity"])

    for key, used in used_by_key.items():
        limit = capacity_by_key.get(key)

        if limit is None:
            errors.append(f"Missing capacity record for {key}")
        elif used > limit:
            errors.append(
                f"{key}: allocated capacity {used}, limit {limit}"
            )

    check("Warehouse daily capacity", errors)

    # Tracking events must follow a valid chronological lifecycle.
    errors = []

    allowed_order = {
        "ORDER_CREATED": 0,
        "PICKED": 1,
        "PACKED": 2,
        "DISPATCHED": 3,
        "IN_TRANSIT": 4,
        "OUT_FOR_DELIVERY": 5,
        "DELIVERED": 6,
    }

    events_by_shipment = defaultdict(list)

    for event in tracking:
        if event["event_type"] in allowed_order:
            events_by_shipment[event["shipment_id"]].append(event)

    for shipment_id, events in events_by_shipment.items():
        events.sort(key=lambda event: event["event_time"])
        previous_stage = -1
        previous_time = None

        for event in events:
            event_type = event["event_type"]
            event_time = datetime.fromisoformat(event["event_time"])
            stage = allowed_order[event_type]

            if previous_time and event_time < previous_time:
                errors.append(
                    f"{shipment_id}: event time moved backwards"
                )

            if stage < previous_stage:
                errors.append(
                    f"{shipment_id}: invalid lifecycle order at {event_type}"
                )

            previous_stage = stage
            previous_time = event_time

    check("Tracking lifecycle order", errors)

    # Basic foreign-key checks.
    errors = []

    for line in lines:
        if line["order_id"] not in order_by_id:
            errors.append(
                f"{line['order_line_id']}: missing parent order"
            )

    for shipment in shipments:
        if shipment["order_id"] not in order_by_id:
            errors.append(
                f"{shipment['shipment_id']}: missing parent order"
            )
        if shipment["node_id"] not in node_by_id:
            errors.append(
                f"{shipment['shipment_id']}: missing fulfillment node"
            )
        if shipment["carrier_id"] not in carrier_by_id:
            errors.append(
                f"{shipment['shipment_id']}: missing carrier"
            )

    check("Basic foreign-key integrity", errors)


if __name__ == "__main__":
    main()