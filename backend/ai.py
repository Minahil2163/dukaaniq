# backend/ai.py

import os
import re
from typing import Optional

from rag import retrieve_knowledge

import pandas as pd


# ============================================================
# DATASET CONFIGURATION
# ============================================================

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


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the raw DukaanIQ dataset.

    Supported raw columns:
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
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS + ["Revenue"])

    data = df.copy()

    # Make sure required columns exist
    for column in REQUIRED_COLUMNS:
        if column not in data.columns:
            data[column] = None

    # Keep only supported dataset columns
    data = data[REQUIRED_COLUMNS].copy()

    # Clean text columns
    for column in ["InvoiceNo", "StockCode", "Description", "Country"]:
        data[column] = data[column].fillna("").astype(str).str.strip()

    # Numeric columns
    data["Quantity"] = pd.to_numeric(
        data["Quantity"],
        errors="coerce"
    ).fillna(0)

    data["UnitPrice"] = pd.to_numeric(
        data["UnitPrice"],
        errors="coerce"
    ).fillna(0)

    data["CustomerID"] = pd.to_numeric(
        data["CustomerID"],
        errors="coerce"
    )

    # Date
    data["InvoiceDate"] = pd.to_datetime(
        data["InvoiceDate"],
        errors="coerce",
        dayfirst=True
    )

    # Derived revenue
    data["Revenue"] = data["Quantity"] * data["UnitPrice"]

    return data


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    return prepare_dataframe(df)


def _money(value: float) -> str:
    return f"{float(value):,.2f}"


def _number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{float(value):,.2f}"


