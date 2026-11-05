# Event Venue Analytics

**How can a congress & event center grow revenue and use its rooms better?**

An end-to-end data project: relational database design (PostgreSQL), an ETL pipeline in Python, business analysis in SQL and an interactive dashboard, ending with recommendations like a consulting deliverable.

> All data will be **synthetic**, generated for a fictional venue. No real company data is used.

## Status

🚧 Work in progress

- [x] Data model: ER diagram and PostgreSQL schema ([`docs/er_diagram.md`](docs/er_diagram.md), [`sql/01_schema.sql`](sql/01_schema.sql))
- [ ] Synthetic data generator
- [ ] ETL pipeline with data-quality checks
- [ ] Business analysis in SQL
- [ ] Dashboard
- [ ] Findings & recommendations

## Run the database locally

```bash
docker compose up -d
psql -h localhost -U postgres -d eventdb -f sql/01_schema.sql   # password: postgres
```
