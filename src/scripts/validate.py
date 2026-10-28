import csv
from pathlib import Path
from collections import defaultdict, Counter
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


def parse_date(value):
    return datetime.fromisoformat(value).date()


def parse_datetime(value):
    return datetime.fromisoformat(value)


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
    capacity_rows = read_csv("warehouse_capacity.csv")

    order_by_id = {o["order_id"]: o for o in orders}
    line_by_id = {x["order_line_id"]: x for x in lines}
    node_by_id = {n["node_id"]: n for n in nodes}
    carrier_by_id = {c["carrier_id"]: c for c in carriers}
    shipment_by_id = {s["shipment_id"]: s for s in shipments}

    # 1. Promise dates must not precede order dates.
    errors = []

    for promise in promises:
        promised = promise.get("promised_delivery_date", "")
        order = order_by_id.get(promise.get("order_id"))

        if not order:
            errors.append(
                f"{promise.get('promise_id')}: missing parent order"
            )
            continue

        if promised and parse_date(promised) < parse_date(order["order_time"]):
            errors.append(
                f"{promise.get('promise_id')}: promise before order date"
            )

    check("Promise date vs order date", errors)

    # 2. Total allocation must not exceed available inventory.
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
        line = line_by_id.get(line_id)
        order = order_by_id.get(line.get("order_id", "")) if line else None
        carrier = carrier_by_id.get(allocation.get("carrier_id", ""))

        if not order or not carrier:
            errors.append(f"Missing order/carrier for {line_id}")
            continue

        supported = [
            zone.strip()
            for zone in carrier.get("service_zones", "").split(",")
        ]

        if order["destination_zone"] not in supported:
            errors.append(
                f"{line_id}: carrier does not support destination zone"
            )

    check("Carrier supports destination zone", errors)

    # 4. Delivered events must not occur before dispatch.
    errors = []

    for event in tracking:
        if event.get("event_type") != "DELIVERED":
            continue

        shipment = shipment_by_id.get(event.get("shipment_id", ""))

        if not shipment:
            errors.append(
                f"{event.get('tracking_event_id')}: missing shipment"
            )
            continue

        dispatch_time = parse_datetime(shipment["dispatch_time"])
        event_time = parse_datetime(event["event_time"])

        if event_time < dispatch_time:
            errors.append(
                f"{event['tracking_event_id']}: delivered before dispatch"
            )

    check("Delivered event occurs after dispatch", errors)

    # 5. Order allocation status must match its line allocation statuses.
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
                f"{order_id}: actual {order['status']}, expected {expected}"
            )

    check("Order allocation status roll-up", errors)

    # 6. Warehouse daily capacity.
    errors = []

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
            errors.append(
                f"Invalid allocation references for {allocation.get('order_line_id')}"
            )
            continue

        capacity_date = parse_date(order["order_time"]).isoformat()
        used_by_key[(node_id, capacity_date)] += int(line["quantity"])

    for key, used in used_by_key.items():
        limit = capacity_by_key.get(key)

        if limit is None:
            errors.append(f"Missing capacity record for {key}")
        elif used > limit:
            errors.append(
                f"{key}: allocated capacity {used}, limit {limit}"
            )

    check("Warehouse daily capacity", errors)

    # 7. Tracking lifecycle chronology and valid stage order.
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
        shipment_id = event.get("shipment_id", "")

        if shipment_id not in shipment_by_id:
            errors.append(
                f"{event.get('tracking_event_id')}: missing shipment"
            )
            continue

        event_type = event.get("event_type", "")

        if event_type not in allowed_order:
            errors.append(
                f"{event.get('tracking_event_id')}: unknown event {event_type}"
            )
            continue

        events_by_shipment[shipment_id].append(event)

    for shipment in shipments:
        shipment_id = shipment["shipment_id"]
        events = events_by_shipment.get(shipment_id, [])

        if not events:
            errors.append(f"{shipment_id}: no tracking events")
            continue

        events.sort(key=lambda event: parse_datetime(event["event_time"]))
        previous_stage = -1
        previous_time = None

        for event in events:
            event_type = event["event_type"]
            event_time = parse_datetime(event["event_time"])
            stage = allowed_order[event_type]

            if previous_time and event_time < previous_time:
                errors.append(f"{shipment_id}: event time moved backwards")

            if stage < previous_stage:
                errors.append(
                    f"{shipment_id}: invalid lifecycle order at {event_type}"
                )

            previous_stage = stage
            previous_time = event_time

    check("Tracking lifecycle order and coverage", errors)

    # 8. Derive order delivery status from all its shipments.
    errors = []
    delivery_by_shipment = defaultdict(list)
    shipments_by_order = defaultdict(list)

    for event in tracking:
        delivery_by_shipment[event["shipment_id"]].append(event)

    for shipment in shipments:
        shipments_by_order[shipment["order_id"]].append(
            shipment["shipment_id"]
        )

    order_delivery_status = {}

    for order in orders:
        order_id = order["order_id"]
        order_shipments = shipments_by_order.get(order_id, [])

        if not order_shipments:
            status = "NOT_DISPATCHED"
        else:
            delivered_count = 0
            dispatched_count = 0

            for shipment_id in order_shipments:
                event_types = {
                    event["event_type"]
                    for event in delivery_by_shipment.get(shipment_id, [])
                }

                if "DISPATCHED" in event_types:
                    dispatched_count += 1

                if "DELIVERED" in event_types:
                    delivered_count += 1

            if delivered_count == len(order_shipments):
                status = "DELIVERED"
            elif delivered_count > 0:
                status = "PARTIALLY_DELIVERED"
            elif dispatched_count > 0:
                status = "IN_TRANSIT"
            else:
                status = "NOT_DISPATCHED"

        order_delivery_status[order_id] = status

    print("Order delivery status roll-up:")
    for status, count in sorted(Counter(order_delivery_status.values()).items()):
        print(f"  {status}: {count}")

    # Confirm every order is included in the derived status summary.
    if len(order_delivery_status) != len(orders):
        errors.append(
            f"Expected {len(orders)} orders, got {len(order_delivery_status)} statuses"
        )

    check("Order delivery status roll-up coverage", errors)

    # 9. Basic foreign-key integrity.
    errors = []

    for line in lines:
        if line["order_id"] not in order_by_id:
            errors.append(f"{line['order_line_id']}: missing parent order")

    for shipment in shipments:
        if shipment["order_id"] not in order_by_id:
            errors.append(f"{shipment['shipment_id']}: missing parent order")

        if shipment["node_id"] not in node_by_id:
            errors.append(f"{shipment['shipment_id']}: missing fulfillment node")

        if shipment["carrier_id"] not in carrier_by_id:
            errors.append(f"{shipment['shipment_id']}: missing carrier")

        if shipment.get("order_line_id") not in line_by_id:
            errors.append(f"{shipment['shipment_id']}: missing order line")

    check("Basic foreign-key integrity", errors)

    # 10. Compare allocation results with ground truth.
    errors = []
    ground_truth = read_csv("ground_truth.csv")

    allocation_by_line = {
        row["order_line_id"]: row
        for row in allocations
    }

    for expected in ground_truth:
        line_id = expected["order_line_id"]
        actual = allocation_by_line.get(line_id)

        if actual is None:
            errors.append(f"{line_id}: missing allocation result")
            continue

        if actual["status"] != expected["allocation_status"]:
            errors.append(
                f"{line_id}: status {actual['status']}, "
                f"expected {expected['allocation_status']}"
            )

        expected_node = expected.get("selected_node_id", "")
        actual_node = actual.get("node_id", "")

        if expected_node and actual_node != expected_node:
            errors.append(
                f"{line_id}: node {actual_node}, expected {expected_node}"
            )

        expected_carrier = expected.get("selected_carrier_id", "")
        actual_carrier = actual.get("carrier_id", "")

        if expected_carrier and actual_carrier != expected_carrier:
            errors.append(
                f"{line_id}: carrier {actual_carrier}, "
                f"expected {expected_carrier}"
            )

    check("Allocation results vs ground truth", errors)


if __name__ == "__main__":
    main()