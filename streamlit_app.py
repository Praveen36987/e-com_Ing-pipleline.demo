"""Interactive decision dashboard for the e-commerce analytics pipeline."""

from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "data" / "ecommerce.db"

st.set_page_config(
    page_title="E-commerce Decision Hub",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=300)
def load_data(query: str, params: tuple = ()) -> pd.DataFrame:
    """Read a query from the local analytics database with a short cache."""
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query(query, connection, params=params)


@st.cache_data(ttl=300)
def available_filters() -> tuple[list[str], pd.Timestamp, pd.Timestamp]:
    data = load_data(
        """
        SELECT MIN(t.full_date) AS min_date, MAX(t.full_date) AS max_date
        FROM fact_orders f JOIN dim_time t ON f.time_id = t.time_id
        """
    )
    categories = load_data(
        """
        SELECT DISTINCT category_name
        FROM fact_orders
        WHERE category_name IS NOT NULL AND category_name NOT IN ('', 'Unknown')
        ORDER BY category_name
        """
    )["category_name"].tolist()
    return categories, pd.Timestamp(data.loc[0, "min_date"]), pd.Timestamp(data.loc[0, "max_date"])


def filtered_metrics(start_date: str, end_date: str, categories: list[str]) -> pd.DataFrame:
    """Return dashboard totals for the current user selections."""
    category_filter = ""
    params: list[str] = [start_date, end_date]
    if categories:
        placeholders = ", ".join("?" for _ in categories)
        category_filter = f" AND f.category_name IN ({placeholders})"
        params.extend(categories)
    return load_data(
        f"""
        SELECT
            COUNT(DISTINCT f.order_id) AS total_orders,
            ROUND(SUM(f.total_amount), 2) AS total_revenue,
            ROUND(AVG(f.total_amount), 2) AS avg_order_value,
            ROUND(AVG(f.review_score), 2) AS avg_review_score,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN f.order_status = 'delivered' THEN f.order_id END)
                  / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS fulfilment_rate_pct
        FROM fact_orders f
        JOIN dim_time t ON f.time_id = t.time_id
        WHERE t.full_date BETWEEN ? AND ? {category_filter}
        """,
        tuple(params),
    )


def main() -> None:
    st.title("🛍️ E-commerce Decision Hub")
    st.caption("Historical category intelligence from the Olist pipeline — updated whenever the pipeline refreshes.")

    if not DATABASE_PATH.exists():
        st.error("Database not found. Run `python main.py --run-once` before launching the dashboard.")
        st.stop()

    categories, min_date, max_date = available_filters()
    with st.sidebar:
        st.header("Decision filters")
        date_range = st.date_input(
            "Order date range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
        selected_categories = st.multiselect("Categories", categories)
        st.divider()
        st.caption("Filters change the overview and trend charts. The decision scorecard uses the full historical dataset so rankings remain comparable.")

    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.info("Select both a start and end date to view results.")
        st.stop()
    start_date, end_date = (value.isoformat() for value in date_range)
    metrics = filtered_metrics(start_date, end_date, selected_categories).iloc[0]

    kpi_columns = st.columns(5)
    kpi_columns[0].metric("Orders", f"{int(metrics['total_orders'] or 0):,}")
    kpi_columns[1].metric("Revenue", f"R$ {float(metrics['total_revenue'] or 0):,.0f}")
    kpi_columns[2].metric("Average order value", f"R$ {float(metrics['avg_order_value'] or 0):,.2f}")
    kpi_columns[3].metric("Average review", f"{float(metrics['avg_review_score'] or 0):.2f} / 5")
    kpi_columns[4].metric("Fulfilment rate", f"{float(metrics['fulfilment_rate_pct'] or 0):.1f}%")

    overview_tab, priorities_tab, health_tab = st.tabs(["Overview", "Category priorities", "Pipeline health"])

    with overview_tab:
        category_filter = ""
        params: list[str] = [start_date, end_date]
        if selected_categories:
            placeholders = ", ".join("?" for _ in selected_categories)
            category_filter = f" AND f.category_name IN ({placeholders})"
            params.extend(selected_categories)
        monthly = load_data(
            f"""
            SELECT substr(t.full_date, 1, 7) AS month,
                   ROUND(SUM(f.total_amount), 2) AS revenue,
                   COUNT(DISTINCT f.order_id) AS orders
            FROM fact_orders f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.full_date BETWEEN ? AND ? {category_filter}
            GROUP BY substr(t.full_date, 1, 7)
            ORDER BY month
            """,
            tuple(params),
        )
        by_category = load_data(
            f"""
            SELECT f.category_name, ROUND(SUM(f.total_amount), 2) AS revenue,
                   COUNT(DISTINCT f.order_id) AS orders
            FROM fact_orders f
            JOIN dim_time t ON f.time_id = t.time_id
            WHERE t.full_date BETWEEN ? AND ? {category_filter}
            GROUP BY f.category_name
            ORDER BY revenue DESC
            LIMIT 15
            """,
            tuple(params),
        )
        left, right = st.columns(2)
        with left:
            st.subheader("Revenue trend")
            st.plotly_chart(px.line(monthly, x="month", y="revenue", markers=True, labels={"revenue": "Revenue (R$)", "month": "Month"}), use_container_width=True)
        with right:
            st.subheader("Top categories by revenue")
            st.plotly_chart(px.bar(by_category.sort_values("revenue"), x="revenue", y="category_name", orientation="h", labels={"revenue": "Revenue (R$)", "category_name": "Category"}), use_container_width=True)

    with priorities_tab:
        scorecard = load_data("SELECT * FROM decision_category_scorecard")
        st.subheader("Where to focus next")
        st.caption("Score weights: demand-to-competition 30%, recent order momentum 25%, review score 20%, fulfilment 15%, and revenue contribution 10%.")
        chart_data = scorecard.head(15).sort_values("decision_score")
        st.plotly_chart(
            px.bar(chart_data, x="decision_score", y="category_name", color="recommended_action", orientation="h", hover_data=["total_revenue", "order_growth_pct", "fulfilment_rate_pct", "avg_review_score"], labels={"decision_score": "Decision score (0–100)", "category_name": "Category"}),
            use_container_width=True,
        )
        visible_columns = ["category_name", "decision_score", "recommended_action", "total_orders", "total_revenue", "demand_to_competition_ratio", "order_growth_pct", "fulfilment_rate_pct", "avg_review_score"]
        st.dataframe(scorecard[visible_columns], use_container_width=True, hide_index=True)
        st.download_button("Download decision scorecard (CSV)", scorecard.to_csv(index=False).encode("utf-8"), "decision_category_scorecard.csv", "text/csv")
        st.info("Interpret this as a prioritisation tool, not an individual-customer purchase prediction. Individual recommendations require customer-level browsing, search, cart, and repeat-purchase events.")

    with health_tab:
        monitoring = load_data("SELECT * FROM pipeline_monitoring ORDER BY id DESC LIMIT 20")
        rejects = load_data("SELECT source_table, COUNT(*) AS rejected_rows FROM rejects GROUP BY source_table ORDER BY rejected_rows DESC")
        st.subheader("Latest pipeline runs")
        st.dataframe(monitoring, use_container_width=True, hide_index=True)
        st.subheader("Rejected records by source")
        st.dataframe(rejects, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
