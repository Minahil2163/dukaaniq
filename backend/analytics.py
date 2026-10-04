"""
DukaanIQ - Retail Analytics Engine

Dataset:
    InvoiceNo
    StockCode
    Description
    Quantity
    InvoiceDate
    UnitPrice
    CustomerID
    Country

Derived:
    Revenue = Quantity * UnitPrice

Important:
    No profit calculation because cost is not available.
    No stock/inventory calculation because stock is not available.
    No category calculation because category is not available.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


# =========================================================
# REQUIRED DATASET COLUMNS
# =========================================================

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


# =========================================================
# DATA PREPARATION
# =========================================================

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the uploaded Online Retail dataset.

    Only the supported dataset fields are used.
    """

    if df is None or df.empty:
        raise ValueError("The uploaded dataset is empty.")

    data = df.copy()

    # -----------------------------------------------------
    # Check required columns
    # -----------------------------------------------------

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    # -----------------------------------------------------
    # Keep only supported columns
    # -----------------------------------------------------

    data = data[REQUIRED_COLUMNS].copy()

    # -----------------------------------------------------
    # Clean text fields
    # -----------------------------------------------------

    text_columns = [
        "InvoiceNo",
        "StockCode",
        "Description",
        "CustomerID",
        "Country",
    ]

    for column in text_columns:
        data[column] = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    # -----------------------------------------------------
    # Numeric fields
    # -----------------------------------------------------

    data["Quantity"] = pd.to_numeric(
        data["Quantity"],
        errors="coerce",
    ).fillna(0)

    data["UnitPrice"] = pd.to_numeric(
        data["UnitPrice"],
        errors="coerce",
    ).fillna(0)

    # -----------------------------------------------------
    # Date
    #
    # Example:
    # 01/12/2010 8:26
    # -----------------------------------------------------

    data["InvoiceDate"] = pd.to_datetime(
        data["InvoiceDate"],
        errors="coerce",
        dayfirst=True,
    )

    # -----------------------------------------------------
    # Revenue
    # -----------------------------------------------------

    data["Revenue"] = (
        data["Quantity"] *
        data["UnitPrice"]
    )

    return data


# =========================================================
# DATASET INFO
# =========================================================

def dataset_info(df: pd.DataFrame) -> dict:
    """
    Return high-level information about the dataset.
    """

    if df is None or df.empty:
        return {
            "rows": 0,
            "products": 0,
            "orders": 0,
            "customers": 0,
            "countries": 0,
            "units_sold": 0,
            "revenue": 0,
            "has_date": False,
        }

    data = prepare_dataframe(df)

    valid_invoice = (
        data["InvoiceNo"]
        .replace("", pd.NA)
        .dropna()
    )

    valid_product = (
        data["StockCode"]
        .replace("", pd.NA)
        .dropna()
    )

    valid_customer = (
        data["CustomerID"]
        .replace("", pd.NA)
        .dropna()
    )

    valid_country = (
        data["Country"]
        .replace("", pd.NA)
        .dropna()
    )

    return {
        "rows": int(len(data)),

        "products": int(
            valid_product.nunique()
        ),

        "orders": int(
            valid_invoice.nunique()
        ),

        "customers": int(
            valid_customer.nunique()
        ),

        "countries": int(
            valid_country.nunique()
        ),

        "units_sold": round(
            float(data["Quantity"].sum()),
            2,
        ),

        "revenue": round(
            float(data["Revenue"].sum()),
            2,
        ),

        "has_date": bool(
            data["InvoiceDate"].notna().any()
        ),
    }


# =========================================================
# PRODUCT PERFORMANCE
# =========================================================

