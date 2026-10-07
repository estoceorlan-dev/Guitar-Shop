# Roel's Guitar Shop

A local Flask application with server-rendered HTML pages in `templates/`, CSS and SVG assets in `static/`, and a SQLite database. Dashboard, product search, role-based login, and point of sale run through Python without a frontend build step.

## Run locally

Requires Python 3.10+ with SQLite 3.37+.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app db-seed
.\.venv\Scripts\python -m flask --app app run --debug
```

Open http://127.0.0.1:5000. If your database already contains records, skip `db-seed`; it intentionally refuses to overwrite existing data. The schema initializes automatically when the app starts.

The login page retains the demo role selector for Administrator, Manager, and Cashier. You can also sign in with `admin.demo`, `staff2.demo` (Manager), or `staff3.demo` (Cashier), using password `GuitarDemo!2026`. Set `$env:SHOP_DEMO_LOGIN = "false"` to require password login.

Administrator and Manager can access dashboard, products, and POS. Cashier can access POS. Product searches use GET forms; cart actions, logout, and payment recording use POST forms with CSRF protection. The cart persists in the signed Flask session. Checkout reloads database prices and stock, calculates integer-centavo totals, and atomically records the sale, payment, inventory movement, and audit event. Card and GCash options record a payment already received; external payment processing is not integrated.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SHOP_DB_PATH` | `database/data/roels-guitar-shop.sqlite` | Choose the local SQLite file |
| `SECRET_KEY` | Random key persisted in `instance/secret-key` | Sign session cookies |
| `SHOP_DEMO_LOGIN` | `true` | Enable the three fictional demo account buttons |

The Flask development server binds to localhost. For deployment, use a WSGI server with the `app:create_app()` application factory and configure a stable secret, HTTPS, secure session cookies, and password-only login.

## Database and validation

```powershell
python -m flask --app app db-init
python -m flask --app app db-check
python -m unittest discover -s tests -v
```

`db-init` is repeatable. `db-seed` inserts the original fictional dataset: 20 tables with 10 records each, including purchases, sales, returns, and immutable stock/audit history. Existing version-1 databases and scrypt password hashes remain compatible. Tests use disposable databases and do not change the shop's data.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the Flask architecture and planned modules, and [database/README.md](database/README.md) for database rules. Product editing, purchasing, inventory adjustments, customers, returns, settings, and extended reports remain planned modules; the navigation shows the currently implemented pages.
