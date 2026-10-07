import sqlite3
import unittest

from database import check_database, initialize_database, open_database, table_counts, transaction
from database.seed import DEMO_PASSWORD, seed_demo, verify_password


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = open_database(':memory:')
        initialize_database(cls.fixture)
        seed_demo(cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.close()

    def setUp(self):
        self.db = open_database(':memory:')
        self.fixture.backup(self.db)
        self.addCleanup(self.db.close)

    def scalar(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def post_sale(self, number, stamp='2026-09-21T05:00:00Z'):
        self.db.execute("UPDATE payments SET status = 'completed', paid_at = ? WHERE id = ?", (stamp, f'PAY-{number:03}'))
        self.db.execute("UPDATE sales SET status = 'completed', completed_at = ? WHERE id = ?", (stamp, f'SAL-{number:03}'))

    def test_demo_counts_reports_and_stock(self):
        counts = check_database(self.db)
        self.assertEqual(len(counts), 20)
        self.assertTrue(all(row['rows'] == 10 for row in counts))
        self.assertEqual(self.scalar('PRAGMA foreign_keys'), 1)
        self.assertEqual(self.scalar('PRAGMA user_version'), 1)
        self.assertEqual(self.scalar("SELECT sum(total_amount) FROM sales WHERE status = 'completed'"), 28560000)
        self.assertEqual(self.scalar("SELECT sum(refund_amount) FROM returns WHERE status = 'completed'"), 5712000)
        self.assertEqual([row[0] for row in self.db.execute('SELECT stock_quantity FROM product_inventory ORDER BY id')],
                         [11, 21, 45, 3, 0, 0, 0, 0, 0, 0])

    def test_initialization_is_repeatable_and_seed_preserves_data(self):
        before = table_counts(self.db)
        initialize_database(self.db)
        with self.assertRaisesRegex(ValueError, 'requires empty tables'):
            seed_demo(self.db)
        self.assertEqual(table_counts(self.db), before)

    def test_salted_passwords_are_compatible(self):
        hashes = [row[0] for row in self.db.execute('SELECT password_hash FROM users')]
        self.assertEqual(len(set(hashes)), 10)
        self.assertTrue(all(verify_password(DEMO_PASSWORD, value) for value in hashes))
        self.assertFalse(verify_password('incorrect', hashes[0]))

    def test_constraints(self):
        for sql in ["UPDATE products SET category_id = 'missing' WHERE id = 'PRD-001'",
                    "UPDATE products SET sku = 'STR-PL-BLK' WHERE id = 'PRD-002'",
                    "UPDATE products SET cost_price = 1.5 WHERE id = 'PRD-001'",
                    "UPDATE sale_items SET quantity = 0 WHERE id = 'SI-005'",
                    "UPDATE products SET selling_price = -1 WHERE id = 'PRD-001'"]:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql)

    def test_unpaid_and_mismatched_sales_are_rejected(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'payments'):
            self.db.execute("UPDATE sales SET status = 'completed', completed_at = '2026-09-21T05:00:00Z' WHERE id = 'SAL-003'")
        self.db.execute("UPDATE sales SET subtotal = 1 WHERE id = 'SAL-003'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'subtotal'):
            self.db.execute("UPDATE sales SET status = 'completed', completed_at = '2026-09-21T05:00:00Z' WHERE id = 'SAL-003'")
        self.assertEqual(self.scalar("SELECT count(*) FROM inventory_movements WHERE sale_item_id = 'SI-003'"), 0)

    def test_out_of_stock_posting_rolls_back(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'Insufficient stock'):
            with transaction(self.db):
                self.post_sale(5)
        self.assertEqual(self.scalar("SELECT status FROM payments WHERE id = 'PAY-005'"), 'pending')
        self.assertEqual(self.scalar("SELECT status FROM sales WHERE id = 'SAL-005'"), 'draft')
        self.assertEqual(self.scalar('SELECT count(*) FROM inventory_movements'), 10)

    def test_checkout_posts_once_and_freezes_history(self):
        with transaction(self.db):
            self.post_sale(3)
        self.assertEqual(self.scalar("SELECT stock_quantity FROM product_inventory WHERE id = 'PRD-003'"), 44)
        for sql in ["UPDATE sales SET subtotal = 1 WHERE id = 'SAL-003'",
                    "DELETE FROM sale_items WHERE id = 'SI-003'",
                    "DELETE FROM payments WHERE id = 'PAY-003'"]:
            with self.subTest(sql=sql), self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
                self.db.execute(sql)

    def test_purchase_posts_stock(self):
        with transaction(self.db):
            self.db.execute("UPDATE purchase_items SET received_quantity = quantity WHERE id = 'PI-005'")
            self.db.execute("UPDATE purchases SET status = 'received', received_at = '2026-09-21T05:00:00Z' WHERE id = 'PUR-005'")
        self.assertEqual(self.scalar("SELECT stock_quantity FROM product_inventory WHERE id = 'PRD-005'"), 5)
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
            self.db.execute("UPDATE purchase_items SET received_quantity = 0 WHERE id = 'PI-005'")

    def test_returns_validate_ownership_quantities_and_refunds(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'original sale'):
            self.db.execute("UPDATE return_items SET sale_item_id = 'SI-002' WHERE id = 'RI-003'")
        self.db.execute("UPDATE return_items SET quantity = 5 WHERE id = 'RI-003'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'exceeds sold quantity'):
            self.db.execute("UPDATE returns SET status = 'completed', completed_at = '2026-09-21T05:00:00Z' WHERE id = 'RET-003'")
        self.db.execute("UPDATE return_items SET quantity = 1, refund_amount = 999999999 WHERE id = 'RI-003'")
        self.db.execute("UPDATE returns SET refund_amount = 999999999 WHERE id = 'RET-003'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'original sale total'):
            self.db.execute("UPDATE returns SET status = 'completed', completed_at = '2026-09-21T05:00:00Z' WHERE id = 'RET-003'")

    def test_damaged_returns_do_not_restock(self):
        with transaction(self.db):
            self.db.execute("UPDATE return_items SET restock = 0, condition = 'damaged' WHERE id = 'RI-003'")
            self.db.execute("UPDATE returns SET status = 'completed', completed_at = '2026-09-21T05:00:00Z' WHERE id = 'RET-003'")
        self.assertEqual(self.scalar("SELECT stock_quantity FROM product_inventory WHERE id = 'PRD-001'"), 11)
        self.assertEqual(self.scalar("SELECT refunded_amount FROM sale_balances WHERE id = 'SAL-001'"), 9520000)

    def test_ledgers_are_immutable(self):
        for sql in ["UPDATE inventory_movements SET quantity_delta = 20 WHERE id = 'MOV-OPEN-001'",
                    "DELETE FROM inventory_movements WHERE id = 'MOV-OPEN-001'",
                    "UPDATE audit_logs SET action = 'changed' WHERE id = 'AUD-001'",
                    "DELETE FROM audit_logs WHERE id = 'AUD-001'"]:
            with self.subTest(sql=sql), self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable'):
                self.db.execute(sql)

    def test_daily_reports_use_manila_date(self):
        with transaction(self.db):
            self.post_sale(3, '2026-09-21T17:00:00Z')
        self.assertEqual(self.scalar("SELECT transactions FROM daily_sales WHERE sale_date = '2026-09-22'"), 1)


if __name__ == '__main__':
    unittest.main()
