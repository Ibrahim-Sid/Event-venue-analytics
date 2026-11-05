# ER Diagram

GitHub renders this Mermaid diagram automatically.

```mermaid
erDiagram
    CUSTOMERS ||--o{ EVENTS : books
    EVENT_TYPES ||--o{ EVENTS : classifies
    EVENTS ||--o{ EVENT_ROOMS : uses
    ROOMS ||--o{ EVENT_ROOMS : "is booked in"
    EVENTS ||--o{ EVENT_SERVICES : orders
    SERVICES ||--o{ EVENT_SERVICES : "is sold in"

    CUSTOMERS {
        int customer_id PK
        varchar company_name
        varchar industry
        varchar customer_type
        varchar city
    }
    EVENT_TYPES {
        int event_type_id PK
        varchar name
    }
    EVENTS {
        int event_id PK
        int customer_id FK
        int event_type_id FK
        varchar event_name
        date booked_at
        date start_date
        date end_date
        int expected_attendees
        int actual_attendees
        varchar status
    }
    ROOMS {
        int room_id PK
        varchar room_name
        int capacity
        numeric daily_rate_eur
    }
    EVENT_ROOMS {
        int event_id PK,FK
        int room_id PK,FK
        int days
        numeric price_eur
    }
    SERVICES {
        int service_id PK
        varchar name
        varchar unit
        numeric unit_price_eur
        numeric unit_cost_eur
    }
    EVENT_SERVICES {
        int event_id PK,FK
        int service_id PK,FK
        int quantity
        numeric unit_price_eur
    }
```

## Design decisions

- **3rd normal form.** Event types, rooms and services are separate lookup tables, so a name or price lives in exactly one place.
- **Two bridge tables (M:N).** An event can use several rooms (`event_rooms`) and order several services (`event_services`).
- **Historical prices are stored in the bridge tables.** `event_services.unit_price_eur` keeps the price *at booking time*, so a later price increase in `services` doesn't change past revenue.
- **Constraints in the database, not just in code.** `CHECK` constraints stop impossible data (end before start, negative capacity, unknown status).
- **A view for reporting.** `v_event_financials` hides the joins, so the analysis queries and the dashboard stay simple.
