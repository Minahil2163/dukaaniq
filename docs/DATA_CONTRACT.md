# DukaanIQ Data Contract v1

## Required fields

| Canonical field | Meaning |
|---|---|
| `product_id` | Stable product/SKU identifier |
| `product_name` | Human-readable product name |
| `quantity_sold` | Units sold in the transaction |
| `sale_price` | Selling price per unit |
| `sale_date` | Transaction date/time |

## Optional fields

| Canonical field | Enables |
|---|---|
| `order_id` | Order/invoice metrics |
| `customer_id` | Customer metrics |
| `cost_price` | Gross profit and gross margin |
| `current_stock` | Inventory monitoring and stock coverage |
| `reorder_threshold` | Restock alerts |
| `category` | Category analysis |
| `supplier` | Supplier-aware recommendations |
| `country` | Existing geographic analysis |

## Derived fields

- `revenue = quantity_sold × sale_price`
- `gross_profit = quantity_sold × (sale_price − cost_price)` when cost is available
- `gross_margin = gross_profit / revenue × 100` when revenue is non-zero

## Compatibility

The existing Online Retail CSV is accepted through aliases such as `StockCode → product_id`, `Description → product_name`, `Quantity → quantity_sold`, `UnitPrice → sale_price`, and `InvoiceDate → sale_date`.

Inventory and profit are never inferred from sales-only data.