def _find_product(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Search product by Description or StockCode.
    """

    if not query:
        return pd.DataFrame()

    query = query.strip().lower()

    mask = (
        df["Description"]
        .str.lower()
        .str.contains(query, na=False)
        |
        df["StockCode"]
        .str.lower()
        .str.contains(query, na=False)
    )

    return df[mask]


def _extract_product_query(question: str) -> Optional[str]:
    """
    Try to identify a product mentioned in the user's question.
    """

    patterns = [
        r"sales of (.+)",
        r"sale of (.+)",
        r"revenue of (.+)",
        r"revenue for (.+)",
        r"sales for (.+)",
        r"units of (.+)",
        r"quantity of (.+)",
        r"how many (.+) sold",
        r"how much did (.+) sell",
    ]

    question_lower = question.lower().strip()

    for pattern in patterns:
        match = re.search(pattern, question_lower)

        if match:
            value = match.group(1)

            value = re.sub(
                r"\b(today|this month|last month|this year)\b",
                "",
                value
            )

            value = value.strip(" ?.")

            if value:
                return value

    return None


# ============================================================
# GENERAL DATASET ANSWERS
# ============================================================

def answer_revenue(df: pd.DataFrame) -> str:
    total = df["Revenue"].sum()

    return (
        f"Total revenue is {_money(total)}. "
        f"Revenue is calculated as Quantity × UnitPrice."
    )


def answer_units(df: pd.DataFrame) -> str:
    units = df["Quantity"].sum()

    return f"Total units sold are {_number(units)}."


def answer_orders(df: pd.DataFrame) -> str:
    orders = df["InvoiceNo"].replace("", pd.NA).nunique()

    return f"Total orders/invoices are {_number(orders)}."


def answer_products(df: pd.DataFrame) -> str:
    products = df["StockCode"].replace("", pd.NA).nunique()

    return f"The dataset contains {_number(products)} unique products."


def answer_customers(df: pd.DataFrame) -> str:
    customers = df["CustomerID"].dropna().nunique()

    return f"There are {_number(customers)} unique customers with CustomerID."


def answer_countries(df: pd.DataFrame) -> str:
    countries = df["Country"].replace("", pd.NA).nunique()

    return f"The dataset contains {_number(countries)} countries."


# ============================================================
# PRICE ANSWERS
# ============================================================

def answer_highest_price(df: pd.DataFrame) -> str:
    if df.empty:
        return "No price data is available."

    row = df.loc[df["UnitPrice"].idxmax()]

    return (
        f"The highest unit price is {_money(row['UnitPrice'])} "
        f"for {row['Description']} "
        f"(StockCode: {row['StockCode']})."
    )


def answer_lowest_price(df: pd.DataFrame) -> str:
    valid = df[df["UnitPrice"] > 0]

    if valid.empty:
        return "No valid positive price data is available."

    row = valid.loc[valid["UnitPrice"].idxmin()]

    return (
        f"The lowest positive unit price is {_money(row['UnitPrice'])} "
        f"for {row['Description']} "
        f"(StockCode: {row['StockCode']})."
    )


def answer_average_price(df: pd.DataFrame) -> str:
    valid = df[df["UnitPrice"] > 0]

    if valid.empty:
        return "No valid price data is available."

    average = valid["UnitPrice"].mean()

    return f"The average unit price is {_money(average)}."


# ============================================================
# TOP PRODUCT ANSWERS
# ============================================================

def answer_top_products(
    df: pd.DataFrame,
    limit: int = 5
) -> str:

    grouped = (
        df.groupby(
            ["StockCode", "Description"],
            dropna=False
        )
        .agg(
            units_sold=("Quantity", "sum"),
            revenue=("Revenue", "sum")
        )
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(limit)
    )

    if grouped.empty:
        return "No product sales data is available."

    lines = ["Top products by revenue:"]

    for index, row in grouped.iterrows():

        stock_code, description = index

        lines.append(
            f"{description} "
            f"(StockCode {stock_code}) — "
            f"Revenue {_money(row['revenue'])}, "
            f"Units {_number(row['units_sold'])}"
        )

    return "\n".join(lines)


# ============================================================
# PRODUCT-SPECIFIC ANSWERS
# ============================================================

def answer_product_sales(
    df: pd.DataFrame,
    product_query: str
) -> str:

    matches = _find_product(df, product_query)

    if matches.empty:
        return (
            f"I couldn't find a product matching "
            f"'{product_query}'."
        )

    revenue = matches["Revenue"].sum()
    units = matches["Quantity"].sum()
    orders = matches["InvoiceNo"].replace("", pd.NA).nunique()

    product_names = (
        matches["Description"]
        .dropna()
        .astype(str)
        .unique()
    )

    name = product_names[0] if len(product_names) else product_query

    return (
        f"{name} generated revenue of {_money(revenue)}, "
        f"with {_number(units)} units sold across "
        f"{_number(orders)} orders."
    )


# ============================================================
# COUNTRY ANSWERS
# ============================================================

def answer_country_sales(
    df: pd.DataFrame,
    country_query: str
) -> str:

    matches = df[
        df["Country"]
        .str.lower()
        .str.contains(
            country_query.lower(),
            na=False
        )
    ]

    if matches.empty:
        return (
            f"I couldn't find sales data for "
            f"'{country_query}'."
        )

    revenue = matches["Revenue"].sum()
    units = matches["Quantity"].sum()
    orders = matches["InvoiceNo"].replace("", pd.NA).nunique()

    return (
        f"{country_query} generated revenue of "
        f"{_money(revenue)}, with "
        f"{_number(units)} units sold across "
        f"{_number(orders)} orders."
    )


def answer_top_countries(
    df: pd.DataFrame,
    limit: int = 5
) -> str:

    grouped = (
        df.groupby("Country", dropna=False)
        .agg(
            revenue=("Revenue", "sum"),
            units_sold=("Quantity", "sum"),
            orders=("InvoiceNo", "nunique")
        )
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(limit)
    )

    lines = ["Top countries by revenue:"]

    for country, row in grouped.iterrows():

        country_name = country if country else "Unknown"

        lines.append(
            f"{country_name} — "
            f"Revenue {_money(row['revenue'])}, "
            f"Units {_number(row['units_sold'])}"
        )

    return "\n".join(lines)


# ============================================================
# DATE / TIME ANSWERS
# ============================================================

def answer_sales_by_date(df: pd.DataFrame) -> str:

    valid = df.dropna(subset=["InvoiceDate"])

    if valid.empty:
        return "No valid InvoiceDate values are available."

    grouped = (
        valid.groupby(
            valid["InvoiceDate"].dt.date
        )
        .agg(
            revenue=("Revenue", "sum"),
            units=("Quantity", "sum"),
            orders=("InvoiceNo", "nunique")
        )
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(5)
    )

    lines = ["Top sales dates by revenue:"]

    for date, row in grouped.iterrows():

        lines.append(
            f"{date} — "
            f"Revenue {_money(row['revenue'])}, "
            f"Units {_number(row['units'])}, "
            f"Orders {_number(row['orders'])}"
        )

    return "\n".join(lines)


def answer_monthly_sales(df: pd.DataFrame) -> str:

    valid = df.dropna(subset=["InvoiceDate"])

    if valid.empty:
        return "No valid InvoiceDate values are available."

    grouped = (
        valid.assign(
            Month=valid["InvoiceDate"].dt.to_period("M")
        )
        .groupby("Month")
        .agg(
            revenue=("Revenue", "sum"),
            units=("Quantity", "sum"),
            orders=("InvoiceNo", "nunique")
        )
        .sort_index()
    )

    lines = ["Monthly sales:"]

    for month, row in grouped.tail(12).iterrows():

        lines.append(
            f"{month} — "
            f"Revenue {_money(row['revenue'])}, "
            f"Units {_number(row['units'])}, "
            f"Orders {_number(row['orders'])}"
        )

    return "\n".join(lines)


# ============================================================
# DEMAND ANSWER
# ============================================================

def answer_demand(df: pd.DataFrame) -> str:

    grouped = (
        df.groupby(
            ["StockCode", "Description"],
            dropna=False
        )
        .agg(
            units_sold=("Quantity", "sum"),
            revenue=("Revenue", "sum"),
            orders=("InvoiceNo", "nunique")
        )
        .sort_values(
            "units_sold",
            ascending=False
        )
        .head(5)
    )

    if grouped.empty:
        return "No product demand data is available."

    lines = ["Highest-demand products by units sold:"]

    for index, row in grouped.iterrows():

        stock_code, description = index

        lines.append(
            f"{description} "
            f"(StockCode {stock_code}) — "
            f"{_number(row['units_sold'])} units sold"
        )

    return "\n".join(lines)


# ============================================================
# PROFIT / STOCK HANDLING
# ============================================================

def answer_profit() -> str:

    return (
        "Profit cannot be calculated from this dataset because "
        "there is no cost or purchase-price column. "
        "The available financial measure is Revenue = "
        "Quantity × UnitPrice."
    )


def answer_restock() -> str:

    return (
        "Actual restocking cannot be determined from this dataset "
        "because there is no stock-on-hand or inventory quantity "
        "column. I can identify high-demand products using sales "
        "quantity instead."
    )


# ============================================================
# DATASET SUMMARY
# ============================================================

def answer_summary(df: pd.DataFrame) -> str:

    revenue = df["Revenue"].sum()
    units = df["Quantity"].sum()
    orders = df["InvoiceNo"].replace("", pd.NA).nunique()
    products = df["StockCode"].replace("", pd.NA).nunique()
    customers = df["CustomerID"].dropna().nunique()

    return (
        f"Dataset summary:\n"
        f"Revenue: {_money(revenue)}\n"
        f"Orders: {_number(orders)}\n"
        f"Units sold: {_number(units)}\n"
        f"Products: {_number(products)}\n"
        f"Customers: {_number(customers)}"
    )


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(question: str) -> str:

    q = question.lower().strip()

    if any(word in q for word in [
        "profit",
        "profits",
        "margin",
        "cost"
    ]):
        return "profit"

    if any(word in q for word in [
        "restock",
        "re-stock",
        "inventory",
        "stock level",
        "stock remaining"
    ]):
        return "restock"

    if any(word in q for word in [
        "revenue",
        "sales",
        "turnover",
        "income"
    ]):
        return "revenue"

    if any(word in q for word in [
        "unit price",
        "price",
        "expensive",
        "cheapest",
        "highest price",
        "lowest price"
    ]):
        if "highest" in q or "most expensive" in q:
            return "highest_price"

        if "lowest" in q or "cheapest" in q:
            return "lowest_price"

        return "average_price"

    if any(word in q for word in [
        "units sold",
        "quantity sold",
        "how many units"
    ]):
        return "units"

    if any(word in q for word in [
        "customer",
        "customers"
    ]):
        return "customers"

    if any(word in q for word in [
        "order",
        "orders",
        "invoice",
        "invoices",
        "transaction",
        "transactions"
    ]):
        return "orders"

    if any(word in q for word in [
        "country",
        "countries",
        "countries selling",
        "country sales"
    ]):
        if any(word in q for word in [
            "top",
            "best",
            "highest",
            "leading"
        ]):
            return "top_countries"

        return "country"

    if any(word in q for word in [
        "month",
        "monthly"
    ]):
        return "monthly"

    if any(word in q for word in [
        "day",
        "daily",
        "date"
    ]):
        return "daily"

    if any(word in q for word in [
        "demand",
        "high demand",
        "best selling",
        "most sold",
        "top product",
        "top products"
    ]):
        return "demand"

    if any(word in q for word in [
        "product",
        "products"
    ]):
        if any(word in q for word in [
            "top",
            "best",
            "best selling",
            "highest"
        ]):
            return "top_products"

        return "products"

    if any(word in q for word in [
        "summary",
        "overview",
        "dashboard",
        "business"
    ]):
        return "summary"

    return "unknown"


# ============================================================
# MAIN BUSINESS ANALYST
# ============================================================

def ask_business_analyst(
    df: pd.DataFrame,
    question: str
) -> str:

    if df is None or df.empty:
        return (
            "No sales dataset is loaded yet. "
            "Please upload the CSV first."
        )

    data = _safe_dataframe(df)

    if data.empty:
        return "The dataset is empty."

    question = (question or "").strip()

    if not question:
        return "Please enter a question about your sales data."

    intent = detect_intent(question)

    # --------------------------------------------------------
    # Product-specific questions
    # --------------------------------------------------------

    product_query = _extract_product_query(question)

    if product_query:
        matches = _find_product(data, product_query)

        if not matches.empty:

            # If question clearly asks about units
            if any(word in question.lower() for word in [
                "units",
                "quantity",
                "how many"
            ]):
                units = matches["Quantity"].sum()

                return (
                    f"{matches['Description'].iloc[0]} "
                    f"has {_number(units)} units sold."
                )

            # Otherwise provide product sales
            if any(word in question.lower() for word in [
                "sales",
                "revenue",
                "sold",
                "sell"
            ]):
                return answer_product_sales(
                    data,
                    product_query
                )

    # --------------------------------------------------------
    # Intent-based answers
    # --------------------------------------------------------

    if intent == "revenue":
        return answer_revenue(data)

    if intent == "units":
        return answer_units(data)

    if intent == "orders":
        return answer_orders(data)

    if intent == "products":
        return answer_products(data)

    if intent == "customers":
        return answer_customers(data)

    if intent == "countries":
        return answer_countries(data)

    if intent == "highest_price":
        return answer_highest_price(data)

    if intent == "lowest_price":
        return answer_lowest_price(data)

    if intent == "average_price":
        return answer_average_price(data)

    if intent == "top_products":
        return answer_top_products(data)

    if intent == "demand":
        return answer_demand(data)

    if intent == "top_countries":
        return answer_top_countries(data)

    if intent == "monthly":
        return answer_monthly_sales(data)

    if intent == "daily":
        return answer_sales_by_date(data)

    if intent == "profit":
        return answer_profit()

    if intent == "restock":
        return answer_restock()

    if intent == "summary":
        return answer_summary(data)

    # --------------------------------------------------------
    # Country-specific question fallback
    # --------------------------------------------------------

    countries = [
        str(country)
        for country in data["Country"].dropna().unique()
        if str(country).strip()
    ]

    question_lower = question.lower()

    for country in countries:

        if country.lower() in question_lower:

            return answer_country_sales(
                data,
                country
            )

    # --------------------------------------------------------
    # Generic fallback
    # --------------------------------------------------------

    return (
        "I can analyze this dataset using:\n"
        "• Revenue\n"
        "• Orders / InvoiceNo\n"
        "• Units sold / Quantity\n"
        "• Products / StockCode / Description\n"
        "• UnitPrice\n"
        "• Customers / CustomerID\n"
        "• Countries\n"
        "• Daily or monthly sales\n"
        "• Product demand\n\n"
        "I cannot calculate profit or actual stock levels "
        "because the dataset does not contain cost or stock columns."
    )


# ============================================================
# OPTIONAL GROQ FALLBACK
# ============================================================

def ask_groq(
    df: pd.DataFrame,
    question: str
) -> Optional[str]:

    """
    Optional LLM fallback.

    This function is intentionally conservative:
    the model receives only aggregated facts generated
    from the actual dataset and is instructed not to invent
    information.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return None

    try:
        from groq import Groq

        data = _safe_dataframe(df)

        context = {
            "total_revenue": float(data["Revenue"].sum()),
            "total_units": float(data["Quantity"].sum()),
            "orders": int(
                data["InvoiceNo"]
                .replace("", pd.NA)
                .nunique()
            ),
            "products": int(
                data["StockCode"]
                .replace("", pd.NA)
                .nunique()
            ),
            "customers": int(
                data["CustomerID"]
                .dropna()
                .nunique()
            ),
            "countries": int(
                data["Country"]
                .replace("", pd.NA)
                .nunique()
            ),
        }

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are DukaanIQ, a retail sales analyst. "
                        "Answer only from the provided dataset facts. "
                        "Never invent numbers. "
                        "Revenue is Quantity multiplied by UnitPrice. "
                        "There is no profit because cost is unavailable. "
                        "There is no stock level because inventory stock "
                        "is unavailable. "
                        "There is no product category column. "
                        "Keep answers concise."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Dataset facts:\n{context}\n\n"
                        f"Question: {question}"
                    ),
                },
            ],
        )

        return response.choices[0].message.content

    except Exception:
        return None


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def get_ai_answer(
    df: pd.DataFrame,
    question: str
) -> str:

    """
    Main public AI function.
    """

    answer = ask_business_analyst(
        df,
        question
    )

    return answer
