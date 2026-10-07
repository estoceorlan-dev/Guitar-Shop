-- Open database/data/roels-guitar-shop.sqlite in your preferred SQLite viewer.
-- These are read-only demo queries. Monetary outputs below are displayed in pesos.

SELECT sku, name, category_name, brand_name,
  selling_price / 100.0 AS price_php, stock_quantity, stock_status
FROM product_inventory ORDER BY name;

SELECT receipt_number, status, total_amount / 100.0 AS total_php,
  paid_amount / 100.0 AS paid_php, refunded_amount / 100.0 AS refunded_php,
  (paid_amount - refunded_amount) / 100.0 AS net_paid_php
FROM sale_balances ORDER BY created_at DESC, receipt_number;

SELECT p.purchase_number, s.name AS supplier, p.status,
  p.total_amount / 100.0 AS total_php, i.quantity, i.received_quantity
FROM purchases p JOIN suppliers s ON s.id = p.supplier_id
JOIN purchase_items i ON i.purchase_id = p.id ORDER BY p.purchase_number;

SELECT p.name, m.movement_type, m.quantity_delta, m.reason, m.created_at
FROM inventory_movements m JOIN products p ON p.id = m.product_id
ORDER BY m.created_at, m.id;

SELECT sale_date, transactions, gross_sales / 100.0 AS gross_sales_php FROM daily_sales;
SELECT refund_date, transactions, refund_amount / 100.0 AS refunds_php FROM daily_refunds;

SELECT u.username, u.full_name, r.name AS role, p.code AS permission
FROM users u JOIN roles r ON r.id = u.role_id
JOIN role_permissions rp ON rp.role_id = r.id
JOIN permissions p ON p.id = rp.permission_id ORDER BY u.username;

SELECT category, sum(amount) / 100.0 AS expense_php FROM expenses GROUP BY category;

SELECT sum(stock_quantity * cost_price) / 100.0 AS inventory_cost_php FROM product_inventory;
