# Roel's Guitar Shop database

SQLite implementation of the 20 core tables in [ARCHITECTURE.md](../ARCHITECTURE.md), with exactly **10 demo records per table (200 total)**.

## Setup

Requires Python 3.10+, Flask, and SQLite 3.37+ (included with current Python builds). No database server is needed.

```powershell
python -m pip install -r requirements.txt
python -m flask --app app db-init
python -m flask --app app db-seed
python -m flask --app app db-check
python -m unittest tests.test_database -v
```

The default file is `database/data/roels-guitar-shop.sqlite`. Set `$env:SHOP_DB_PATH = "C:\path\demo.sqlite"` to use a separate database. Schema initialization is automatic when the Flask application starts and preserves existing version-1 databases. Seeding requires empty tables and refuses to replace existing records. [demo-queries.sql](demo-queries.sql) contains sample reports.

## Tables and relationships

| Table | Purpose and main relationships |
| --- | --- |
| `roles` | Staff roles; users reference one role |
| `permissions` | Permission codes |
| `role_permissions` | Many-to-many role/permission assignments |
| `users` | Staff accounts, salted password hashes, role FK |
| `categories` | Product classifications |
| `brands` | Product manufacturers |
| `products` | SKU, barcode, category/brand FKs, prices, reorder threshold |
| `suppliers` | Supplier contacts |
| `customers` | Optional customer identities for sales |
| `purchases` | Supplier purchase headers and totals |
| `purchase_items` | Ordered products, costs, ordered/received quantities |
| `sales` | Receipt, optional customer, cashier, totals and lifecycle |
| `sale_items` | Products sold; historical name/SKU/price/cost snapshots |
| `payments` | Multiple payments per sale, methods, tender/change and status |
| `inventory_movements` | Immutable signed stock ledger with item-level source FKs |
| `returns` | Original sale, return status, refund and processing user |
| `return_items` | Original sale items, quantities, refund amount and restock decision |
| `expenses` | Expense category, amount, date, method and recording user |
| `settings` | Validated JSON configuration values |
| `audit_logs` | Immutable user/action/entity history with JSON details |

All tables use SQLite STRICT typing, string identifiers and foreign keys. Catalog/contact/user records support archiving with `is_active`. Identifiers created by the demo are readable (`PRD-001`, `SAL-001`); future application records can use UUIDs. Foreign keys preserve referenced history. Money is stored as integer **PHP centavos** (`4250000` means PHP 42,500.00). Timestamps use UTC ISO strings; daily report views group by Manila time (UTC+08:00). The seed uses fixed September 2026 dates to keep demonstrations reproducible.

## Stock and transaction rules

`product_inventory` computes stock from the movement ledger, including zero-stock products. It also joins category/brand names and derives the stock status. There is no independently editable stock counter. `sale_balances` shows paid and refunded totals. `daily_sales` reports gross sales; `daily_refunds` reports refunds on their processing dates. Pending payments and requested returns do not affect those totals.

Build documents as drafts, then update their status inside `with transaction(db):` from [__init__.py](__init__.py):

1. **Complete a sale:** insert items with historical product values, set header subtotal/discount/tax, record completed payments, then set `status = 'completed'` and `completed_at`. Triggers validate item/payment totals, write stock-out entries, and reject negative stock.
2. **Receive a purchase:** set the items' `received_quantity`, then set the purchase to `received` with `received_at`. Triggers require complete receipt quantities and matching totals, then post outstanding stock-in quantities.
3. **Complete a return:** insert a requested return and its original sale items, then set `status = 'completed'` and `completed_at`. Triggers validate original sale ownership, cumulative returned quantities, refund totals and the original sale's refund ceiling. Only resellable items marked `restock = 1` create stock-in entries.
4. Append an audit log in the same transaction for the business action. Roll back the whole transaction when any step fails.

Finalized documents and their items/payments are locked against edits. Inventory and audit entries are immutable; corrections require new records. The schema supports purchase status `partially_received` and multiple movement entries per purchase item, but incremental receipt orchestration remains a future application-service responsibility. Such a service must update received quantities and append the corresponding movements atomically; full receiving posts only the remaining quantity.

Services must still enforce user permissions, active catalog records, tax/discount policy, per-line refund allocation, and audit creation. Database constraints complement those services. SQL status changes record local business events; they do not process external card/GCash payments.

## Demo coverage

The 10 products match the current Products page's names and prices. There are four opening stock entries, two received purchases, two completed sales and two completed restocked returns: exactly **10 inventory movements**. Remaining purchases and sales are draft/ordered/held examples. Eight return requests and eight payments remain pending. The Flask pages display these actual stock balances, including active, low-stock and zero-stock examples.

All names/contact details are fictional demo records. Ten roles and ten sample role-permission assignments illustrate the relationship; expand the permission matrix when implementing authorization. `*` is intended as the administrator's application-level wildcard; SQLite itself does not interpret permission codes.

Demo accounts are `admin.demo` and `staff2.demo` through `staff10.demo`, with password `GuitarDemo!2026`. Only independently salted scrypt hashes are stored in the database, encoded as `scrypt$N$r$p$salt$hash`. The app supports credential login for the Administrator, Manager, and Cashier accounts (`admin.demo`, `staff2.demo`, `staff3.demo`). Its optional demo selector uses those same database users; other roles are reserved for future modules. Set `SHOP_DEMO_LOGIN=false` to require passwords.

## Flask integration

`database/__init__.py` supplies one SQLite connection per Flask request and closes it at teardown. `services.py` queries the catalog and records checkout within `BEGIN IMMEDIATE`, including payment, stock posting via triggers, and audit creation. Prices and tax are calculated on the server. The browser receives HTML from Jinja templates and never executes SQL.

`demo-data.json` preserves the original seed records and status transitions in execution order. `seed.py` replays them in a single transaction and generates a fresh scrypt salt for every account. Passwords and hash values are not embedded in the JSON fixture. Sample record counts and ledger totals remain identical to the original dataset.