def product_performance(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Calculate product-level sales performance.
    """

    if df is None or df.empty:
        return []

    data = prepare_dataframe(df)

    grouped = (
        data.groupby(
            [
                "StockCode",
                "Description",
            ],
            dropna=False,
        )
        .agg(
            orders=(
                "InvoiceNo",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),

            units_sold=(
                "Quantity",
                "sum",
            ),

            revenue=(
                "Revenue",
                "sum",
            ),

            average_price=(
                "UnitPrice",
                "mean",
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "revenue",
        ascending=False,
    )

    result = []

    for _, row in grouped.iterrows():

        result.append(
            {
                "stock_code": str(
                    row["StockCode"]
                ),

                "product": str(
                    row["Description"]
                ),

                "orders": int(
                    row["orders"] or 0
                ),

                "units_sold": round(
                    float(
                        row["units_sold"] or 0
                    ),
                    2,
                ),

                "revenue": round(
                    float(
                        row["revenue"] or 0
                    ),
                    2,
                ),

                "average_price": round(
                    float(
                        row["average_price"] or 0
                    ),
                    2,
                ),
            }
        )

    return result


# =========================================================
# TOP PRODUCTS
# =========================================================

def top_products(
    df: pd.DataFrame,
    limit: int = 10,
) -> list[dict]:
    """
    Return products ordered by revenue.
    """

    products = product_performance(df)

    return products[:limit]


# =========================================================
# SALES TREND
# =========================================================

def sales_trend(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Daily revenue and units sold.
    """

    if df is None or df.empty:
        return []

    data = prepare_dataframe(df)

    data = data[
        data["InvoiceDate"].notna()
    ].copy()

    if data.empty:
        return []

    data["Date"] = (
        data["InvoiceDate"]
        .dt.date
    )

    grouped = (
        data.groupby("Date")
        .agg(
            revenue=(
                "Revenue",
                "sum",
            ),

            units_sold=(
                "Quantity",
                "sum",
            ),

            orders=(
                "InvoiceNo",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "Date"
    )

    result = []

    for _, row in grouped.iterrows():

        result.append(
            {
                "date": str(
                    row["Date"]
                ),

                "revenue": round(
                    float(
                        row["revenue"] or 0
                    ),
                    2,
                ),

                "units_sold": round(
                    float(
                        row["units_sold"] or 0
                    ),
                    2,
                ),

                "orders": int(
                    row["orders"] or 0
                ),
            }
        )

    return result


# =========================================================
# MONTHLY SALES
# =========================================================

def monthly_sales(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Monthly revenue, units and orders.
    """

    if df is None or df.empty:
        return []

    data = prepare_dataframe(df)

    data = data[
        data["InvoiceDate"].notna()
    ].copy()

    if data.empty:
        return []

    data["Month"] = (
        data["InvoiceDate"]
        .dt.to_period("M")
        .astype(str)
    )

    grouped = (
        data.groupby("Month")
        .agg(
            revenue=(
                "Revenue",
                "sum",
            ),

            units_sold=(
                "Quantity",
                "sum",
            ),

            orders=(
                "InvoiceNo",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),
        )
        .reset_index()
    )

    result = []

    for _, row in grouped.iterrows():

        result.append(
            {
                "month": str(
                    row["Month"]
                ),

                "revenue": round(
                    float(
                        row["revenue"] or 0
                    ),
                    2,
                ),

                "units_sold": round(
                    float(
                        row["units_sold"] or 0
                    ),
                    2,
                ),

                "orders": int(
                    row["orders"] or 0
                ),
            }
        )

    return result


# =========================================================
# COUNTRY PERFORMANCE
# =========================================================

def country_performance(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Country-level sales performance.
    """

    if df is None or df.empty:
        return []

    data = prepare_dataframe(df)

    data = data[
        data["Country"] != ""
    ].copy()

    if data.empty:
        return []

    grouped = (
        data.groupby("Country")
        .agg(
            revenue=(
                "Revenue",
                "sum",
            ),

            units_sold=(
                "Quantity",
                "sum",
            ),

            orders=(
                "InvoiceNo",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),

            customers=(
                "CustomerID",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "revenue",
        ascending=False,
    )

    result = []

    for _, row in grouped.iterrows():

        result.append(
            {
                "country": str(
                    row["Country"]
                ),

                "revenue": round(
                    float(
                        row["revenue"] or 0
                    ),
                    2,
                ),

                "units_sold": round(
                    float(
                        row["units_sold"] or 0
                    ),
                    2,
                ),

                "orders": int(
                    row["orders"] or 0
                ),

                "customers": int(
                    row["customers"] or 0
                ),
            }
        )

    return result


# =========================================================
# CUSTOMER PERFORMANCE
# =========================================================

def customer_performance(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Customer-level sales performance.
    """

    if df is None or df.empty:
        return []

    data = prepare_dataframe(df)

    data = data[
        data["CustomerID"] != ""
    ].copy()

    if data.empty:
        return []

    grouped = (
        data.groupby("CustomerID")
        .agg(
            revenue=(
                "Revenue",
                "sum",
            ),

            units_sold=(
                "Quantity",
                "sum",
            ),

            orders=(
                "InvoiceNo",
                lambda x: (
                    x.replace("", pd.NA)
                    .dropna()
                    .nunique()
                ),
            ),
        )
        .reset_index()
    )

    grouped = grouped.sort_values(
        "revenue",
        ascending=False,
    )

    result = []

    for _, row in grouped.iterrows():

        result.append(
            {
                "customer_id": str(
                    row["CustomerID"]
                ),

                "revenue": round(
                    float(
                        row["revenue"] or 0
                    ),
                    2,
                ),

                "units_sold": round(
                    float(
                        row["units_sold"] or 0
                    ),
                    2,
                ),

                "orders": int(
                    row["orders"] or 0
                ),
            }
        )

    return result


# =========================================================
# PRODUCT DEMAND
# =========================================================

def demand_analysis(
    df: pd.DataFrame,
) -> list[dict]:
    """
    Sales-demand analysis.

    This does NOT represent current inventory.
    It only describes recorded sales activity.
    """

    products = product_performance(df)

    if not products:
        return []

    result = []

    for product in products:

        result.append(
            {
                "stock_code": product[
                    "stock_code"
                ],

                "product": product[
                    "product"
                ],

                "units_sold": product[
                    "units_sold"
                ],

                "revenue": product[
                    "revenue"
                ],

                "orders": product[
                    "orders"
                ],
            }
        )

    result.sort(
        key=lambda x: x["units_sold"],
        reverse=True,
    )

    return result


# =========================================================
# BUSINESS SUMMARY
# =========================================================

def business_summary(
    df: pd.DataFrame,
) -> dict:
    """
    Complete dashboard summary.
    """

    if df is None or df.empty:

        return {
            "total_revenue": 0,
            "orders_count": 0,
            "units_sold": 0,
            "products_count": 0,
            "customers_count": 0,
            "countries_count": 0,

            "top_products": [],
            "low_performing_products": [],

            "sales_trend": [],
            "monthly_sales": [],
            "country_performance": [],

            "dataset_info": dataset_info(df),

            "has_profit": False,
            "has_stock": False,
            "has_category": False,
        }

    data = prepare_dataframe(df)

    info = dataset_info(data)

    products = product_performance(data)

    countries = country_performance(data)

    # Lowest revenue products
    low_products = sorted(
        products,
        key=lambda x: x["revenue"],
    )[:10]

    return {
        # -------------------------------------------------
        # Main KPIs
        # -------------------------------------------------

        "total_revenue": round(
            float(data["Revenue"].sum()),
            2,
        ),

        "orders_count": info[
            "orders"
        ],

        "units_sold": round(
            float(data["Quantity"].sum()),
            2,
        ),

        "products_count": info[
            "products"
        ],

        "customers_count": info[
            "customers"
        ],

        "countries_count": info[
            "countries"
        ],

        # -------------------------------------------------
        # Products
        # -------------------------------------------------

        "top_products": products[:10],

        "low_performing_products":
            low_products,

        # -------------------------------------------------
        # Analytics
        # -------------------------------------------------

        "sales_trend":
            sales_trend(data),

        "monthly_sales":
            monthly_sales(data),

        "country_performance":
            countries,

        # -------------------------------------------------
        # Dataset
        # -------------------------------------------------

        "dataset_info": info,

        # -------------------------------------------------
        # Explicit capability flags
        # -------------------------------------------------

        "has_profit": False,

        "has_stock": False,

        "has_category": False,

        "available_columns":
            REQUIRED_COLUMNS + ["Revenue"],
    }


# =========================================================
# MAIN ENTRY POINT
# =========================================================

def analyze_dataframe(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """
    Main entry point used by FastAPI.
    """

    normalized = prepare_dataframe(df)

    summary = business_summary(
        normalized
    )

    mapping = {
        "detected_columns": {
            column: (
                column
                if column in df.columns
                else None
            )
            for column in REQUIRED_COLUMNS
        },

        "available_fields": [
            column
            for column in REQUIRED_COLUMNS
            if column in df.columns
        ],

        "missing_fields": [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ],

        "original_columns": [
            str(column)
            for column in df.columns
        ],

        "rows": len(normalized),

        "summary": summary,
    }

    return normalized, mapping
# =========================================================
# DUKAANIQ PHASE 3 - DECISION SUPPORT ANALYTICS
# =========================================================

def enhanced_product_performance(canonical_df: pd.DataFrame) -> list[dict]:
    """Canonical-schema product analytics with optional profit/inventory metrics."""
    if canonical_df is None or canonical_df.empty:
        return []
    data = canonical_df.copy()
    data["revenue"] = pd.to_numeric(data["revenue"], errors="coerce").fillna(0)
    data["quantity_sold"] = pd.to_numeric(data["quantity_sold"], errors="coerce").fillna(0)
    data["sale_price"] = pd.to_numeric(data["sale_price"], errors="coerce").fillna(0)
    for c in ["cost_price", "current_stock", "reorder_threshold"]:
        data[c] = pd.to_numeric(data[c], errors="coerce")

    grouped = data.groupby(["product_id", "product_name"], dropna=False).agg(
        units_sold=("quantity_sold", "sum"),
        revenue=("revenue", "sum"),
        average_price=("sale_price", "mean"),
        cost_price=("cost_price", "mean"),
        current_stock=("current_stock", "max"),
        reorder_threshold=("reorder_threshold", "max"),
    ).reset_index()
    grouped["gross_profit"] = grouped["units_sold"] * (grouped["average_price"] - grouped["cost_price"])
    grouped["gross_margin"] = (grouped["gross_profit"] / grouped["revenue"].replace(0, pd.NA)) * 100
    grouped = grouped.sort_values("revenue", ascending=False)

    result = []
    for _, r in grouped.iterrows():
        result.append({
            "product_id": str(r["product_id"]),
            "product": str(r["product_name"]),
            "units_sold": round(float(r["units_sold"]), 2),
            "revenue": round(float(r["revenue"]), 2),
            "average_price": round(float(r["average_price"]), 2),
            "gross_profit": None if pd.isna(r["gross_profit"]) else round(float(r["gross_profit"]), 2),
            "gross_margin": None if pd.isna(r["gross_margin"]) else round(float(r["gross_margin"]), 2),
            "current_stock": None if pd.isna(r["current_stock"]) else round(float(r["current_stock"]), 2),
            "reorder_threshold": None if pd.isna(r["reorder_threshold"]) else round(float(r["reorder_threshold"]), 2),
        })
    return result


def inventory_risk_analysis(canonical_df: pd.DataFrame, threshold_days: int = 7) -> list[dict]:
    """Estimate stock coverage from sales velocity when current stock is available."""
    if canonical_df is None or canonical_df.empty or "current_stock" not in canonical_df.columns:
        return []
    data = canonical_df.copy()
    data["sale_date"] = pd.to_datetime(data["sale_date"], errors="coerce")
    data["quantity_sold"] = pd.to_numeric(data["quantity_sold"], errors="coerce").fillna(0)
    data["current_stock"] = pd.to_numeric(data["current_stock"], errors="coerce")
    data["reorder_threshold"] = pd.to_numeric(data["reorder_threshold"], errors="coerce")
    data = data.dropna(subset=["current_stock"])
    if data.empty:
        return []

    start, end = data["sale_date"].min(), data["sale_date"].max()
    days = max((end - start).days + 1, 1) if pd.notna(start) and pd.notna(end) else 1
    grouped = data.groupby(["product_id", "product_name"], dropna=False).agg(
        units_sold=("quantity_sold", "sum"),
        current_stock=("current_stock", "max"),
        reorder_threshold=("reorder_threshold", "max"),
    ).reset_index()
    grouped["daily_sales_velocity"] = grouped["units_sold"] / days
    grouped["stock_coverage_days"] = grouped["current_stock"] / grouped["daily_sales_velocity"].replace(0, pd.NA)

    def risk(row):
        coverage = row["stock_coverage_days"]
        if pd.isna(coverage): return "NO_DEMAND_DATA"
        if coverage <= 2: return "CRITICAL"
        if coverage <= threshold_days: return "HIGH"
        if coverage <= threshold_days * 2: return "MEDIUM"
        return "LOW"

    grouped["risk"] = grouped.apply(risk, axis=1)
    grouped["restock_review"] = (grouped["risk"].isin(["CRITICAL", "HIGH"])) | (
        grouped["reorder_threshold"].notna() & (grouped["current_stock"] <= grouped["reorder_threshold"])
    )
    grouped = grouped.sort_values(["restock_review", "stock_coverage_days"], ascending=[False, True])
    result = []
    for _, r in grouped.iterrows():
        result.append({
            "product_id": str(r["product_id"]),
            "product": str(r["product_name"]),
            "current_stock": round(float(r["current_stock"]), 2),
            "units_sold": round(float(r["units_sold"]), 2),
            "daily_sales_velocity": round(float(r["daily_sales_velocity"]), 2),
            "stock_coverage_days": None if pd.isna(r["stock_coverage_days"]) else round(float(r["stock_coverage_days"]), 2),
            "reorder_threshold": None if pd.isna(r["reorder_threshold"]) else round(float(r["reorder_threshold"]), 2),
            "risk": r["risk"],
            "restock_review": bool(r["restock_review"]),
        })
    return result


def enhanced_business_summary(canonical_df: pd.DataFrame, threshold_days: int = 7) -> dict:
    """Single deterministic summary used by the Phase 3 dashboard and future agent tools."""
    if canonical_df is None or canonical_df.empty:
        return {"revenue": 0, "gross_profit": None, "gross_margin": None, "products": 0, "orders": 0, "units_sold": 0,
                "top_products": [], "low_performing_products": [], "inventory_risks": [], "restock_count": 0,
                "has_profit": False, "has_inventory": False, "threshold_days": threshold_days}
    d = canonical_df.copy()
    d["quantity_sold"] = pd.to_numeric(d["quantity_sold"], errors="coerce").fillna(0)
    d["revenue"] = pd.to_numeric(d["revenue"], errors="coerce").fillna(0)
    d["gross_profit"] = pd.to_numeric(d["gross_profit"], errors="coerce")
    revenue = float(d["revenue"].sum())
    profit = float(d["gross_profit"].sum()) if d["gross_profit"].notna().any() else None
    margin = (profit / revenue * 100) if profit is not None and revenue else None
    products = enhanced_product_performance(d)
    risks = inventory_risk_analysis(d, threshold_days)
    return {
        "revenue": round(revenue, 2),
        "gross_profit": None if profit is None else round(profit, 2),
        "gross_margin": None if margin is None else round(margin, 2),
        "products": int(d["product_id"].nunique()),
        "orders": int(d["order_id"].replace("", pd.NA).dropna().nunique()),
        "units_sold": round(float(d["quantity_sold"].sum()), 2),
        "top_products": products[:10],
        "low_performing_products": sorted(products, key=lambda x: x["revenue"])[:10],
        "inventory_risks": risks[:20],
        "restock_count": sum(1 for x in risks if x["restock_review"]),
        "has_profit": profit is not None,
        "has_inventory": bool(risks),
        "threshold_days": threshold_days,
    }
