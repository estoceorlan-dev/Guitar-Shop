-- Roel's Guitar Shop / SQLite 3.37+ / schema version 1
-- Amounts are integer PHP centavos. Dates are ISO 8601 UTC strings.
-- Enable foreign_keys on EVERY connection, not just during initialization.
PRAGMA foreign_keys = ON;

CREATE TABLE roles (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  description TEXT NOT NULL DEFAULT '',
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
) STRICT;

CREATE TABLE permissions (
  id TEXT PRIMARY KEY NOT NULL,
  code TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL
) STRICT;

CREATE TABLE role_permissions (
  role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id TEXT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
) STRICT;

CREATE TABLE users (
  id TEXT PRIMARY KEY NOT NULL,
  role_id TEXT NOT NULL REFERENCES roles(id),
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  full_name TEXT NOT NULL,
  email TEXT UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL CHECK (password_hash LIKE 'scrypt$%'),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

CREATE TABLE categories (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  description TEXT NOT NULL DEFAULT '',
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
) STRICT;

CREATE TABLE brands (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  description TEXT NOT NULL DEFAULT '',
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
) STRICT;

CREATE TABLE products (
  id TEXT PRIMARY KEY NOT NULL,
  sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
  barcode TEXT UNIQUE,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  category_id TEXT NOT NULL REFERENCES categories(id),
  brand_id TEXT REFERENCES brands(id),
  cost_price INTEGER NOT NULL CHECK (cost_price >= 0),
  selling_price INTEGER NOT NULL CHECK (selling_price >= 0),
  reorder_level INTEGER NOT NULL DEFAULT 5 CHECK (reorder_level >= 0),
  unit TEXT NOT NULL DEFAULT 'piece',
  image_url TEXT,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

CREATE TABLE suppliers (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  contact_person TEXT,
  phone TEXT,
  email TEXT,
  address TEXT,
  notes TEXT NOT NULL DEFAULT '',
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
) STRICT;

CREATE TABLE customers (
  id TEXT PRIMARY KEY NOT NULL,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  address TEXT,
  notes TEXT NOT NULL DEFAULT '',
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
) STRICT;

CREATE TABLE purchases (
  id TEXT PRIMARY KEY NOT NULL,
  purchase_number TEXT NOT NULL UNIQUE,
  supplier_id TEXT NOT NULL REFERENCES suppliers(id),
  created_by TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','ordered','partially_received','received','cancelled')),
  subtotal INTEGER NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
  tax_amount INTEGER NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
  shipping_amount INTEGER NOT NULL DEFAULT 0 CHECK (shipping_amount >= 0),
  total_amount INTEGER GENERATED ALWAYS AS (subtotal + tax_amount + shipping_amount) STORED,
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  received_at TEXT,
  CHECK (status <> 'received' OR received_at IS NOT NULL)
) STRICT;

CREATE TABLE purchase_items (
  id TEXT PRIMARY KEY NOT NULL,
  purchase_id TEXT NOT NULL REFERENCES purchases(id),
  product_id TEXT NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  received_quantity INTEGER NOT NULL DEFAULT 0 CHECK (received_quantity BETWEEN 0 AND quantity),
  unit_cost INTEGER NOT NULL CHECK (unit_cost >= 0),
  line_total INTEGER GENERATED ALWAYS AS (quantity * unit_cost) STORED
) STRICT;

CREATE TABLE sales (
  id TEXT PRIMARY KEY NOT NULL,
  receipt_number TEXT NOT NULL UNIQUE,
  customer_id TEXT REFERENCES customers(id),
  cashier_id TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','held','completed','cancelled')),
  subtotal INTEGER NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
  discount_amount INTEGER NOT NULL DEFAULT 0 CHECK (discount_amount BETWEEN 0 AND subtotal),
  tax_amount INTEGER NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
  total_amount INTEGER GENERATED ALWAYS AS (subtotal - discount_amount + tax_amount) STORED,
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  completed_at TEXT,
  CHECK (status <> 'completed' OR completed_at IS NOT NULL)
) STRICT;

CREATE TABLE sale_items (
  id TEXT PRIMARY KEY NOT NULL,
  sale_id TEXT NOT NULL REFERENCES sales(id),
  product_id TEXT NOT NULL REFERENCES products(id),
  product_name TEXT NOT NULL,
  sku TEXT NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
  unit_cost INTEGER NOT NULL CHECK (unit_cost >= 0),
  discount_amount INTEGER NOT NULL DEFAULT 0 CHECK (discount_amount BETWEEN 0 AND quantity * unit_price),
  line_total INTEGER GENERATED ALWAYS AS (quantity * unit_price - discount_amount) STORED
) STRICT;

CREATE TABLE payments (
  id TEXT PRIMARY KEY NOT NULL,
  sale_id TEXT NOT NULL REFERENCES sales(id),
  method TEXT NOT NULL CHECK (method IN ('cash','gcash','card','bank_transfer','other')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','completed','failed','cancelled')),
  amount INTEGER NOT NULL CHECK (amount > 0),
  tendered_amount INTEGER CHECK (tendered_amount >= amount),
  change_amount INTEGER GENERATED ALWAYS AS (coalesce(tendered_amount,amount) - amount) STORED,
  reference_number TEXT,
  paid_at TEXT,
  CHECK (status <> 'completed' OR paid_at IS NOT NULL)
) STRICT;

CREATE TABLE returns (
  id TEXT PRIMARY KEY NOT NULL,
  return_number TEXT NOT NULL UNIQUE,
  sale_id TEXT NOT NULL REFERENCES sales(id),
  processed_by TEXT NOT NULL REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','completed','rejected')),
  reason TEXT NOT NULL,
  refund_amount INTEGER NOT NULL CHECK (refund_amount >= 0),
  refund_method TEXT NOT NULL CHECK (refund_method IN ('cash','gcash','card','bank_transfer','other')),
  refund_reference TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  completed_at TEXT,
  CHECK (status <> 'completed' OR completed_at IS NOT NULL)
) STRICT;

CREATE TABLE return_items (
  id TEXT PRIMARY KEY NOT NULL,
  return_id TEXT NOT NULL REFERENCES returns(id),
  sale_item_id TEXT NOT NULL REFERENCES sale_items(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  refund_amount INTEGER NOT NULL CHECK (refund_amount >= 0),
  restock INTEGER NOT NULL DEFAULT 1 CHECK (restock IN (0,1)),
  condition TEXT NOT NULL DEFAULT 'resellable' CHECK (condition IN ('resellable','damaged','defective')),
  UNIQUE (return_id, sale_item_id),
  CHECK (restock = 0 OR condition = 'resellable')
) STRICT;

CREATE TABLE inventory_movements (
  id TEXT PRIMARY KEY NOT NULL,
  product_id TEXT NOT NULL REFERENCES products(id),
  movement_type TEXT NOT NULL CHECK (movement_type IN
    ('opening','purchase','sale','return','adjustment_in','adjustment_out','damaged','lost','supplier_return')),
  quantity_delta INTEGER NOT NULL CHECK (quantity_delta <> 0),
  purchase_item_id TEXT REFERENCES purchase_items(id),
  sale_item_id TEXT UNIQUE REFERENCES sale_items(id),
  return_item_id TEXT UNIQUE REFERENCES return_items(id),
  created_by TEXT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  CHECK ((movement_type IN ('opening','purchase','return','adjustment_in') AND quantity_delta > 0)
    OR (movement_type IN ('sale','adjustment_out','damaged','lost','supplier_return') AND quantity_delta < 0)),
  CHECK ((movement_type = 'purchase' AND purchase_item_id IS NOT NULL AND sale_item_id IS NULL AND return_item_id IS NULL)
    OR (movement_type = 'sale' AND sale_item_id IS NOT NULL AND purchase_item_id IS NULL AND return_item_id IS NULL)
    OR (movement_type = 'return' AND return_item_id IS NOT NULL AND sale_item_id IS NULL AND purchase_item_id IS NULL)
    OR (movement_type NOT IN ('purchase','sale','return') AND purchase_item_id IS NULL AND sale_item_id IS NULL AND return_item_id IS NULL))
) STRICT;

CREATE TABLE expenses (
  id TEXT PRIMARY KEY NOT NULL,
  category TEXT NOT NULL,
  amount INTEGER NOT NULL CHECK (amount > 0),
  description TEXT NOT NULL,
  expense_date TEXT NOT NULL,
  payment_method TEXT NOT NULL CHECK (payment_method IN ('cash','gcash','card','bank_transfer','other')),
  recorded_by TEXT NOT NULL REFERENCES users(id),
  reference_number TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

CREATE TABLE settings (
  key TEXT PRIMARY KEY NOT NULL,
  value_json TEXT NOT NULL CHECK (json_valid(value_json)),
  description TEXT NOT NULL,
  updated_by TEXT REFERENCES users(id),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

CREATE TABLE audit_logs (
  id TEXT PRIMARY KEY NOT NULL,
  user_id TEXT REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  old_value TEXT CHECK (old_value IS NULL OR json_valid(old_value)),
  new_value TEXT CHECK (new_value IS NULL OR json_valid(new_value)),
  metadata TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata)),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
) STRICT;

CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);
CREATE INDEX idx_products_name ON products(name COLLATE NOCASE);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_purchases_supplier_date ON purchases(supplier_id, created_at);
CREATE INDEX idx_purchase_items_purchase ON purchase_items(purchase_id);
CREATE INDEX idx_purchase_items_product ON purchase_items(product_id);
CREATE INDEX idx_sales_status_date ON sales(status, completed_at);
CREATE INDEX idx_sales_customer_date ON sales(customer_id, created_at);
CREATE INDEX idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX idx_sale_items_product ON sale_items(product_id);
CREATE INDEX idx_payments_sale_status ON payments(sale_id, status);
CREATE INDEX idx_returns_sale ON returns(sale_id);
CREATE INDEX idx_return_items_sale_item ON return_items(sale_item_id);
CREATE INDEX idx_movements_product_date ON inventory_movements(product_id, created_at);
CREATE INDEX idx_movements_purchase ON inventory_movements(purchase_item_id);
CREATE INDEX idx_expenses_date ON expenses(expense_date);
CREATE INDEX idx_audit_entity_date ON audit_logs(entity_type, entity_id, created_at);

-- Stock is calculated from the immutable ledger, so a cached quantity cannot drift.
CREATE VIEW product_inventory AS
SELECT p.*, c.name AS category_name, b.name AS brand_name,
  coalesce(m.stock_quantity,0) AS stock_quantity,
  CASE WHEN p.is_active = 0 THEN 'Archived'
    WHEN coalesce(m.stock_quantity,0) = 0 THEN 'Out of Stock'
    WHEN m.stock_quantity <= p.reorder_level THEN 'Low Stock'
    ELSE 'Active' END AS stock_status
FROM products p
JOIN categories c ON c.id = p.category_id
LEFT JOIN brands b ON b.id = p.brand_id
LEFT JOIN (SELECT product_id, sum(quantity_delta) AS stock_quantity
  FROM inventory_movements GROUP BY product_id) m ON m.product_id = p.id;

CREATE VIEW sale_balances AS
SELECT s.*,
  coalesce((SELECT sum(amount) FROM payments WHERE sale_id = s.id AND status = 'completed'),0) AS paid_amount,
  coalesce((SELECT sum(refund_amount) FROM returns WHERE sale_id = s.id AND status = 'completed'),0) AS refunded_amount
FROM sales s;

-- Daily groups follow the shop's Asia/Manila timezone (UTC+08:00).
CREATE VIEW daily_sales AS
SELECT date(completed_at, '+8 hours') AS sale_date, count(*) AS transactions,
  sum(subtotal) AS subtotal, sum(discount_amount) AS discounts,
  sum(tax_amount) AS tax_amount, sum(total_amount) AS gross_sales
FROM sales WHERE status = 'completed' GROUP BY date(completed_at, '+8 hours');

CREATE VIEW daily_refunds AS
SELECT date(completed_at, '+8 hours') AS refund_date,
  count(*) AS transactions, sum(refund_amount) AS refund_amount
FROM returns WHERE status = 'completed' GROUP BY date(completed_at, '+8 hours');

CREATE TRIGGER inventory_no_negative BEFORE INSERT ON inventory_movements
WHEN NEW.quantity_delta + coalesce((SELECT sum(quantity_delta) FROM inventory_movements WHERE product_id = NEW.product_id),0) < 0
BEGIN SELECT RAISE(ABORT, 'Insufficient stock'); END;

CREATE TRIGGER inventory_source_matches BEFORE INSERT ON inventory_movements
BEGIN
  SELECT CASE WHEN NEW.sale_item_id IS NOT NULL AND NOT EXISTS
    (SELECT 1 FROM sale_items i JOIN sales s ON s.id = i.sale_id WHERE i.id = NEW.sale_item_id
      AND i.product_id = NEW.product_id AND NEW.quantity_delta = -i.quantity AND s.status = 'completed')
    THEN RAISE(ABORT, 'Sale movement does not match completed sale item') END;
  SELECT CASE WHEN NEW.purchase_item_id IS NOT NULL AND NOT EXISTS
    (SELECT 1 FROM purchase_items i JOIN purchases p ON p.id = i.purchase_id WHERE i.id = NEW.purchase_item_id
      AND i.product_id = NEW.product_id AND p.status IN ('partially_received','received')
      AND NEW.quantity_delta + coalesce((SELECT sum(quantity_delta) FROM inventory_movements WHERE purchase_item_id = i.id),0) <= i.received_quantity)
    THEN RAISE(ABORT, 'Purchase movement exceeds received quantity') END;
  SELECT CASE WHEN NEW.return_item_id IS NOT NULL AND NOT EXISTS
    (SELECT 1 FROM return_items i JOIN sale_items si ON si.id = i.sale_item_id JOIN returns r ON r.id = i.return_id
      WHERE i.id = NEW.return_item_id AND si.product_id = NEW.product_id
        AND NEW.quantity_delta = i.quantity AND i.restock = 1 AND r.status = 'completed')
    THEN RAISE(ABORT, 'Return movement does not match completed return item') END;
END;

CREATE TRIGGER inventory_no_update BEFORE UPDATE ON inventory_movements
BEGIN SELECT RAISE(ABORT, 'Inventory history is immutable; append a correction'); END;
CREATE TRIGGER inventory_no_delete BEFORE DELETE ON inventory_movements
BEGIN SELECT RAISE(ABORT, 'Inventory history is immutable; append a correction'); END;
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Audit history is immutable'); END;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_logs
BEGIN SELECT RAISE(ABORT, 'Audit history is immutable'); END;

-- Terminal documents must be assembled as drafts, then posted atomically.
CREATE TRIGGER sales_insert_draft BEFORE INSERT ON sales WHEN NEW.status = 'completed'
BEGIN SELECT RAISE(ABORT, 'Create sale as draft before completing'); END;
CREATE TRIGGER purchases_insert_draft BEFORE INSERT ON purchases WHEN NEW.status IN ('received','partially_received')
BEGIN SELECT RAISE(ABORT, 'Create purchase before receiving'); END;
CREATE TRIGGER returns_insert_requested BEFORE INSERT ON returns WHEN NEW.status = 'completed'
BEGIN SELECT RAISE(ABORT, 'Create return as requested before completing'); END;

CREATE TRIGGER sales_lock BEFORE UPDATE ON sales WHEN OLD.status IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale is immutable; use a return for refunds'); END;
CREATE TRIGGER purchases_lock BEFORE UPDATE ON purchases WHEN OLD.status IN ('received','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized purchase is immutable'); END;
CREATE TRIGGER returns_lock BEFORE UPDATE ON returns WHEN OLD.status IN ('completed','rejected')
BEGIN SELECT RAISE(ABORT, 'Finalized return is immutable'); END;

CREATE TRIGGER sales_complete BEFORE UPDATE OF status ON sales WHEN NEW.status = 'completed'
BEGIN
  SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM sale_items WHERE sale_id = NEW.id)
    OR NEW.subtotal <> (SELECT sum(line_total) FROM sale_items WHERE sale_id = NEW.id)
    THEN RAISE(ABORT, 'Sale subtotal does not match items') END;
  SELECT CASE WHEN coalesce((SELECT sum(amount) FROM payments WHERE sale_id = NEW.id AND status = 'completed'),0)
    <> NEW.subtotal - NEW.discount_amount + NEW.tax_amount
    THEN RAISE(ABORT, 'Completed payments must equal sale total') END;
END;

CREATE TRIGGER sales_post_stock AFTER UPDATE OF status ON sales WHEN NEW.status = 'completed'
BEGIN
  INSERT INTO inventory_movements(id, product_id, movement_type, quantity_delta, sale_item_id, created_by, reason, created_at)
  SELECT 'sale:' || id, product_id, 'sale', -quantity, id, NEW.cashier_id, NEW.receipt_number, NEW.completed_at
  FROM sale_items WHERE sale_id = NEW.id;
END;

CREATE TRIGGER purchases_receive BEFORE UPDATE OF status ON purchases WHEN NEW.status = 'received'
BEGIN
  SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM purchase_items WHERE purchase_id = NEW.id)
    OR NEW.subtotal <> (SELECT sum(line_total) FROM purchase_items WHERE purchase_id = NEW.id)
    OR EXISTS (SELECT 1 FROM purchase_items WHERE purchase_id = NEW.id AND received_quantity <> quantity)
    THEN RAISE(ABORT, 'Received purchase must have matching totals and received quantities') END;
END;

CREATE TRIGGER purchases_post_stock AFTER UPDATE OF status ON purchases WHEN NEW.status = 'received'
BEGIN
  INSERT INTO inventory_movements(id, product_id, movement_type, quantity_delta, purchase_item_id, created_by, reason, created_at)
  SELECT 'receipt:' || i.id, i.product_id, 'purchase', i.received_quantity - coalesce(m.received,0), i.id,
    NEW.created_by, NEW.purchase_number, NEW.received_at
  FROM purchase_items i LEFT JOIN
    (SELECT purchase_item_id, sum(quantity_delta) AS received FROM inventory_movements GROUP BY purchase_item_id) m
    ON m.purchase_item_id = i.id
  WHERE i.purchase_id = NEW.id AND i.received_quantity > coalesce(m.received,0);
END;

CREATE TRIGGER returns_complete BEFORE UPDATE OF status ON returns WHEN NEW.status = 'completed'
BEGIN
  SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM sales WHERE id = NEW.sale_id AND status = 'completed')
    THEN RAISE(ABORT, 'Only completed sales can be returned') END;
  SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM return_items WHERE return_id = NEW.id)
    OR NEW.refund_amount <> (SELECT sum(refund_amount) FROM return_items WHERE return_id = NEW.id)
    THEN RAISE(ABORT, 'Refund total does not match items') END;
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM return_items ri JOIN sale_items si ON si.id = ri.sale_item_id
    WHERE ri.return_id = NEW.id AND (si.sale_id <> NEW.sale_id OR ri.quantity + coalesce((
      SELECT sum(pri.quantity) FROM return_items pri JOIN returns pr ON pr.id = pri.return_id
      WHERE pri.sale_item_id = ri.sale_item_id AND pr.status = 'completed'),0) > si.quantity))
    THEN RAISE(ABORT, 'Return exceeds sold quantity or belongs to another sale') END;
  SELECT CASE WHEN NEW.refund_amount + coalesce((SELECT sum(refund_amount) FROM returns
      WHERE sale_id = NEW.sale_id AND status = 'completed'),0)
    > (SELECT total_amount FROM sales WHERE id = NEW.sale_id)
    THEN RAISE(ABORT, 'Refund exceeds original sale total') END;
