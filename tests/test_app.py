import tempfile
import unittest
from pathlib import Path

from app import create_app
from database import check_database, open_database
from database.seed import DEMO_PASSWORD, seed_demo
from services import cart_totals


class FlaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = open_database(':memory:')
        from database import initialize_database
        initialize_database(cls.fixture)
        seed_demo(cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.close()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database_path = str(Path(directory.name) / 'test.sqlite')
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret', 'DATABASE': database_path, 'DEMO_LOGIN': True})
        self.db = open_database(database_path)
        self.fixture.backup(self.db)
        self.addCleanup(self.db.close)
        self.client = self.app.test_client()

    def post(self, path, **data):
        with self.client.session_transaction() as session:
            token = session['csrf_token']
        return self.client.post(path, data={'csrf_token': token, **data})

    def login(self, role='Administrator'):
        self.client.get('/login')
        response = self.post('/login', role=role)
        self.client.get(response.location)
        return response

    def scalar(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def test_protected_pages_redirect_to_login(self):
        for path in ('/', '/products', '/pos'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login?next=', response.location)

    def test_demo_roles_render_their_allowed_pages(self):
        for role in ('Administrator', 'Manager', 'Cashier'):
            self.client = self.app.test_client()
            response = self.login(role)
            self.assertEqual(response.location, '/pos' if role == 'Cashier' else '/')
            self.assertEqual(self.client.get('/pos').status_code, 200)
            for path in ('/', '/products'):
                page = self.client.get(path)
                self.assertEqual(page.status_code, 302 if role == 'Cashier' else 200)

    def test_login_resumes_only_allowed_local_routes(self):
        self.client.get('/login?next=/products')
        self.assertEqual(self.post('/login', role='Manager', next='/products').location, '/products')
        self.client.get('/products')
        self.post('/logout')
        self.client.get('/login')
        self.assertEqual(self.post('/login', role='Cashier', next='https://example.com').location, '/pos')

    def test_password_login_and_disabled_demo(self):
        self.app.config['DEMO_LOGIN'] = False
        page = self.client.get('/login').get_data(as_text=True)
        self.assertNotIn('Select Demo Account', page)
        self.assertEqual(self.post('/login', role='Administrator').status_code, 200)
        self.assertEqual(self.post('/login', username='admin.demo', password='wrong').status_code, 200)
        response = self.post('/login', username='admin.demo', password=DEMO_PASSWORD)
        self.assertEqual(response.location, '/')

    def test_csrf_protects_mutations(self):
        self.client.get('/login')
        self.assertEqual(self.client.post('/login', data={'role': 'Administrator'}).status_code, 400)
        self.login()
        self.assertEqual(self.client.post('/pos/cart', data={'action': 'add', 'product_id': 'PRD-001'}).status_code, 400)
        self.assertEqual(self.client.get('/logout').status_code, 405)

    def test_product_search_and_html_escaping(self):
        self.login()
        page = self.client.get('/products?q=ERN-2221').get_data(as_text=True)
        self.assertIn('Ernie Ball Regular Slinky', page)
        self.assertNotIn('Yamaha F310 Acoustic', page)
        self.assertIn('Showing 1 of 10 products', page)
        page = self.client.get('/products', query_string={'q': '<script>alert(1)</script>'}).get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;script&gt;', page)

    def test_pos_category_filter(self):
        self.login('Cashier')
        page = self.client.get('/pos?category=Strings').get_data(as_text=True)
        self.assertIn('Add Ernie Ball Regular Slinky to cart', page)
        self.assertNotIn('Add Yamaha F310 Acoustic to cart', page)

    def test_cart_add_decrease_remove_and_stock_limit(self):
        self.login('Cashier')
        self.post('/pos/cart', action='add', product_id='PRD-004')
        self.post('/pos/cart', action='add', product_id='PRD-004')
        self.post('/pos/cart', action='decrease', product_id='PRD-004')
        with self.client.session_transaction() as session:
            self.assertEqual(session['cart'], {'PRD-004': 1})
        self.post('/pos/cart', action='remove', product_id='PRD-004')
        self.post('/pos/cart', action='add', product_id='PRD-005')
        with self.client.session_transaction() as session:
            self.assertEqual(session['cart'], {})
        for _ in range(4):
            self.post('/pos/cart', action='add', product_id='PRD-004')
        with self.client.session_transaction() as session:
            self.assertEqual(session['cart']['PRD-004'], 3)
        self.assertIn('Not enough stock', self.client.get('/pos').get_data(as_text=True))
        self.post('/pos/cart', action='clear')
        with self.client.session_transaction() as session:
            self.assertEqual(session['cart'], {})

    def test_checkout_posts_payment_stock_audit_and_clears_cart(self):
        self.login('Cashier')
        self.post('/pos/cart', action='add', product_id='PRD-003')
        self.post('/pos/checkout', method='gcash', total='1')
        self.assertEqual(self.scalar("SELECT stock_quantity FROM product_inventory WHERE id = 'PRD-003'"), 44)
        self.assertEqual(self.scalar("SELECT count(*) FROM sales WHERE status = 'completed'"), 3)
        self.assertEqual(self.scalar("SELECT total_amount FROM sales WHERE id NOT LIKE 'SAL-%'"), 50400)
        self.assertEqual(self.scalar("SELECT method FROM payments WHERE id NOT LIKE 'PAY-%'"), 'gcash')
        self.assertEqual(self.scalar('SELECT count(*) FROM audit_logs'), 11)
        with self.client.session_transaction() as session:
            self.assertNotIn('cart', session)
        self.assertIn('Payment recorded', self.client.get('/pos').get_data(as_text=True))
        self.post('/pos/checkout', method='cash')
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 11)
        check_database(self.db)

    def test_checkout_rechecks_stock_and_rolls_back(self):
        self.login()
        self.post('/pos/cart', action='add', product_id='PRD-004')
        self.db.execute("INSERT INTO inventory_movements (id, product_id, movement_type, quantity_delta, created_by, reason) VALUES ('test-adjustment', 'PRD-004', 'adjustment_out', -3, 'USR-001', 'Stock correction')")
        self.post('/pos/checkout', method='cash')
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 10)
        self.assertEqual(self.scalar('SELECT count(*) FROM payments'), 10)
        self.assertIn('Insufficient stock', self.client.get('/pos').get_data(as_text=True))

    def test_invalid_checkout_method_does_not_write(self):
        self.login()
        self.post('/pos/cart', action='add', product_id='PRD-003')
        self.post('/pos/checkout', method='invalid')
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 10)

    def test_checkout_transaction_rolls_back_when_audit_fails(self):
        self.login()
        self.post('/pos/cart', action='add', product_id='PRD-003')
        self.db.execute("CREATE TRIGGER reject_test_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'Test audit rejection'); END")
        self.post('/pos/checkout', method='cash')
        self.assertEqual(self.scalar('SELECT count(*) FROM sales'), 10)
        self.assertEqual(self.scalar('SELECT count(*) FROM payments'), 10)
        self.assertEqual(self.scalar("SELECT stock_quantity FROM product_inventory WHERE id = 'PRD-003'"), 45)

    def test_tax_inclusive_and_integer_rounding(self):
        self.db.execute("UPDATE products SET selling_price = 101 WHERE id = 'PRD-003'")
        totals = cart_totals(self.db, {'PRD-003': 1})
        self.assertEqual(totals['tax'], 12)
        self.assertEqual(totals['total'], 113)
        self.db.execute("UPDATE settings SET value_json = 'true' WHERE key = 'tax.price_inclusive'")
        self.assertEqual(cart_totals(self.db, {'PRD-003': 1})['total'], 101)

    def test_logout_clears_access_and_cart(self):
        self.login()
        self.post('/pos/cart', action='add', product_id='PRD-003')
        self.post('/logout')
        with self.client.session_transaction() as session:
            self.assertNotIn('user_id', session)
            self.assertNotIn('cart', session)
        self.assertEqual(self.client.get('/pos').status_code, 302)

    def test_deactivated_user_loses_access(self):
        self.login()
        self.db.execute("UPDATE users SET is_active = 0 WHERE id = 'USR-001'")
        self.assertEqual(self.client.get('/products').status_code, 302)

    def test_static_files_and_not_found_page(self):
        with self.client.get('/static/css/base.css') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/missing').status_code, 404)

    def test_cli_checks_data_and_refuses_reseed(self):
        runner = self.app.test_cli_runner()
        self.assertEqual(runner.invoke(args=['db-init']).exit_code, 0)
        result = runner.invoke(args=['db-check'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Integrity and foreign keys: OK', result.output)
        result = runner.invoke(args=['db-seed'])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('Existing data was preserved', result.output)


if __name__ == '__main__':
    unittest.main()
