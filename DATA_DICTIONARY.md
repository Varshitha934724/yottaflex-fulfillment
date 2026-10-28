Data Dictionary

1. Order

- Primary key: "order_id"
- Fields: "order_id" (string, required, unique), "order_date" (datetime), "customer_id" (string), "destination_zone" (string), "order_status" (string).
- Validation: Order IDs must be unique; order dates must be valid.

2. OrderLine

- Primary key: "order_line_id"
- Foreign key: "order_id" references Order.
- Fields: "order_line_id" (string, required, unique), "order_id" (string, required), "sku_id" (string, required), "quantity" (integer, positive).
- Validation: Each line must reference an existing order and SKU.

3. SKU

- Primary key: "sku_id"
- Fields: "sku_id" (string, unique), product attributes and weight where available.
- Validation: SKU identifiers must be unique.

4. FulfillmentNode

- Primary key: "node_id"
- Fields: "node_id" (string, unique), "node_name" (string), "zone" (string), "daily_capacity" (integer, positive).
- Validation: Capacity must be non-negative and node IDs must be unique.

5. Inventory

- Primary key: Composite key "(node_id, sku_id)"
- Foreign keys: "node_id" references FulfillmentNode; "sku_id" references SKU.
- Fields: "node_id", "sku_id", "quantity" or the stock quantity field in the source CSV.
- Validation: Stock quantities must be non-negative.

6. WarehouseCapacity

- Primary key: Composite key "(node_id, date)"
- Foreign key: "node_id" references FulfillmentNode.
- Fields: Node, date, and capacity usage fields from the source CSV.
- Validation: Capacity usage must not exceed the defined limit.

7. Carrier

- Primary key: "carrier_id"
- Fields: "carrier_id" (string, unique), carrier attributes and supported services from the source CSV.
- Validation: Carrier IDs must be unique.

8. ServiceLevel

- Primary key: Use the service-level identifier defined in the source data.
- Fields: Service name, transit-time rules, and applicable service zones where available.
- Validation: A service must be supported by the selected carrier and destination zone.

9. Shipment

- Primary key: "shipment_id"
- Foreign keys: References to the associated order line, fulfillment node, and carrier.
- Fields: Shipment identifier, dispatch date, delivery date, and shipment status as available.
- Validation: Shipment IDs must be unique; delivery must not precede dispatch.

10. TrackingEvent

- Primary key: "tracking_event_id"
- Foreign key: "shipment_id" references Shipment.
- Fields: Event identifier, shipment identifier, event timestamp, and event status.
- Validation: Events must reference valid shipments and follow valid lifecycle ordering.

11. DeliveryPromise

- Primary key: Use the promise identifier defined in the source data.
- Foreign keys: References the associated order or order line.
- Fields: Promise date and promise status as available.
- Validation: Promise dates must follow the documented cutoff, calendar, carrier, and service-level rules.

Relationships and Cardinality

- Order → OrderLine: one-to-many.
- SKU → OrderLine: one-to-many.
- FulfillmentNode → Inventory: one-to-many.
- SKU → Inventory: one-to-many.
- FulfillmentNode → WarehouseCapacity: one-to-many.
- Carrier → Shipment: one-to-many.
- Shipment → TrackingEvent: one-to-many.
- Order or OrderLine → DeliveryPromise: one-to-many or one-to-one depending on the implemented model.

Important Note

This is a preliminary data dictionary. Verify field names, types, primary keys, foreign keys, allowed values, units, optional fields, and effective dates against the actual CSV headers and implementation before submission. Do not claim a validation rule is enforced unless it is implemented and tested.