END;

CREATE TRIGGER returns_post_stock AFTER UPDATE OF status ON returns WHEN NEW.status = 'completed'
BEGIN
  INSERT INTO inventory_movements(id, product_id, movement_type, quantity_delta, return_item_id, created_by, reason, created_at)
  SELECT 'return:' || ri.id, si.product_id, 'return', ri.quantity, ri.id, NEW.processed_by, NEW.reason, NEW.completed_at
  FROM return_items ri JOIN sale_items si ON si.id = ri.sale_item_id WHERE ri.return_id = NEW.id AND ri.restock = 1;
END;

CREATE TRIGGER sale_items_insert_lock BEFORE INSERT ON sale_items
WHEN (SELECT status FROM sales WHERE id = NEW.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale items are immutable'); END;
CREATE TRIGGER sale_items_update_lock BEFORE UPDATE ON sale_items
WHEN (SELECT status FROM sales WHERE id = OLD.sale_id) IN ('completed','cancelled')
  OR (SELECT status FROM sales WHERE id = NEW.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale items are immutable'); END;
CREATE TRIGGER sale_items_delete_lock BEFORE DELETE ON sale_items
WHEN (SELECT status FROM sales WHERE id = OLD.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale items are immutable'); END;

CREATE TRIGGER payments_insert_lock BEFORE INSERT ON payments
WHEN (SELECT status FROM sales WHERE id = NEW.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale payments are immutable'); END;
CREATE TRIGGER payments_update_lock BEFORE UPDATE ON payments
WHEN (SELECT status FROM sales WHERE id = OLD.sale_id) IN ('completed','cancelled')
  OR (SELECT status FROM sales WHERE id = NEW.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale payments are immutable'); END;
CREATE TRIGGER payments_delete_lock BEFORE DELETE ON payments
WHEN (SELECT status FROM sales WHERE id = OLD.sale_id) IN ('completed','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized sale payments are immutable'); END;

CREATE TRIGGER purchase_items_insert_lock BEFORE INSERT ON purchase_items
WHEN (SELECT status FROM purchases WHERE id = NEW.purchase_id) IN ('received','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized purchase items are immutable'); END;
CREATE TRIGGER purchase_items_update_lock BEFORE UPDATE ON purchase_items
WHEN (SELECT status FROM purchases WHERE id = OLD.purchase_id) IN ('received','cancelled')
  OR (SELECT status FROM purchases WHERE id = NEW.purchase_id) IN ('received','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized purchase items are immutable'); END;
CREATE TRIGGER purchase_items_delete_lock BEFORE DELETE ON purchase_items
WHEN (SELECT status FROM purchases WHERE id = OLD.purchase_id) IN ('received','cancelled')
BEGIN SELECT RAISE(ABORT, 'Finalized purchase items are immutable'); END;

CREATE TRIGGER return_items_insert_lock BEFORE INSERT ON return_items
WHEN (SELECT status FROM returns WHERE id = NEW.return_id) IN ('completed','rejected')
BEGIN SELECT RAISE(ABORT, 'Finalized return items are immutable'); END;
CREATE TRIGGER return_items_update_lock BEFORE UPDATE ON return_items
WHEN (SELECT status FROM returns WHERE id = OLD.return_id) IN ('completed','rejected')
  OR (SELECT status FROM returns WHERE id = NEW.return_id) IN ('completed','rejected')
BEGIN SELECT RAISE(ABORT, 'Finalized return items are immutable'); END;
CREATE TRIGGER return_items_delete_lock BEFORE DELETE ON return_items
WHEN (SELECT status FROM returns WHERE id = OLD.return_id) IN ('completed','rejected')
BEGIN SELECT RAISE(ABORT, 'Finalized return items are immutable'); END;

CREATE TRIGGER return_items_validate_insert BEFORE INSERT ON return_items
WHEN NOT EXISTS (SELECT 1 FROM sale_items si JOIN returns r ON r.sale_id = si.sale_id
  JOIN sales s ON s.id = si.sale_id
  WHERE si.id = NEW.sale_item_id AND r.id = NEW.return_id AND s.status = 'completed' AND NEW.quantity <= si.quantity)
BEGIN SELECT RAISE(ABORT, 'Return item must belong to its completed original sale'); END;
CREATE TRIGGER return_items_validate_update BEFORE UPDATE ON return_items
WHEN NOT EXISTS (SELECT 1 FROM sale_items si JOIN returns r ON r.sale_id = si.sale_id
  JOIN sales s ON s.id = si.sale_id
  WHERE si.id = NEW.sale_item_id AND r.id = NEW.return_id AND s.status = 'completed' AND NEW.quantity <= si.quantity)
BEGIN SELECT RAISE(ABORT, 'Return item must belong to its completed original sale'); END;

PRAGMA user_version = 1;
