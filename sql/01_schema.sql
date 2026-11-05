-- =====================================================================
-- Event Venue Analytics – PostgreSQL schema (3rd normal form)
-- Business context: a congress & event center rents rooms and sells
-- add-on services (catering, AV, security ...) to customers.
-- =====================================================================

DROP TABLE IF EXISTS event_services, event_rooms, events,
                     services, rooms, event_types, customers CASCADE;

-- Who books events
CREATE TABLE customers (
    customer_id    SERIAL PRIMARY KEY,
    company_name   VARCHAR(120) NOT NULL,
    industry       VARCHAR(60)  NOT NULL,
    customer_type  VARCHAR(20)  NOT NULL
                   CHECK (customer_type IN ('Corporate', 'Association', 'Public', 'Private')),
    city           VARCHAR(60)  NOT NULL
);

-- Kinds of events (lookup table)
CREATE TABLE event_types (
    event_type_id  SERIAL PRIMARY KEY,
    name           VARCHAR(40) NOT NULL UNIQUE
);

-- Rentable rooms / halls
CREATE TABLE rooms (
    room_id        SERIAL PRIMARY KEY,
    room_name      VARCHAR(60)  NOT NULL UNIQUE,
    capacity       INT          NOT NULL CHECK (capacity > 0),
    daily_rate_eur NUMERIC(10,2) NOT NULL CHECK (daily_rate_eur >= 0)
);

-- Sellable add-on services with list price and internal cost
CREATE TABLE services (
    service_id     SERIAL PRIMARY KEY,
    name           VARCHAR(60)  NOT NULL UNIQUE,
    unit           VARCHAR(20)  NOT NULL,            -- e.g. 'per person', 'per day'
    unit_price_eur NUMERIC(10,2) NOT NULL,
    unit_cost_eur  NUMERIC(10,2) NOT NULL
);

-- One row per booked event
CREATE TABLE events (
    event_id           SERIAL PRIMARY KEY,
    customer_id        INT  NOT NULL REFERENCES customers(customer_id),
    event_type_id      INT  NOT NULL REFERENCES event_types(event_type_id),
    event_name         VARCHAR(150) NOT NULL,
    booked_at          DATE NOT NULL,
    start_date         DATE NOT NULL,
    end_date           DATE NOT NULL,
    expected_attendees INT  NOT NULL CHECK (expected_attendees > 0),
    actual_attendees   INT,                          -- NULL if cancelled
    status             VARCHAR(12) NOT NULL CHECK (status IN ('completed', 'cancelled')),
    CHECK (end_date >= start_date),
    CHECK (booked_at <= start_date)
);

-- M:N  events <-> rooms  (an event can use several rooms)
CREATE TABLE event_rooms (
    event_id   INT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    room_id    INT NOT NULL REFERENCES rooms(room_id),
    days       INT NOT NULL CHECK (days > 0),
    price_eur  NUMERIC(12,2) NOT NULL,               -- price actually charged (after discount)
    PRIMARY KEY (event_id, room_id)
);

-- M:N  events <-> services
CREATE TABLE event_services (
    event_id       INT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    service_id     INT NOT NULL REFERENCES services(service_id),
    quantity       INT NOT NULL CHECK (quantity > 0),
    unit_price_eur NUMERIC(10,2) NOT NULL,           -- price at time of booking
    PRIMARY KEY (event_id, service_id)
);

-- Indexes for the most common filters / joins
CREATE INDEX idx_events_start   ON events(start_date);
CREATE INDEX idx_events_status  ON events(status);
CREATE INDEX idx_events_cust    ON events(customer_id);

-- Convenience view: one row per event with revenue, cost and margin
CREATE OR REPLACE VIEW v_event_financials AS
SELECT
    e.event_id,
    e.event_name,
    et.name                                   AS event_type,
    c.company_name,
    c.customer_type,
    e.booked_at,
    e.start_date,
    e.end_date,
    (e.start_date - e.booked_at)              AS lead_time_days,
    e.expected_attendees,
    e.actual_attendees,
    e.status,
    COALESCE(r.room_revenue, 0)               AS room_revenue,
    COALESCE(s.service_revenue, 0)            AS service_revenue,
    COALESCE(r.room_revenue, 0) + COALESCE(s.service_revenue, 0) AS total_revenue,
    COALESCE(s.service_cost, 0)               AS service_cost,
    COALESCE(r.room_revenue, 0) + COALESCE(s.service_revenue, 0)
        - COALESCE(s.service_cost, 0)         AS gross_margin
FROM events e
JOIN event_types et ON et.event_type_id = e.event_type_id
JOIN customers   c  ON c.customer_id    = e.customer_id
LEFT JOIN (
    SELECT event_id, SUM(price_eur) AS room_revenue
    FROM event_rooms GROUP BY event_id
) r ON r.event_id = e.event_id
LEFT JOIN (
    SELECT es.event_id,
           SUM(es.quantity * es.unit_price_eur) AS service_revenue,
           SUM(es.quantity * sv.unit_cost_eur)  AS service_cost
    FROM event_services es
    JOIN services sv ON sv.service_id = es.service_id
    GROUP BY es.event_id
) s ON s.event_id = e.event_id;
