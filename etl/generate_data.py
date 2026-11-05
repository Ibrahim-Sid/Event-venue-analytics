"""
Generate a SYNTHETIC dataset for a fictional congress & event center.

No real company data is used. The generator builds in realistic business
patterns (seasonality, a few big customers, lead-time effects on
cancellations, ...) so the analysis has something to find.

Usage:
    python etl/generate_data.py            # writes CSVs to data/raw/
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # reproducible output

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
START, END = date(2023, 1, 1), date(2025, 12, 31)

# ---------------------------------------------------------------- lookups
EVENT_TYPES = {
    # name: (share, attendees range, duration days range, services likelihood)
    "Congress":          (0.20, (300, 2500), (2, 4)),
    "Trade Fair":        (0.10, (800, 4000), (2, 5)),
    "Corporate Meeting": (0.35, (20, 250),   (1, 2)),
    "Gala / Dinner":     (0.15, (100, 800),  (1, 1)),
    "Concert":           (0.12, (500, 2200), (1, 1)),
    "Workshop":          (0.08, (10, 60),    (1, 2)),
}

ROOMS = [
    # name, capacity, daily rate (EUR)
    ("Grand Hall",        4500, 18000),
    ("Mozart Hall",       2300, 11000),
    ("Musensaal",         1200,  7000),
    ("Hall Bernstein",     700,  4200),
    ("Conference Room A",  250,  1500),
    ("Conference Room B",  250,  1500),
    ("Seminar Room 1",      60,   450),
    ("Seminar Room 2",      60,   450),
    ("Seminar Room 3",      40,   350),
    ("Foyer",              900,  2500),
]

SERVICES = [
    # name, unit, price, cost
    ("Catering Standard", "per person", 38.00, 24.00),
    ("Catering Premium",  "per person", 72.00, 41.00),
    ("Coffee Break",      "per person",  9.50,  4.00),
    ("AV Technology",     "per day",   1800.00, 950.00),
    ("Live Streaming",    "per day",   2600.00, 1700.00),
    ("Security Staff",    "per day",    900.00, 650.00),
    ("Cleaning",          "per day",    600.00, 420.00),
    ("Wardrobe Service",  "per day",    350.00, 200.00),
]

INDUSTRIES = ["Pharma", "Automotive", "Software", "Chemicals", "Banking",
              "Insurance", "Medical Association", "Music & Entertainment",
              "Public Sector", "Education", "Retail", "Energy"]
CITIES = ["Mannheim", "Heidelberg", "Ludwigshafen", "Frankfurt", "Stuttgart",
          "Karlsruhe", "Munich", "Cologne", "Berlin", "Darmstadt"]
NAME_PARTS_A = ["Rhein", "Neckar", "Kurpfalz", "Nova", "Alpha", "Blue",
                "Quadrat", "Delta", "Linden", "Orion", "Vektor", "Helios"]
NAME_PARTS_B = ["Pharma", "Solutions", "Systems", "Consulting", "Medical",
                "Group", "Analytics", "Energy", "Events", "Partners", "Labs"]
LEGAL = ["GmbH", "AG", "SE", "e.V.", "GmbH & Co. KG"]

# Seasonality: relative event demand per month (summer + Dec dip)
MONTH_WEIGHT = {1: 0.7, 2: 0.9, 3: 1.2, 4: 1.1, 5: 1.2, 6: 1.0,
                7: 0.6, 8: 0.4, 9: 1.3, 10: 1.4, 11: 1.3, 12: 0.8}


def make_customers(n=180):
    customers, used = [], set()
    for cid in range(1, n + 1):
        industry = random.choice(INDUSTRIES)
        city = random.choice(CITIES)
        if industry in ("Medical Association", "Education"):
            ctype = "Association"
        elif industry == "Public Sector":
            ctype = "Public"
        elif industry == "Music & Entertainment" or random.random() < 0.05:
            ctype = "Private"
        else:
            ctype = "Corporate"
        while True:
            a = random.choice(NAME_PARTS_A)
            if ctype == "Association":
                name = f"{a} {random.choice(['Gesellschaft', 'Verband', 'Forum', 'Akademie'])} e.V."
            elif ctype == "Public":
                name = f"{random.choice(['Stadt', 'Landkreis', 'Hochschule', 'Amt'])} {a}"
            elif ctype == "Private":
                name = f"{a} {random.choice(['Concerts', 'Live', 'Entertainment', 'Promotion'])} GmbH"
            else:
                name = f"{a} {random.choice(NAME_PARTS_B)} {random.choice(LEGAL)}"
            if name not in used:
                used.add(name)
                break
        customers.append((cid, name, industry, ctype, city))
    return customers


def random_start_date():
    """Pick a start date honouring monthly seasonality and growth over time."""
    while True:
        d = START + timedelta(days=random.randint(0, (END - START).days))
        growth = 1 + 0.12 * (d.year - START.year)           # ~12 % growth / year
        weekday_factor = 0.5 if d.weekday() == 6 else 1.0  # fewer Sunday starts
        if random.random() < MONTH_WEIGHT[d.month] * growth * weekday_factor / 1.8:
            return d


def pick_rooms(attendees, start, days, calendar):
    """Choose free rooms with enough total capacity. Returns list of room ids or None."""
    dates = [start + timedelta(days=i) for i in range(days)]
    free = [(i + 1, cap) for i, (_, cap, _) in enumerate(ROOMS)
            if all((i + 1, d) not in calendar for d in dates)]
    # smallest single room that fits
    random.shuffle(free)  # random tie-break between identical rooms
    fits = sorted([r for r in free if r[1] >= attendees], key=lambda r: r[1])
    if fits:
        chosen = [fits[0][0]]
    else:
        # combine biggest free rooms
        chosen, cap = [], 0
        for rid, c in sorted(free, key=lambda r: -r[1]):
            chosen.append(rid)
            cap += c
            if cap >= attendees:
                break
        if cap < attendees:
            return None
    # big events often use the foyer too
    if attendees > 600 and 10 not in chosen and all((10, d) not in calendar for d in dates) \
            and random.random() < 0.5:
        chosen.append(10)
    for rid in chosen:
        for d in dates:
            calendar.add((rid, d))
    return chosen


def main(n_events=1600):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    customers = make_customers()

    # Pareto: a handful of key accounts book much more often
    weights = [min(random.paretovariate(1.6), 12) for _ in customers]

    type_names = list(EVENT_TYPES)
    type_shares = [EVENT_TYPES[t][0] for t in type_names]

    events, event_rooms, event_services = [], [], []
    calendar = set()  # (room_id, date) already booked
    eid = 0

    attempts = 0
    while eid < n_events and attempts < n_events * 5:
        attempts += 1
        etype = random.choices(type_names, type_shares)[0]
        _, (amin, amax), (dmin, dmax) = EVENT_TYPES[etype]
        start = random_start_date()
        days = random.randint(dmin, dmax)
        end = start + timedelta(days=days - 1)
        if end > END:
            continue
        expected = random.randint(amin, amax)

        rooms = pick_rooms(expected, start, days, calendar)
        if rooms is None:
            continue

        # customer – concerts mostly private promoters / entertainment
        promoters = [c for c in customers if c[3] == "Private"]
        if etype == "Concert" and promoters and random.random() < 0.85:
            cust = random.choice(promoters)
        else:
            w = [0.05 if c[3] == "Private" else wt for c, wt in zip(customers, weights)]
            cust = random.choices(customers, w)[0]

        # lead time: big events are booked long in advance
        lead = int(random.gauss(240, 90)) if expected > 500 else int(random.gauss(70, 40))
        lead = max(7, lead)
        booked = start - timedelta(days=lead)

        # cancellations: more likely for long lead times and small corporate events
        p_cancel = 0.04 + (0.06 if lead > 180 else 0) + (0.05 if etype == "Corporate Meeting" else 0)
        if start.year == 2023 and start.month <= 3:
            p_cancel += 0.05  # post-pandemic uncertainty
        status = "cancelled" if random.random() < p_cancel else "completed"

        actual = None
        if status == "completed":
            # no-show rate: free events (associations/public) have more no-shows
            show_rate = random.uniform(0.70, 0.90) if cust[3] in ("Association", "Public") \
                else random.uniform(0.85, 1.0)
            actual = max(1, int(expected * show_rate))

        eid += 1
        year_tag = start.year
        events.append((eid, cust[0], type_names.index(etype) + 1,
                       f"{cust[1].split()[0]} {etype} {year_tag}",
                       booked.isoformat(), start.isoformat(), end.isoformat(),
                       expected, actual if actual is not None else "", status))

        if status == "cancelled":
            continue  # no revenue lines for cancelled events

        # room revenue (key accounts get a discount)
        discount = 0.10 if weights[cust[0] - 1] > 4 else 0.0
        for rid in rooms:
            rate = ROOMS[rid - 1][2]
            event_rooms.append((eid, rid, days, round(rate * days * (1 - discount), 2)))

        # services
        price_drift = 1 + 0.04 * (start.year - START.year)  # yearly price increase
        def add(sid, qty):
            event_services.append((eid, sid, qty, round(SERVICES[sid - 1][2] * price_drift, 2)))

        if etype in ("Gala / Dinner",) or (etype == "Congress" and random.random() < 0.5):
            add(2, actual)                                   # premium catering
        elif random.random() < 0.65:
            add(1, actual)                                   # standard catering
        if etype in ("Congress", "Corporate Meeting", "Workshop", "Trade Fair") and random.random() < 0.8:
            add(3, actual * days)                            # coffee breaks
        if random.random() < 0.75:
            add(4, days)                                     # AV
        if etype in ("Congress", "Corporate Meeting") and start.year >= 2024 and random.random() < 0.35:
            add(5, days)                                     # streaming grows from 2024
        if expected > 500:
            add(6, days)                                     # security
        add(7, days)                                         # cleaning always
        if start.month in (1, 2, 3, 10, 11, 12) and expected > 150 and random.random() < 0.7:
            add(8, days)                                     # wardrobe in cold months

    def write(name, header, rows):
        with open(OUT_DIR / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    write("customers.csv", ["customer_id", "company_name", "industry", "customer_type", "city"], customers)
    write("event_types.csv", ["event_type_id", "name"],
          [(i + 1, t) for i, t in enumerate(type_names)])
    write("rooms.csv", ["room_id", "room_name", "capacity", "daily_rate_eur"],
          [(i + 1, *r) for i, r in enumerate(ROOMS)])
    write("services.csv", ["service_id", "name", "unit", "unit_price_eur", "unit_cost_eur"],
          [(i + 1, *s) for i, s in enumerate(SERVICES)])
    write("events.csv", ["event_id", "customer_id", "event_type_id", "event_name", "booked_at",
                         "start_date", "end_date", "expected_attendees", "actual_attendees", "status"],
          events)
    write("event_rooms.csv", ["event_id", "room_id", "days", "price_eur"], event_rooms)
    write("event_services.csv", ["event_id", "service_id", "quantity", "unit_price_eur"], event_services)

    print(f"Wrote {len(events)} events, {len(event_rooms)} room bookings, "
          f"{len(event_services)} service lines to {OUT_DIR}")


if __name__ == "__main__":
    main()
