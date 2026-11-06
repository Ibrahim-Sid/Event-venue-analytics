# Power BI version

The same analysis as the Streamlit dashboard, built in Power BI as a **star-schema semantic model with DAX measures** and a two-page report.

It's saved as a [Power BI Project (`.pbip`)](https://learn.microsoft.com/power-bi/developer/projects/projects-overview): the model (TMDL) and the report are plain text files, so every change shows up as a readable diff on GitHub. For anyone without Power BI Desktop, there's a `.pbix` export in this folder and screenshots below.

| Page | Contents |
|---|---|
| **Overview** | KPI cards (revenue, gross margin, events, cancellation rate, show-up rate), year and event-type slicers, revenue by event type, monthly seasonality, room utilization, cancellation rate by booking lead time |
| **Customers & Services** | Customers ranked by revenue with revenue share, service attach rate, revenue per attendee by event type |

![Overview page](screenshots/overview.png)
![Customers & Services page](screenshots/customers.png)

## Data model

The source data is the CSVs from [`etl/generate_data.py`](../etl/generate_data.py), loaded with Power Query.

```
Customers ─┐
Event Types ┼─< Events >── Date
           │     │
           │     ├──< Event Rooms >── Rooms
           │     └──< Event Services >── Services
```

- **Events** is the central table, with one row per booking. Power Query adds `lead_time_days` and a sorted lead-time bucket.
- **Event Rooms** and **Event Services** hold the revenue lines. Power Query joins the service cost onto each service line, so revenue and cost come from simple `SUM`s.
- **Date** is generated in Power Query and marked as the date table, so time intelligence (`SAMEPERIODLASTYEAR`) works.
- All relationships are many-to-one with single-direction filtering. Slicers on dimensions filter `Events`, which then filters the revenue lines.
- Text is parsed with the `en-US` culture, so the model loads correctly on German-locale Windows. Otherwise `18000.00` would be read as 1,800,000.

## Key DAX measures

```dax
Revenue            = [Room Revenue] + [Service Revenue]
Gross Margin %     = DIVIDE([Gross Margin], [Revenue])
Revenue YoY %      = DIVIDE([Revenue] - [Revenue PY], [Revenue PY])
Revenue PY         = CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[Date]))
Revenue Share %    = DIVIDE([Revenue], CALCULATE([Revenue], ALL(Customers)))

Cancellation Rate  = DIVIDE(CALCULATE(COUNTROWS(Events), Events[status] = "cancelled"), [Bookings])
Show-up Rate       = DIVIDE(SUM(Events[actual_attendees]),
                            CALCULATE(SUM(Events[expected_attendees]), Events[status] = "completed"))
Room Utilization % = DIVIDE(SUM('Event Rooms'[days]), COUNTROWS('Date') * COUNTROWS(Rooms))
Service Attach Rate = DIVIDE(DISTINCTCOUNT('Event Services'[event_id]), [Events])
```

All 16 measures are in [`Events.tmdl`](EventVenueAnalytics.SemanticModel/definition/tables/Events.tmdl), grouped into *Finance* and *Operations* display folders.

## How to open it

Requires **Power BI Desktop** (free, Windows only).

1. Generate the data: `python etl/generate_data.py` (writes `data/raw/*.csv`).
2. Open `powerbi/EventVenueAnalytics.pbip` in Power BI Desktop.
3. **Home → Transform data → Edit parameters** and set `DataFolder` to the full path of your `data/raw` folder.
4. Click **Refresh**.

### Expected values (all years, no filters)

Use these to check that the model loaded correctly.

| Measure | Value |
|---|---|
| Revenue | € 74.56 M |
| Gross Margin % | 59.1 % |
| Events (completed) | 1,463 |
| Cancellation Rate | 8.6 % |
| Show-up Rate | 89.1 % |
| Revenue YoY % (2025 vs 2024) | +9.7 % |
| Room Utilization % – Foyer / Grand Hall / Seminar Room 1 | 44.6 % / 37.5 % / 9.7 % |
