# E-Commerce Data Ingestion Pipeline - Architecture Documentation

## Pipeline Overview

This project implements a production-grade, end-to-end e-commerce data pipeline engineered to handle multi-source data ingestion, automated validation and cleaning, SQLite Star Schema storage, and SQL analytical view transformations.

```mermaid
flowchart TD
    subgraph Data Sources
        CSV[Bulk CSV Files /data/raw/*.csv\nOlist Kaggle Dataset]
        API[Live REST API\nhttps://dummyjson.com/products]
    end

    subgraph 1. Extract Layer
        CSV_EXT[CSV Extractor\nDynamic Directory Scanner]
        API_EXT[API Extractor\nExponential Backoff & Retries]
    end

    subgraph 2. Validate & Clean
        VAL[Schema Validation & Type Coercion]
        REJ[(Rejects Table\nMalformed/Null Keys)]
    end

    subgraph 3. Load & Staging (SQLite)
        STAGE[(Staging Tables\nstaging_*)]
    end

    subgraph 4. Star Schema Storage
        DIM_P[dim_products]
        DIM_C[dim_customers]
        DIM_CAT[dim_category]
        DIM_T[dim_time]
        FACT_O[fact_orders]
    end

    subgraph 5. SQL Transformations & Analytics
        REV_V[view_revenue_by_category_over_time]
        FUN_V[view_order_funnel_metrics]
        SENT_V[view_sentiment_vs_volume]
        SEO_V[seo_opportunity_report]
    end

    subgraph 6. Orchestration & Monitoring
        SCHED[Scheduler / Main CLI]
        MON[(pipeline_monitoring)]
    end

    CSV --> CSV_EXT
    API --> API_EXT
    CSV_EXT --> VAL
    API_EXT --> VAL
    VAL -- Invalid Rows --> REJ
    VAL -- Valid Rows --> STAGE
    STAGE --> DIM_P & DIM_C & DIM_CAT & DIM_T
    DIM_P & DIM_C & DIM_CAT & DIM_T --> FACT_O
    FACT_O --> REV_V & FUN_V & SENT_V & SEO_V
    SCHED --> CSV_EXT & API_EXT & STAGE & FACT_O
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
