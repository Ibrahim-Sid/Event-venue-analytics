-- =====================================================================
-- Business questions answered in SQL
-- Run in psql:  \i sql/02_analysis.sql
-- =====================================================================


-- Q1  Which event types bring the most revenue and margin?
SELECT event_type,
       COUNT(*)                                        AS events,
       ROUND(SUM(total_revenue))                       AS revenue_eur,
       ROUND(SUM(gross_margin) / NULLIF(SUM(total_revenue), 0) * 100, 1) AS margin_pct,
       ROUND(AVG(total_revenue))                       AS avg_revenue_per_event
FROM v_event_financials
WHERE status = 'completed'
GROUP BY event_type
ORDER BY revenue_eur DESC;


-- Q2  How does revenue develop per year? (growth with window function LAG)
WITH yearly AS (
    SELECT EXTRACT(YEAR FROM start_date)::int AS year,
           SUM(total_revenue)                 AS revenue
    FROM v_event_financials
    WHERE status = 'completed'
    GROUP BY 1
)
SELECT year,
       ROUND(revenue)                                                    AS revenue_eur,
       ROUND((revenue / LAG(revenue) OVER (ORDER BY year) - 1) * 100, 1) AS yoy_growth_pct
FROM yearly
ORDER BY year;


-- Q3  Seasonality: which months are weak?
SELECT EXTRACT(MONTH FROM start_date)::int AS month,
       COUNT(*)                            AS events,
       ROUND(SUM(total_revenue) / COUNT(DISTINCT EXTRACT(YEAR FROM start_date))) AS avg_revenue_per_year
FROM v_event_financials
WHERE status = 'completed'
GROUP BY 1
ORDER BY 1;


-- Q4  Room utilization: share of days each room was booked (2025)
WITH booked_days AS (
    SELECT er.room_id, SUM(er.days) AS days_booked
    FROM event_rooms er
    JOIN events e ON e.event_id = er.event_id
    WHERE EXTRACT(YEAR FROM e.start_date) = 2025
    GROUP BY er.room_id
)
SELECT r.room_name,
       r.capacity,
       COALESCE(b.days_booked, 0)                         AS days_booked,
       ROUND(COALESCE(b.days_booked, 0) / 365.0 * 100, 1) AS utilization_pct
FROM rooms r
LEFT JOIN booked_days b ON b.room_id = r.room_id
ORDER BY utilization_pct DESC;


-- Q5  Customer concentration (Pareto): how much revenue do the top 10 % of customers bring?
WITH cust AS (
    SELECT company_name, SUM(total_revenue) AS revenue
    FROM v_event_financials
    WHERE status = 'completed'
    GROUP BY company_name
),
ranked AS (
    SELECT company_name, revenue,
           NTILE(10) OVER (ORDER BY revenue DESC) AS decile
    FROM cust
)
SELECT decile,
       COUNT(*)                                                     AS customers,
       ROUND(SUM(revenue))                                          AS revenue_eur,
       ROUND(SUM(revenue) / SUM(SUM(revenue)) OVER () * 100, 1)     AS share_pct
FROM ranked
GROUP BY decile
ORDER BY decile;


-- Q6  Top 10 customers with their rank and favourite event type
WITH cust AS (
    SELECT company_name, customer_type,
           COUNT(*)            AS events,
           SUM(total_revenue)  AS revenue,
           MODE() WITHIN GROUP (ORDER BY event_type) AS main_event_type
    FROM v_event_financials
    WHERE status = 'completed'
    GROUP BY company_name, customer_type
)
SELECT RANK() OVER (ORDER BY revenue DESC) AS rank,
       company_name, customer_type, events, main_event_type,
       ROUND(revenue) AS revenue_eur
FROM cust
ORDER BY rank
LIMIT 10;


-- Q7  Cancellations: does a longer lead time mean more cancellations?
SELECT CASE
         WHEN lead_time_days <  60 THEN '1: < 2 months'
         WHEN lead_time_days < 180 THEN '2: 2-6 months'
         WHEN lead_time_days < 365 THEN '3: 6-12 months'
         ELSE                           '4: > 12 months'
       END                                                        AS lead_time_bucket,
       COUNT(*)                                                   AS bookings,
       SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END)      AS cancelled,
       ROUND(AVG(CASE WHEN status = 'cancelled' THEN 1.0 ELSE 0 END) * 100, 1) AS cancel_rate_pct
FROM v_event_financials
GROUP BY 1
ORDER BY 1;


-- Q8  No-shows: actual vs. expected attendees by customer type
SELECT customer_type,
       COUNT(*)                                                         AS events,
       ROUND(AVG(actual_attendees::numeric / expected_attendees) * 100, 1) AS show_up_rate_pct
FROM v_event_financials
WHERE status = 'completed'
GROUP BY customer_type
ORDER BY show_up_rate_pct;


-- Q9  Service attach rate: in what % of events is each service sold?
SELECT s.name,
       COUNT(DISTINCT es.event_id)                                        AS events_with_service,
       ROUND(COUNT(DISTINCT es.event_id) * 100.0 /
             (SELECT COUNT(*) FROM events WHERE status = 'completed'), 1) AS attach_rate_pct,
       ROUND(SUM(es.quantity * (es.unit_price_eur - s.unit_cost_eur)))    AS margin_eur
FROM services s
LEFT JOIN event_services es ON es.service_id = s.service_id
GROUP BY s.name
ORDER BY margin_eur DESC;


-- Q10 Revenue per attendee by event type – who is worth the most per head?
SELECT event_type,
       ROUND(SUM(total_revenue) / SUM(actual_attendees), 2) AS revenue_per_attendee_eur,
       ROUND(SUM(service_revenue) / SUM(total_revenue) * 100, 1) AS service_share_pct
FROM v_event_financials
WHERE status = 'completed'
GROUP BY event_type
ORDER BY revenue_per_attendee_eur DESC;
