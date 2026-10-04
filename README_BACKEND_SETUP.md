# DukaanIQ — Local Backend Setup

## Start the backend (Windows)

1. Extract the ZIP.
2. Double-click `START_DukaanIQ.bat`. The first run creates a virtual environment and installs the backend requirements.
3. Keep the terminal window open while using DukaanIQ.
4. Check `http://127.0.0.1:8000/health` and API docs at `http://127.0.0.1:8000/docs`.
5. Open `index.html` with VS Code Live Server (recommended) and use CSV Upload.

The frontend calls `http://127.0.0.1:8000`. If you see a backend connection error, ensure the terminal reports that Uvicorn is running on port 8000.

## Current CSV format

The current analytics engine expects these exact column names:

`InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`

The included Online Retail sample uses this schema. A generic file containing only `product,revenue` is not compatible with the current analytics engine; schema mapping will be a later integration task.

## Important limitations in this version

- One active dataset is supported and stored as `backend/data/sales.csv`.
- Revenue, orders, units, products, customers and sales trends are derived from the uploaded dataset.
- Profit and on-hand inventory are not inferred when the source file does not contain cost/stock data.
- Do not commit API keys or `.env` files to GitHub.
