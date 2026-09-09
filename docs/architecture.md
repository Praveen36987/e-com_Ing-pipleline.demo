# E-Commerce Data Ingestion Pipeline - Architecture Documentation

## Pipeline Overview

This project implements a production-grade, end-to-end e-commerce data pipeline engineered to handle multi-source data ingestion, automated validation and cleaning, SQLite Star Schema storage, and SQL analytical view transformations.

```mermaid
flowchart TD
    subgraph sources["Data sources"]
        CSV["Bulk CSV files<br/>data/raw/*.csv"]
        API["DummyJSON products API"]
    end

    subgraph extract["1. Extract layer"]
        CSV_EXT["CSV extractor<br/>dynamic directory scan"]
        API_EXT["API extractor<br/>retry and backoff"]
    end

    subgraph validate["2. Validate and clean"]
        VAL["Schema validation and type coercion"]
        REJ["Rejects table"]
    end

    subgraph load["3. Load and stage in SQLite"]
        STAGE["Staging tables"]
    end

    subgraph model["4. Star schema"]
        DIM_P["dim_products"]
        DIM_C["dim_customers"]
        DIM_CAT["dim_category"]
        DIM_T["dim_time"]
        FACT_O["fact_orders"]
    end

    subgraph analytics["5. SQL analytics"]
        REV_V["Revenue by category and time"]
        FUN_V["Order funnel metrics"]
        SENT_V["Sentiment versus volume"]
        SEO_V["SEO opportunity report"]
        SCORE["Decision category scorecard"]
    end

    subgraph orchestration["6. Orchestration and monitoring"]
        SCHED["Scheduler and CLI"]
        MON["Pipeline monitoring"]
    end

    CSV --> CSV_EXT
    API --> API_EXT
    CSV_EXT --> VAL
    API_EXT --> VAL
    VAL -->|Invalid rows| REJ
    VAL -->|Valid rows| STAGE
    STAGE --> DIM_P
    STAGE --> DIM_C
    STAGE --> DIM_CAT
    STAGE --> DIM_T
    DIM_P --> FACT_O
    DIM_C --> FACT_O
    DIM_CAT --> FACT_O
    DIM_T --> FACT_O
    FACT_O --> REV_V
    FACT_O --> FUN_V
    FACT_O --> SENT_V
    FACT_O --> SEO_V
    FACT_O --> SCORE
    SCHED --> CSV_EXT
    SCHED --> API_EXT
    SCHED --> STAGE
    SCHED --> FACT_O
    SCHED --> MON
```

---

## Technical Architecture Components

### 1. Extract Layer (`src/extract/`)
- **Bulk CSV Extractor (`csv_extractor.py`)**: Automatically scans `/data/raw/` for any `.csv` files. Reads schemas dynamically, logs file sizes, row counts, and column names without requiring hardcoded filenames.
- **Live API Extractor (`api_extractor.py`)**: Uses Python `requests` configured with `urllib3.util.Retry` (5 retries, 1.0s backoff factor) to handle network glitches, rate limits (HTTP 429), or 5xx server errors gracefully. Handles pagination via `limit` and `skip`.

### 2. Validate & Clean Layer (`src/load/staging_loader.py`)
- Filters missing primary keys (`order_id`, `product_id`, `customer_id`), corrupt data types, or invalid prices.
- Rejects are serialized into JSON strings and stored in the `rejects` table along with the target source table name, rejection timestamp, and exact reason.

### 3. Load Layer (`src/load/star_schema_loader.py`)
- Transforms raw staging data into a dimensional Star Schema.
- Standardizes product categories across Portuguese Olist files and English API categories using category translation mapping.

### 4. Transform Layer (`sql/*.sql` & `src/transform/sql_transformer.py`)
- DDL scripts create analytical views:
  - `view_revenue_by_category_over_time`
  - `view_order_funnel_metrics`
  - `view_category_demand_vs_supply`
  - `view_sentiment_vs_volume`
  - `seo_opportunity_report`

### 5. Orchestration & Monitoring (`src/orchestrator/scheduler.py`)
- Measures start time, end time, and total run duration.
- Counts extracted rows, loaded fact records, and rejected rows.
- Records all run metadata into `pipeline_monitoring`.
