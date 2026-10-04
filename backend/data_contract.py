"""DukaanIQ canonical data contract and CSV normalization helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


# Canonical fields used internally by DukaanIQ.
REQUIRED_CORE_FIELDS = [
    "product_id",
    "product_name",
    "quantity_sold",
    "sale_price",
    "sale_date",
]

OPTIONAL_FIELDS = [
    "order_id",
    "customer_id",
    "cost_price",
    "current_stock",
    "reorder_threshold",
    "category",
    "supplier",
    "country",
]

ALL_CANONICAL_FIELDS = REQUIRED_CORE_FIELDS + OPTIONAL_FIELDS

# Aliases accepted from common retail/CSV formats.
ALIASES: Dict[str, List[str]] = {
    "product_id": ["product_id", "product", "sku", "stockcode", "stock_code", "item_id", "item_code", "product_code"],
    "product_name": ["product_name", "description", "product description", "item_name", "item", "product_title", "name"],
    "quantity_sold": ["quantity_sold", "quantity", "qty", "units_sold", "units", "sold_quantity", "sales_quantity"],
    "sale_price": ["sale_price", "unitprice", "unit_price", "price", "selling_price", "selling price", "sales_price", "amount_per_unit"],
    "sale_date": ["sale_date", "invoicedate", "invoice_date", "date", "transaction_date", "order_date", "sales_date", "timestamp"],
    "order_id": ["order_id", "invoiceno", "invoice_no", "invoice", "transaction_id"],
    "customer_id": ["customer_id", "customerid", "customer", "customer_no"],
    "cost_price": ["cost_price", "cost", "unit_cost", "purchase_price", "buying_price"],
    "current_stock": ["current_stock", "stock", "inventory", "stock_quantity", "on_hand"],
    "reorder_threshold": ["reorder_threshold", "reorder_point", "minimum_stock", "min_stock", "restock_threshold"],
    "category": ["category", "product_category", "type"],
    "supplier": ["supplier", "vendor", "supplier_name"],
    "country": ["country", "market", "region"],
}


def _normal(text: object) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text).strip()).strip("_")


ALIAS_LOOKUP = {
    _normal(alias): canonical
    for canonical, aliases in ALIASES.items()
    for alias in aliases
}


@dataclass
class DataCapabilities:
    has_inventory: bool
    has_profit: bool
    has_reorder_threshold: bool
    has_category: bool
    has_customer: bool
    has_order: bool

    def as_dict(self) -> dict:
        return {
            "has_inventory": bool(self.has_inventory),
            "has_profit": bool(self.has_profit),
            "has_reorder_threshold": bool(self.has_reorder_threshold),
            "has_category": bool(self.has_category),
            "has_customer": bool(self.has_customer),
            "has_order": bool(self.has_order),
        }


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Map common source column names to DukaanIQ canonical names."""
    if df is None or df.empty:
        raise ValueError("The uploaded dataset is empty.")

    data = df.copy()
    mapping: dict[str, str] = {}
    used: set[str] = set()

    for source in list(data.columns):
        canonical = ALIAS_LOOKUP.get(_normal(source))
        if canonical and canonical not in used:
            data = data.rename(columns={source: canonical})
            mapping[source] = canonical
            used.add(canonical)

    # Product ID/name are both useful, but many real-world sales files have only
    # one of them. Derive the missing one instead of rejecting an otherwise usable CSV.
    if "product_id" not in data.columns and "product_name" not in data.columns:
        data["product_id"] = [f"ROW-{i+1}" for i in range(len(data))]
        data["product_name"] = data["product_id"]
    elif "product_id" not in data.columns:
        data["product_id"] = data["product_name"]
    elif "product_name" not in data.columns:
        data["product_name"] = data["product_id"]

    # Revenue-only exports are common. Treat each row as one sales unit when
    # there is no quantity column, while preserving the actual row amount.
    if "sale_price" not in data.columns:
        revenue_source = next((c for c in data.columns if _normal(c) in {
            "revenue", "sales", "sales_amount", "total_sales", "total_revenue", "amount", "total_amount", "net_sales"
        }), None)
        if revenue_source is not None:
            data["sale_price"] = pd.to_numeric(data[revenue_source], errors="coerce")
            if "quantity_sold" not in data.columns:
                data["quantity_sold"] = 1

    missing = [field for field in ["quantity_sold", "sale_price", "sale_date"] if field not in data.columns]
    if missing:
        raise ValueError(
            "Could not identify the required sales fields: " + ", ".join(missing) + ". "
            "Accepted examples include Quantity/Qty, UnitPrice/Price/Sales, and Date/SaleDate."
        )

    for field in OPTIONAL_FIELDS:
        if field not in data.columns:
            data[field] = pd.NA

    data = data[ALL_CANONICAL_FIELDS].copy()

    # Text normalization
    for field in ["product_id", "product_name", "order_id", "customer_id", "category", "supplier", "country"]:
        data[field] = data[field].fillna("").astype(str).str.strip()

    # Numeric normalization
    for field in ["quantity_sold", "sale_price", "cost_price", "current_stock", "reorder_threshold"]:
        data[field] = pd.to_numeric(data[field], errors="coerce")

    # Date normalization
    data["sale_date"] = pd.to_datetime(data["sale_date"], errors="coerce", dayfirst=True)

    # Required numeric/date fields must be usable.
    data = data.dropna(subset=["quantity_sold", "sale_price", "sale_date"])
    data["revenue"] = data["quantity_sold"] * data["sale_price"]
    data["gross_profit"] = data["quantity_sold"] * (data["sale_price"] - data["cost_price"])
    data["gross_margin"] = data["gross_profit"].div(data["revenue"].replace(0, pd.NA)) * 100

    return data, mapping


def capabilities(df: pd.DataFrame) -> DataCapabilities:
    return DataCapabilities(
        has_inventory="current_stock" in df.columns and df["current_stock"].notna().any(),
        has_profit="cost_price" in df.columns and df["cost_price"].notna().any(),
        has_reorder_threshold="reorder_threshold" in df.columns and df["reorder_threshold"].notna().any(),
        has_category="category" in df.columns and df["category"].replace("", pd.NA).notna().any(),
        has_customer="customer_id" in df.columns and df["customer_id"].replace("", pd.NA).notna().any(),
        has_order="order_id" in df.columns and df["order_id"].replace("", pd.NA).notna().any(),
    )


def validation_summary(raw_df: pd.DataFrame, normalized_df: pd.DataFrame, mapping: dict) -> dict:
    caps = capabilities(normalized_df)
    return {
        "input_rows": int(len(raw_df)),
        "valid_rows": int(len(normalized_df)),
        "dropped_rows": int(len(raw_df) - len(normalized_df)),
        "source_columns": [str(c) for c in raw_df.columns],
        "canonical_columns": list(normalized_df.columns),
        "mapping": mapping,
        "capabilities": caps.as_dict(),
    }


def to_legacy_analytics_schema(canonical_df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility adapter for the current analytics/frontend implementation."""
    data = canonical_df.copy()
    return data.rename(columns={
        "product_id": "StockCode",
        "product_name": "Description",
        "quantity_sold": "Quantity",
        "sale_price": "UnitPrice",
        "sale_date": "InvoiceDate",
        "order_id": "InvoiceNo",
        "customer_id": "CustomerID",
        "category": "Category",
        "cost_price": "CostPrice",
        "current_stock": "CurrentStock",
        "reorder_threshold": "ReorderThreshold",
        "supplier": "Supplier",
        "country": "Country",
    })
