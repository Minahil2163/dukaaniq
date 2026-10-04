from pathlib import Path
from fastapi.responses import FileResponse
# backend/app.py

import shutil
import os
import json
from pathlib import Path
from typing import Optional

import pandas as pd

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
BASE_DIR = Path(__file__).resolve().parent
from analytics import (
    enhanced_business_summary,
    enhanced_product_performance,
    inventory_risk_analysis,
    REQUIRED_COLUMNS,
    analyze_dataframe,
    business_summary,
    country_performance,
    customer_performance,
    dataset_info,
    demand_analysis,
    monthly_sales,
    product_performance,
    sales_trend,
    top_products,
)

from ai import ask_business_analyst, run_business_agent
from data_contract import normalize_columns, validation_summary, to_legacy_analytics_schema, capabilities


# ============================================================
# APP CONFIG
# ============================================================

app = FastAPI(
    title="DukaanIQ API",
    version="5.0.0",
    description="AI-powered retail sales intelligence API",
)


app.add_middleware(
    CORSMiddleware,
    # Local development: supports the VS Code Live Server and file:// origins.
    # Credentials are not used by this API, so wildcard origins are safe here.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SAMPLE_FILE = DATA_DIR / "sample_sales.csv"
ACTIVE_FILE = DATA_DIR / "active_upload.csv"
ACTIVE_META_FILE = DATA_DIR / "active_upload_meta.json"


# ============================================================
# GLOBAL DATA
# ============================================================

sales_data: Optional[pd.DataFrame] = None
canonical_data: Optional[pd.DataFrame] = None
dataset_filename: Optional[str] = None


# ============================================================
# REQUEST MODELS
# ============================================================

class AIRequest(BaseModel):
    question: str


# ============================================================
# DATA LOADING
# ============================================================

def load_csv(file_path: Path) -> pd.DataFrame:

    try:
        return pd.read_csv(
            file_path,
            encoding="utf-8-sig",
        )

    except UnicodeDecodeError:
        return pd.read_csv(
            file_path,
            encoding="latin1",
        )

    except Exception as exc:
        raise ValueError(
            f"Could not read CSV: {exc}"
        )


def normalize_and_validate_dataset(df: pd.DataFrame):
    """Normalize supported retail CSV formats while preserving legacy analytics compatibility."""
    canonical_df, mapping = normalize_columns(df)
    analytics_df = to_legacy_analytics_schema(canonical_df)
    return canonical_df, analytics_df, mapping


def load_existing_data():

    global sales_data
    global canonical_data
    global dataset_filename

    # Upload-first architecture: never load the bundled/demo CSV automatically.
    # A dataset exists only after the user has uploaded a CSV and it has validated successfully.
    source_file = ACTIVE_FILE
    is_sample = False

    if not source_file.exists():
        sales_data = None
        canonical_data = None
        dataset_filename = None
        return

    try:
        df = load_csv(source_file)

        canonical_data, analytics_df, _ = normalize_and_validate_dataset(df)

        sales_data, _ = analyze_dataframe(analytics_df)

        if ACTIVE_META_FILE.exists():
            try:
                dataset_filename = json.loads(ACTIVE_META_FILE.read_text(encoding="utf-8")).get("filename", "uploaded.csv")
            except Exception:
                dataset_filename = "uploaded.csv"
        else:
            dataset_filename = "uploaded.csv"

        print(
            f"Loaded dataset: "
            f"{len(sales_data):,} rows"
        )

    except Exception as exc:

        sales_data = None
        canonical_data = None
        dataset_filename = None
        for stale in (ACTIVE_FILE, ACTIVE_META_FILE):
            try:
                if stale.exists():
                    stale.unlink()
            except Exception:
                pass

        print(
            f"Could not load existing dataset: {exc}"
        )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    load_existing_data()


# ============================================================
# ROOT
# ============================================================

@app.get("/api")
def root():

    return {
        "name": "DukaanIQ API",
        "version": "5.0.0",
        "status": "running",
        "dataset_loaded": sales_data is not None,
        "dataset_columns": REQUIRED_COLUMNS,
        "derived_columns": ["Revenue"],
        "canonical_schema": "DukaanIQ Retail Data Contract v1",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "dataset_loaded": sales_data is not None,
        "rows": (
            len(sales_data)
            if sales_data is not None
            else 0
        ),
    }


# ============================================================
# UPLOAD DATASET
# ============================================================

@app.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
):

    global sales_data
    global canonical_data
    global dataset_filename

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    temp_file = DATA_DIR / "_upload_temp.csv"

    # A new upload attempt replaces the current session. If validation fails,
    # the dashboard stays empty instead of showing the previous CSV.
    sales_data = None
    canonical_data = None
    dataset_filename = None
    for stale in (ACTIVE_FILE, ACTIVE_META_FILE):
        try:
            if stale.exists():
                stale.unlink()
        except Exception:
            pass

    try:

        # ----------------------------------------------------
        # Save temporary file
        # ----------------------------------------------------

        with temp_file.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # ----------------------------------------------------
        # Read CSV
        # ----------------------------------------------------

        df = load_csv(temp_file)

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        canonical_df, analytics_df, source_mapping = normalize_and_validate_dataset(df)

        # ----------------------------------------------------
        # Analyze
        # ----------------------------------------------------

        processed_df, mapping = analyze_dataframe(analytics_df)

        mapping = {**source_mapping, **mapping}

        if processed_df.empty:
            raise ValueError(
                "The uploaded CSV contains no usable rows."
            )

        # ----------------------------------------------------
        # Save active dataset
        # ----------------------------------------------------

        # Store uploads separately from the bundled demo dataset.
        # This prevents a restart from silently switching back to the demo file.
        os.replace(str(temp_file), str(ACTIVE_FILE))
        ACTIVE_META_FILE.write_text(json.dumps({"filename": file.filename}, ensure_ascii=False), encoding="utf-8")

        sales_data = processed_df
        canonical_data = canonical_df.copy()
        dataset_filename = file.filename

        # ----------------------------------------------------
        # Dataset information
        # ----------------------------------------------------

        info = dataset_info(
            sales_data
        )

        summary = business_summary(
            sales_data
        )

        print(
            f"Uploaded dataset: "
            f"{dataset_filename} | "
            f"{info['rows']:,} rows"
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {
            "success": True,
            "message": "Uploaded CSV is now the active DukaanIQ dataset. Dashboard and reports were recalculated from this file.",
            "filename": dataset_filename,
            "active_dataset": True,
            "rows": info["rows"],
            "columns": REQUIRED_COLUMNS,
            "derived_columns": ["Revenue"],
            "summary": info,
            "dashboard": {
                "revenue": summary["total_revenue"],
                "orders": summary["orders_count"],
                "units_sold": summary["units_sold"],
                "customers": summary["customers_count"],
                "products": summary["products_count"],
            },
            "mapping": mapping,
            "capabilities": capabilities(canonical_df).as_dict(),
            "validation": validation_summary(df, canonical_df, source_mapping),
        }

    except HTTPException:
        raise

    except Exception as exc:

        if temp_file.exists():

            try:
                temp_file.unlink()
            except Exception:
                pass

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# DATA CONTRACT
# ============================================================

@app.get("/data-contract")
def get_data_contract():
    return {
        "version": "1.0",
        "required_fields": [
            "product_id", "product_name", "quantity_sold",
            "sale_price", "sale_date"
        ],
        "optional_fields": [
            "order_id", "customer_id", "cost_price",
            "current_stock", "reorder_threshold", "category", "supplier"
        ],
        "capabilities": {
            "sales": True,
            "inventory": "current_stock",
            "profit": "cost_price",
            "restocking": "current_stock + reorder_threshold",
        },
    }


# ============================================================
# DATASET STATUS
# ============================================================

@app.get("/dataset")
def get_dataset():

    if sales_data is None:

        return {
            "loaded": False,
            "filename": None,
            "rows": 0,
            "columns": REQUIRED_COLUMNS,
            "derived_columns": ["Revenue"],
        }

    info = dataset_info(
        sales_data
    )

    return {
        "loaded": True,
        "filename": dataset_filename,
        "rows": info["rows"],
        "columns": REQUIRED_COLUMNS,
        "derived_columns": ["Revenue"],
        "info": info,
        "is_demo": False,
        "is_user_upload": True,
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def get_dashboard():
    if canonical_data is None or sales_data is None:
        return {"loaded": False, "message": "Please upload a CSV dataset first.", "kpis": {"revenue": 0, "orders": 0, "units_sold": 0, "customers": 0, "products": 0, "gross_profit": None, "stock_alerts": 0}, "top_products": [], "sales_trend": [], "countries": [], "inventory_risks": []}

    summary = enhanced_business_summary(canonical_data)
    legacy = business_summary(sales_data)
    caps = capabilities(canonical_data).as_dict()
    return {
        "loaded": True, "kpis": {"revenue": summary["revenue"], "gross_profit": summary["gross_profit"], "gross_margin": summary["gross_margin"], "orders": summary["orders"], "units_sold": summary["units_sold"], "customers": int(canonical_data["customer_id"].replace("", pd.NA).dropna().nunique()), "products": summary["products"], "stock_alerts": summary["restock_count"]},
        "revenue": summary["revenue"], "orders": summary["orders"], "units_sold": summary["units_sold"], "customers": int(canonical_data["customer_id"].replace("", pd.NA).dropna().nunique()), "products_count": summary["products"],
        "top_products": summary["top_products"], "low_performing_products": summary["low_performing_products"],
        "sales_trend": legacy["sales_trend"], "monthly_sales": legacy["monthly_sales"], "countries": legacy["country_performance"],
        "inventory_risks": summary["inventory_risks"], "restock_count": summary["restock_count"],
        "dataset_info": legacy["dataset_info"], "capabilities": caps,
        "has_profit": summary["has_profit"], "has_stock": summary["has_inventory"], "has_category": caps["has_category"],
        "dataset_filename": dataset_filename,
        "is_demo_dataset": False,
        "is_user_upload": True
    }


# ============================================================
# PRODUCTS
# ============================================================

@app.get("/products")
def get_products(
    limit: int = 100,
):

    if sales_data is None:

        return {
            "products": [],
            "total": 0,
        }

    limit = max(
        1,
        min(limit, 1000),
    )

    products = product_performance(
        sales_data
    )

    products = products[:limit]

    return {
        "products": products,
        "total": len(products),
    }


# ============================================================
# PRODUCT SEARCH
# ============================================================

@app.get("/products/search")
def search_products(
    q: str = "",
    limit: int = 50,
):

    if sales_data is None:

        return {
            "products": [],
            "total": 0,
        }

    query = q.strip().lower()

    products = product_performance(
        sales_data
    )

    if query:

        products = [
            product
            for product in products
            if query in str(
                product.get("product", "")
            ).lower()
            or query in str(
                product.get("stock_code", "")
            ).lower()
        ]

    limit = max(
        1,
        min(limit, 500),
    )

    products = products[:limit]

    return {
        "products": products,
        "total": len(products),
    }


# ============================================================
# INVENTORY / DEMAND
# ============================================================

@app.get("/inventory")
def get_inventory():

    if sales_data is None:

        return {
            "items": [],
            "total": 0,
            "type": "sales_demand",
        }

    demand = demand_analysis(
        sales_data
    )

    return {
        "items": demand,
        "total": len(demand),
        "type": "sales_demand",
    }


@app.get("/demand")
def get_demand(
    limit: int = 100,
):

    if sales_data is None:

        return {
            "products": [],
            "total": 0,
        }

    limit = max(
        1,
        min(limit, 1000),
    )

    demand = demand_analysis(
        sales_data
    )

    demand = demand[:limit]

    return {
        "products": demand,
        "total": len(demand),
    }


# ============================================================
# ANALYTICS - DAILY
# ============================================================

@app.get("/analytics/daily")
def get_daily_analytics():

    if sales_data is None:

        return {
            "data": [],
            "total": 0,
        }

    trend = sales_trend(
        sales_data
    )

    return {
        "data": trend,
        "total": len(trend),
    }


# ============================================================
# ANALYTICS - MONTHLY
# ============================================================

@app.get("/analytics/monthly")
def get_monthly_analytics():

    if sales_data is None:

        return {
            "data": [],
            "total": 0,
        }

    data = monthly_sales(
        sales_data
    )

    return {
        "data": data,
        "total": len(data),
    }


# ============================================================
# ANALYTICS - COUNTRIES
# ============================================================

@app.get("/analytics/countries")
def get_country_analytics():

    if sales_data is None:

        return {
            "data": [],
            "total": 0,
        }

    data = country_performance(
        sales_data
    )

    return {
        "data": data,
        "total": len(data),
    }


# ============================================================
# ANALYTICS - CUSTOMERS
# ============================================================

@app.get("/analytics/customers")
def get_customer_analytics():

    if sales_data is None:

        return {
            "data": [],
            "total": 0,
        }

    data = customer_performance(
        sales_data
    )

    return {
        "data": data,
        "total": len(data),
    }


# ============================================================
# TOP PRODUCTS
# ============================================================

@app.get("/analytics/top-products")
def get_top_products(
    limit: int = 10,
):

    if sales_data is None:

        return {
            "data": [],
            "total": 0,
        }

    limit = max(
        1,
        min(limit, 100),
    )

    data = top_products(
        sales_data,
        limit=limit,
    )

    return {
        "data": data,
        "total": len(data),
    }


# ============================================================
# FULL ANALYTICS
# ============================================================

@app.get("/analytics")
def get_analytics():

    if sales_data is None:

        return {
            "loaded": False,
            "message": "Please upload a CSV dataset first.",
        }

    daily = sales_trend(
        sales_data
    )

    monthly = monthly_sales(
        sales_data
    )

    countries = country_performance(
        sales_data
    )

    customers = customer_performance(
        sales_data
    )

    products = top_products(
        sales_data,
        limit=10,
    )

    demand = demand_analysis(
        sales_data
    )

    decision = enhanced_business_summary(canonical_data) if canonical_data is not None else {}
    return {
        "loaded": True,
        "daily_sales": daily, "monthly_sales": monthly, "countries": countries,
        "customers": customers[:100], "top_products": products, "demand": demand[:100],
        "decision_support": decision,
    }


# ============================================================
# AI ANALYST
# ============================================================

@app.post("/ask-ai")
def ask_ai(
    request: AIRequest,
):

    if sales_data is None:

        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV dataset first.",
        )

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    try:

        result = run_business_agent(canonical_data, question)

        return {
            "success": True,
            "question": question,
            **result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {exc}",
        )


# ============================================================
# PHASE 4 AI TOOL LAYER
# ============================================================

@app.get("/ai/tools")
def get_ai_tools():
    from ai_tools import list_tools
    return {"tools": list_tools()}


@app.get("/ai/knowledge")
def get_ai_knowledge():
    from rag import retrieve_knowledge
    return {"knowledge_base": retrieve_knowledge("retail inventory profit sales", limit=20)}



# ============================================================
# PHASE 3 DECISION SUPPORT
# ============================================================

@app.get("/analytics/inventory-risks")
def get_inventory_risks():
    if canonical_data is None:
        return {"loaded": False, "data": [], "total": 0}
    data = inventory_risk_analysis(canonical_data)
    return {"loaded": True, "data": data, "total": len(data)}


@app.get("/analytics/product-performance")
def get_enhanced_product_performance(limit: int = 100):
    if canonical_data is None:
        return {"loaded": False, "data": [], "total": 0}
    data = enhanced_product_performance(canonical_data)[:max(1, min(limit, 1000))]
    return {"loaded": True, "data": data, "total": len(data)}


@app.get("/analytics/decision-support")
def get_decision_support():
    if canonical_data is None:
        return {"loaded": False, "message": "Please upload a CSV dataset first."}
    return {"loaded": True, **enhanced_business_summary(canonical_data)}


# ============================================================
# REPORTS
# ============================================================

@app.get("/reports/decision-support")
def decision_support_report():
    if canonical_data is None:
        return {"loaded": False, "data": {}}
    return {"loaded": True, "data": enhanced_business_summary(canonical_data)}


@app.get("/reports/sales")
def sales_report():

    if sales_data is None:

        return {
            "loaded": False,
            "data": [],
        }

    data = sales_trend(
        sales_data
    )

    return {
        "loaded": True,
        "filename": dataset_filename,
        "data": data,
    }


@app.get("/reports/products")
def products_report():

    if sales_data is None:

        return {
            "loaded": False,
            "data": [],
        }

    data = product_performance(
        sales_data
    )

    return {
        "loaded": True,
        "filename": dataset_filename,
        "data": data,
    }


@app.get("/reports/customers")
def customers_report():

    if sales_data is None:

        return {
            "loaded": False,
            "data": [],
        }

    data = customer_performance(
        sales_data
    )

    return {
        "loaded": True,
        "filename": dataset_filename,
        "data": data,
    }


@app.get("/reports/countries")
def countries_report():

    if sales_data is None:

        return {
            "loaded": False,
            "data": [],
        }

    data = country_performance(
        sales_data
    )

    return {
        "loaded": True,
        "filename": dataset_filename,
        "data": data,
    }


# ============================================================
# FRONTEND (single-command local development)
# ============================================================
from fastapi.staticfiles import StaticFiles

# Path setup relative to current file location
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Serve static assets (CSS, JS) if present at root
if (PROJECT_ROOT / "style.css").exists():
    app.mount("/style.css", StaticFiles(file=PROJECT_ROOT / "style.css"), name="style")
if (PROJECT_ROOT / "script.js").exists():
    app.mount("/script.js", StaticFiles(file=PROJECT_ROOT / "script.js"), name="script")

@app.get("/", include_in_schema=False)
def frontend_index():
    # Check current directory and root parent directory
    possible_paths = [
        PROJECT_ROOT / "index.html",
        BASE_DIR / "index.html",
        Path("index.html").resolve(),
    ]
    
    for index_path in possible_paths:
        if index_path.exists():
            return FileResponse(index_path)
            
    return {"message": "Dukaaniq API is running live, but index.html was not found."}

# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
