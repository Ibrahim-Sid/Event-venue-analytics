# Event Venue Analytics

**How can a congress & event center grow revenue and use its rooms better?**

An end-to-end data project: relational database design (PostgreSQL), an ETL pipeline in Python, business analysis in SQL and an interactive dashboard, ending with recommendations like a consulting deliverable.

> All data will be **synthetic**, generated for a fictional venue. No real company data is used.

## Status

🚧 Work in progress

- [x] Data model: ER diagram and PostgreSQL schema ([`docs/er_diagram.md`](docs/er_diagram.md), [`sql/01_schema.sql`](sql/01_schema.sql))
- [x] Synthetic data generator ([`etl/generate_data.py`](etl/generate_data.py))
- [x] ETL pipeline with data-quality checks ([`etl/load_data.py`](etl/load_data.py))
- [x] Business analysis in SQL ([`sql/02_analysis.sql`](sql/02_analysis.sql))
- [ ] Dashboard
- [ ] Findings & recommendations

## How to run

```bash
# 1. Start PostgreSQL
docker compose up -d

# 2. Install Python dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Generate data and load it into the database
python etl/generate_data.py
python etl/load_data.py
```
