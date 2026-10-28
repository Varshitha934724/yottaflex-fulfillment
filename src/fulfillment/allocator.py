import csv
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def read_csv(filename):
    with open(DATA_DIR / filename, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(filename, rows, fields):
    with open(DATA_DIR / filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def next_business_day(date_time, holiday_dates):
    while (
        date_time.weekday() >= 5
        or date_time.date().isoformat() in holiday_dates
    ):
        date_time += timedelta(days=1)
        date_time = date_time.replace(
            hour=9, minute=0, second=0, microsecond=0
        )
    return date_time


def allocate_order(
    order,
    order_lines,
    inventory_lookup,
    nodes,
    carriers_by_zone,
    capacity_lookup,
    holiday_dates,
):
    zone = order["destination_zone"]
    created = datetime.fromisoformat(order["order_time"])
    results = []

    eligible_carriers = carriers_by_zone.get(zone, [])

    # Don't reserve stock or capacity when no carrier can serve the zone.
    if not eligible_carriers:
        for line in order_lines:
            results.append({
                "order_id": order["order_id"],
                "order_line_id": line["order_line_id"],
                "status": "NO_CARRIER",
                "node_id": "",
                "carrier_id": "",
                "promised_delivery_date": "",
            })
        return results

    # Prefer carriers with shorter transit times.
    carrier = min(
        eligible_carriers,
        key=lambda item: (
            int(item["base_transit_days"]),
            int(item["cutoff_hour"]),
            item["carrier_id"],
        ),
    )

    dispatch = created + timedelta(hours=2)

    if dispatch.hour >= int(carrier["cutoff_hour"]):
        dispatch = (dispatch + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

    dispatch = next_business_day(dispatch, holiday_dates)

    delivery = dispatch + timedelta(days=int(carrier["base_transit_days"]))
    delivery = next_business_day(delivery, holiday_dates)

    for line in order_lines:
        sku_id = line["sku_id"]
        qty = int(line["quantity"])
        selected = None

        # Find nodes in the destination zone with enough stock and capacity.
        candidates = []

        for node in nodes:
            if node["zone"] != zone:
                continue

            inv = inventory_lookup.get((node["node_id"], sku_id))
            cap = capacity_lookup.get(
                (node["node_id"], created.date().isoformat())
            )

            if inv is None or cap is None:
                continue

            available_stock = int(inv["stock"])
            available_capacity = (
                int(cap["daily_capacity"]) - int(cap["used_capacity"])
            )

            if available_stock >= qty and available_capacity >= qty:
                candidates.append((
                    available_stock,
                    available_capacity,
                    node,
                    inv,
                    cap,
                ))

        # Choose the node with the least used capacity first.
        candidates.sort(
            key=lambda item: (
                int(item[4]["used_capacity"]),
                item[2]["node_id"],
            )
        )
        if candidates:
            _, _, selected, inv, cap = candidates[0]

            # Reserve inventory and capacity only after a valid node is found.
            inv["stock"] = str(int(inv["stock"]) - qty)
            cap["used_capacity"] = str(int(cap["used_capacity"]) + qty)

            results.append({
                "order_id": order["order_id"],
                "order_line_id": line["order_line_id"],
                "status": "ALLOCATED",
                "node_id": selected["node_id"],
                "carrier_id": carrier["carrier_id"],
                "promised_delivery_date": delivery.date().isoformat(),
            })
        else:
            results.append({
                "order_id": order["order_id"],
                "order_line_id": line["order_line_id"],
                "status": "UNFULFILLABLE",
                "node_id": "",
                "carrier_id": "",
                "promised_delivery_date": "",
            })

    return results


def main():
    orders = read_csv("orders.csv")
    lines = read_csv("order_lines.csv")
    inventory = read_csv("inventory.csv")
    nodes = read_csv("fulfillment_nodes.csv")
    carriers = read_csv("carriers.csv")
    capacity = read_csv("warehouse_capacity.csv")
    holidays = read_csv("holidays.csv")

    # Fast inventory lookup.
    inventory_lookup = {
        (item["node_id"], item["sku_id"]): item
        for item in inventory
    }

    # Fast capacity lookup.
    for item in capacity:
        item["used_capacity"] = "0"

    capacity_lookup = {
        (item["node_id"], item["capacity_date"]): item
        for item in capacity
    }

    # Group order lines by order ID.
    by_order = {}
    for line in lines:
        by_order.setdefault(line["order_id"], []).append(line)

    # Group carriers by supported destination zone.
    carriers_by_zone = {zone: [] for zone in ["South", "West", "North", "East"]}

    for carrier in carriers:
        supported_zones = carrier["service_zones"].split(",")

        for zone in supported_zones:
            zone = zone.strip()
            if zone in carriers_by_zone:
                carriers_by_zone[zone].append(carrier)

    holiday_dates = {item["holiday_date"] for item in holidays}

    results = []

    # Deterministic order of processing.
    for order in orders:
        order_lines = by_order.get(order["order_id"], [])

        results.extend(
            allocate_order(
                order,
                order_lines,
                inventory_lookup,
                nodes,
                carriers_by_zone,
                capacity_lookup,
                holiday_dates,
            )
        )

    fields = [
        "order_id",
        "order_line_id",
        "status",
        "node_id",
        "carrier_id",
        "promised_delivery_date",
    ]

    write_csv("allocation_results.csv", results, fields)

    # Print summary.
    status_counts = {}
    for result in results:
        status_counts[result["status"]] = (
            status_counts.get(result["status"], 0) + 1
        )

    print("Processed orders:", len(orders))
    print("Allocation results:", len(results))
    print("Statuses:")

    for status in sorted(status_counts):
        print(f"  {status}: {status_counts[status]}")

    print("Results saved to:", DATA_DIR / "allocation_results.csv")


if __name__ == "__main__":
    main()