"""Deterministic analytics tools used by the DukaanIQ AI Analyst.

Principle: Python computes business facts; the AI layer only interprets them.
"""
from typing import Any, Dict, List
import pandas as pd

from analytics import (
    enhanced_business_summary,
    enhanced_product_performance,
    inventory_risk_analysis,
    monthly_sales,
    sales_trend,
    top_products,
)


def _clean_records(records: list[dict]) -> list[dict]:
    out = []
    for row in records:
        clean = {}
        for k, v in row.items():
            if hasattr(v, "item"):
                v = v.item()
            if pd.isna(v) if not isinstance(v, (list, dict)) else False:
                v = None
            clean[k] = v
        out.append(clean)
    return out



def _legacy(df: pd.DataFrame) -> pd.DataFrame:
    """Adapt canonical DukaanIQ fields to legacy analytics functions."""
    mapping = {
        "product_id": "StockCode", "product_name": "Description",
        "quantity_sold": "Quantity", "sale_price": "UnitPrice",
        "sale_date": "InvoiceDate", "order_id": "InvoiceNo",
        "customer_id": "CustomerID", "country": "Country",
    }
    out = df.copy()
    for src, dst in mapping.items():
        if src in out.columns and dst not in out.columns:
            out[dst] = out[src]
    return out

def get_business_summary(canonical_df: pd.DataFrame) -> Dict[str, Any]:
    return enhanced_business_summary(canonical_df)


def get_top_products(canonical_df: pd.DataFrame, limit: int = 5) -> Dict[str, Any]:
    return {"products": _clean_records(top_products(_legacy(canonical_df), limit=limit)), "limit": limit}


def get_product_performance(canonical_df: pd.DataFrame, limit: int = 10) -> Dict[str, Any]:
    return {"products": _clean_records(enhanced_product_performance(canonical_df)[:limit]), "limit": limit}


def get_sales_trends(canonical_df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "daily_sales": _clean_records(sales_trend(_legacy(canonical_df))),
        "monthly_sales": _clean_records(monthly_sales(_legacy(canonical_df))),
    }


def get_inventory_risks(canonical_df: pd.DataFrame, limit: int = 20) -> Dict[str, Any]:
    rows = inventory_risk_analysis(canonical_df)
    return {"risks": _clean_records(rows[:limit]), "total_risks": len(rows), "limit": limit}


def get_restock_recommendations(canonical_df: pd.DataFrame, limit: int = 10) -> Dict[str, Any]:
    rows = inventory_risk_analysis(canonical_df)
    actionable = [r for r in rows if r.get("restock_review")]
    return {"recommendations": _clean_records(actionable[:limit]), "total": len(actionable), "limit": limit}


def get_profit_analysis(canonical_df: pd.DataFrame) -> Dict[str, Any]:
    summary = enhanced_business_summary(canonical_df)
    return {
        "gross_profit": summary.get("gross_profit"),
        "gross_margin": summary.get("gross_margin"),
        "has_cost_data": summary.get("capabilities", {}).get("has_cost_data", False),
        "limitation": None if summary.get("capabilities", {}).get("has_cost_data", False)
        else "Cost price is not present, so gross profit and margin cannot be calculated.",
    }


TOOL_REGISTRY = {
    "get_business_summary": get_business_summary,
    "get_top_products": get_top_products,
    "get_product_performance": get_product_performance,
    "get_sales_trends": get_sales_trends,
    "get_inventory_risks": get_inventory_risks,
    "get_restock_recommendations": get_restock_recommendations,
    "get_profit_analysis": get_profit_analysis,
}


def list_tools() -> List[Dict[str, str]]:
    descriptions = {
        "get_business_summary": "Overall revenue, orders, units, products and dataset capabilities.",
        "get_top_products": "Top products ranked by revenue.",
        "get_product_performance": "Product-level revenue, units and performance indicators.",
        "get_sales_trends": "Daily and monthly sales trends.",
        "get_inventory_risks": "Deterministic stock-risk analysis when inventory fields exist.",
        "get_restock_recommendations": "Restock review recommendations from stock and demand data.",
        "get_profit_analysis": "Gross profit and margin when cost data exists; otherwise explains the limitation.",
    }
    return [{"name": n, "description": descriptions[n]} for n in TOOL_REGISTRY]