# ============================================================
# PHASE 4 — TOOL-BASED AI AGENT
# ============================================================

from ai_tools import (
    get_business_summary,
    get_top_products,
    get_product_performance,
    get_sales_trends,
    get_inventory_risks,
    get_restock_recommendations,
    get_profit_analysis,
    list_tools,
)


def _select_tools(question: str) -> list[str]:
    q = question.lower()
    selected: list[str] = []

    def add(name: str):
        if name not in selected:
            selected.append(name)

    if any(x in q for x in ["restock", "reorder", "stock", "inventory", "out of stock"]):
        add("get_inventory_risks")
        add("get_restock_recommendations")
    if any(x in q for x in ["profit", "margin", "cost"]):
        add("get_profit_analysis")
    if any(x in q for x in ["trend", "monthly", "daily", "growth", "declin", "increase", "decrease"]):
        add("get_sales_trends")
    if any(x in q for x in ["top", "best", "selling", "product"]):
        add("get_top_products")
        add("get_product_performance")
    if any(x in q for x in ["summary", "overview", "business", "dashboard", "overall"]):
        add("get_business_summary")

    if not selected:
        add("get_business_summary")

    return selected


def run_business_agent(canonical_df: pd.DataFrame, question: str) -> dict:
    """Route a business question to deterministic tools, then interpret facts."""
    if canonical_df is None or canonical_df.empty:
        return {
            "answer": "No dataset is loaded yet. Please upload a CSV first.",
            "tools_used": [],
            "facts": {},
            "limitations": [],
        }

    tool_names = _select_tools(question)
    registry = {
        "get_business_summary": get_business_summary,
        "get_top_products": get_top_products,
        "get_product_performance": get_product_performance,
        "get_sales_trends": get_sales_trends,
        "get_inventory_risks": get_inventory_risks,
        "get_restock_recommendations": get_restock_recommendations,
        "get_profit_analysis": get_profit_analysis,
    }

    facts = {}
    limitations = []
    # Summary capabilities are needed whenever a decision depends on fields
    # such as inventory or cost data. This makes missing-data warnings explicit.
    if any(n in tool_names for n in ("get_inventory_risks", "get_restock_recommendations", "get_profit_analysis")) and "get_business_summary" not in tool_names:
        tool_names = ["get_business_summary", *tool_names]
    for name in tool_names:
        result = registry[name](canonical_df)
        facts[name] = result
        if result.get("limitation"):
            limitations.append(result["limitation"])
        if name in ("get_inventory_risks", "get_restock_recommendations") and result.get("total_risks", result.get("total", 0)) == 0:
            summary = facts.get("get_business_summary")
            if summary and not summary.get("capabilities", {}).get("has_inventory_data", False):
                limitations.append("Current dataset has no current-stock/reorder-threshold fields, so actual stock risk cannot be determined.")

    # Optional LLM interpretation over tool output only.
    answer = None
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are DukaanIQ, an AI retail business analyst. "
                            "The supplied JSON comes only from deterministic Python analytics tools. "
                            "Never invent, estimate, or alter numbers. Explain what the facts mean for a small retailer. "
                            "If a capability is unavailable, clearly say so. Give concise, actionable advice."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {question}\n\nTools used: {tool_names}\nTool facts:\n{facts}\nLimitations:\n{limitations}",
                    },
                ],
            )
            answer = response.choices[0].message.content
        except Exception:
            answer = None

    if not answer:
        # Safe deterministic fallback; still demonstrates the tool-driven architecture.
        summary = facts.get("get_business_summary", {})
        if "get_profit_analysis" in facts and facts["get_profit_analysis"].get("gross_profit") is None:
            answer = "I checked the profit analysis tool, but this dataset does not contain cost price, so gross profit and margin cannot be calculated."
        elif "get_top_products" in facts and "get_restock_recommendations" in facts:
            products = facts["get_top_products"].get("products", [])[:3]
            names = [str(p.get("product") or p.get("product_name") or p.get("product_id") or "Unknown product") for p in products]
            answer = (
                "Top revenue products are: " + ", ".join(names) + ". "
                "I also checked the restock tools, but this dataset has no current-stock/reorder-threshold data, so I cannot safely recommend which item to restock first."
            )
        elif "get_restock_recommendations" in facts and facts["get_restock_recommendations"].get("total", 0) == 0:
            answer = "I checked the inventory and restock tools, but the available data does not support an actionable restock recommendation."
        elif "get_top_products" in facts:
            products = facts["get_top_products"].get("products", [])[:3]
            names = [str(p.get("product_name") or p.get("Description") or p.get("product_id") or "Unknown product") for p in products]
            answer = "Top revenue products from the analytics tools: " + ", ".join(names) + "."
        else:
            answer = (
                f"The dataset contains {summary.get('products', 'N/A')} products and "
                f"revenue of {summary.get('revenue', 'N/A')}."
            )

    knowledge = retrieve_knowledge(question, limit=2)
    limitation_list = list(dict.fromkeys(limitations))

    # Build a visible, deterministic evidence section. The LLM answer remains
    # interpretation only; these fields are derived from tool output/RAG.
    evidence = []
    summary = facts.get("get_business_summary", {})
    if summary:
        for label, key in (("Revenue", "revenue"), ("Orders", "orders"), ("Units sold", "units_sold"), ("Products", "products")):
            if summary.get(key) is not None:
                evidence.append({"label": label, "value": summary[key]})
    top = facts.get("get_top_products", {}).get("products", [])[:3]
    for row in top:
        name = row.get("product") or row.get("product_name") or row.get("Description") or row.get("product_id")
        revenue = row.get("revenue")
        if name and revenue is not None:
            evidence.append({"label": str(name), "value": revenue})

    recommendation = "Use the evidence above together with the retail guidance below; do not infer unavailable metrics."
    if "restock" in question.lower() and limitation_list:
        recommendation = "Do not make a stock-order decision until current stock, reorder threshold and/or lead-time data are available."
    elif top:
        recommendation = "Prioritize the highest-revenue products for closer monitoring, while checking margin and inventory data before making purchasing decisions."

    return {
        "answer": answer,
        "structured_response": {
            "executive_answer": answer,
            "evidence": evidence[:8],
            "recommendation": recommendation,
            "knowledge_used": [{"id": k["id"], "title": k["title"], "topic": k["topic"], "text": k["text"]} for k in knowledge],
            "limitations": limitation_list,
        },
        "tools_used": tool_names,
        "tool_count": len(tool_names),
        "facts": facts,
        "limitations": limitation_list,
        "knowledge_used": [{"id": k["id"], "title": k["title"], "topic": k["topic"]} for k in knowledge],
        "agent_mode": "tool_based_rag",
    }
