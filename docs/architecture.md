# E-Commerce Data Ingestion Pipeline - Architecture Documentation

## Pipeline Overview

This project implements a production-grade, end-to-end e-commerce data pipeline engineered to handle multi-source data ingestion, automated validation and cleaning, SQLite Star Schema storage, and SQL analytical view transformations.

```mermaid
mindmap
  root((E-commerce Decision Hub))
    Data sources
      Olist CSV files
        data/raw directory scan
      DummyJSON products API
        public catalog demo source
    Extract layer
      CSV extractor
        dynamic schema discovery
      API extractor
        retry and backoff
    Validate and clean
      schema checks
      type coercion
      rejects table
        invalid rows and reasons
    SQLite data model
      staging tables
      star schema
        dim_products
        dim_customers
        dim_category
        dim_time
        fact_orders
    SQL analytics
      revenue by category and time
      order funnel metrics
      sentiment versus volume
      SEO opportunity report
      decision category scorecard
    Orchestration and monitoring
      scheduler and CLI
      pipeline monitoring
```

---

## Technical Architecture Components

The GitHub-rendered mind map provides the overview. Use the linked component names below to open the implementation behind each branch.

### 1. Extract layer ([`src/extract/`](../src/extract/))
- **[Bulk CSV extractor](../src/extract/csv_extractor.py)**: Automatically scans `/data/raw/` for any `.csv` files. Reads schemas dynamically, logs file sizes, row counts, and column names without requiring hardcoded filenames.
- **[Live API extractor](../src/extract/api_extractor.py)**: Uses Python `requests` configured with `urllib3.util.Retry` (5 retries, 1.0s backoff factor) to handle network glitches, rate limits (HTTP 429), or 5xx server errors gracefully. Handles pagination via `limit` and `skip`.

### 2. Validate and clean ([`staging_loader.py`](../src/load/staging_loader.py))
- Filters missing primary keys (`order_id`, `product_id`, `customer_id`), corrupt data types, or invalid prices.
- Rejects are serialized into JSON strings and stored in the `rejects` table along with the target source table name, rejection timestamp, and exact reason.

### 3. Load layer ([`star_schema_loader.py`](../src/load/star_schema_loader.py))
- Transforms raw staging data into a dimensional Star Schema.
- Standardizes product categories across Portuguese Olist files and English API categories using category translation mapping.

### 4. Transform layer ([`sql/`](../sql/) and [`sql_transformer.py`](../src/transform/sql_transformer.py))
- DDL scripts create analytical views:
  - `view_revenue_by_category_over_time`
  - `view_order_funnel_metrics`
  - `view_category_demand_vs_supply`
  - `view_sentiment_vs_volume`
  - `seo_opportunity_report`

### 5. Orchestration and monitoring ([`scheduler.py`](../src/orchestrator/scheduler.py))
- Measures start time, end time, and total run duration.
- Counts extracted rows, loaded fact records, and rejected rows.
- Records all run metadata into `pipeline_monitoring`.
