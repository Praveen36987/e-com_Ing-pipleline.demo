-- Star Schema DDL

CREATE TABLE IF NOT EXISTS dim_category (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL,
    source_system TEXT DEFAULT 'UNIFIED'
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id TEXT PRIMARY KEY,
    title TEXT,
    category_name TEXT,
    price REAL,
    stock INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    brand TEXT,
    source_type TEXT, -- 'CSV_BULK' or 'LIVE_API'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_date TEXT UNIQUE NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_orders (
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    customer_id TEXT,
    time_id INTEGER,
    category_name TEXT,
    order_status TEXT,
    item_count INTEGER DEFAULT 1,
    unit_price REAL DEFAULT 0.0,
    freight_value REAL DEFAULT 0.0,
    total_amount REAL DEFAULT 0.0,
    review_score REAL,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customers(customer_id),
    FOREIGN KEY (time_id) REFERENCES dim_time(time_id)
);
