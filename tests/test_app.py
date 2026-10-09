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

    def demo_state(self):
        with self.client.session_transaction() as session:
            return self.app.extensions['demo_ui'][session['preview_id']]

    def test_all_management_views_forms_details_and_exports(self):
        from demo_data import MODULES
        self.login()
        for module, config in MODULES.items():
            with self.subTest(module=module):
                response = self.client.get('/' + module)
                self.assertEqual(response.status_code, 200)
                record_id = self.demo_state()[module][0]['id']
                self.assertEqual(self.client.get(f'/{module}/{record_id}').status_code, 200)
                if config['action']:
                    self.assertEqual(self.client.get(f'/{module}/new').status_code, 200)
                response = self.client.get(f'/{module}/export')
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/csv', response.content_type)
        for path in ['/reports', '/reports?section=inventory', '/reports?section=expenses', '/reports?section=returns',
                     '/settings', '/settings?section=sales', '/settings?section=inventory', '/settings?section=data', '/inventory?tab=movements']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_new_pages_enforce_roles_on_lists_details_exports_and_posts(self):
        self.login('Cashier')
        self.assertEqual(self.client.get('/sales').status_code, 200)
        self.assertEqual(self.client.get('/customers').status_code, 200)
        self.assertEqual(self.client.get('/sales/TRX-1035').status_code, 200)
        for path in ['/inventory', '/purchases/new', '/returns/RMA-301', '/users/export', '/settings', '/reports']:
            self.assertEqual(self.client.get(path).location, '/pos', path)
        self.assertEqual(self.post('/purchases/PO-2026/action', action='receive', quantity='1').location, '/pos')
        self.client = self.app.test_client()
        self.login('Manager')
        self.assertEqual(self.client.get('/reports').status_code, 200)
        self.assertEqual(self.client.get('/users').location, '/')
        self.assertEqual(self.client.get('/settings').location, '/')

    def test_customer_create_edit_archive_restore_and_browser_isolation(self):
        self.login('Cashier')
        response = self.post('/customers/new', name='Demo New Customer', email='demo@example.com', phone='0900 000 0000', notes='Prefers bass guitars')
        self.assertEqual(response.status_code, 302)
        self.assertIn('Demo New Customer', self.client.get(response.location).get_data(as_text=True))
        record_id = response.location.rsplit('/', 1)[-1]
        response = self.post(f'/customers/{record_id}/edit', name='Updated Demo Customer', email='demo@example.com', phone='0900 000 0001', notes='Updated notes')
        self.assertEqual(response.status_code, 302)
        self.assertIn('Updated Demo Customer', self.client.get(response.location).get_data(as_text=True))
        self.post(f'/customers/{record_id}/action', action='archive')
        self.assertIn('Updated Demo Customer', self.client.get('/customers?status=Archived').get_data(as_text=True))
        self.post(f'/customers/{record_id}/action', action='archive')
        self.assertNotIn('Updated Demo Customer', self.client.get('/customers?status=Archived').get_data(as_text=True))
        other = self.app.test_client()
        other.get('/login')
        with other.session_transaction() as session:
            token = session['csrf_token']
        other.post('/login', data={'role': 'Cashier', 'csrf_token': token})
        self.assertNotIn('Updated Demo Customer', other.get('/customers').get_data(as_text=True))
        self.assertEqual(self.scalar('SELECT count(*) FROM customers'), 10)

    def test_product_creation_and_stock_adjustment_share_demo_catalog(self):
        self.login()
        response = self.post('/products/new', name='Demo Bass', sku='DEMO-BASS-1', category='Electric Guitars', brand='Fender',
                             cost='123.45', price='200.00', reorder='2', unit='Piece')
        self.assertEqual(response.status_code, 302)
        self.assertIn('Demo Bass', self.client.get('/inventory').get_data(as_text=True))
        self.assertIn('Demo Bass', self.client.get('/inventory/new').get_data(as_text=True))
        self.post('/inventory/new', product='Demo Bass', movement='Stock in', quantity='3', reason='Sample stock count')
        product = next(r for r in self.demo_state()['products'] if r['name'] == 'Demo Bass')
        stock = next(r for r in self.demo_state()['inventory'] if r['name'] == 'Demo Bass')
        self.assertEqual(product['stock'], 3)
        self.assertEqual(stock['value'], 37035)
        response = self.post('/inventory/new', product='Demo Bass', movement='Stock out', quantity='4', reason='Correction')
        self.assertEqual(response.status_code, 200)
        self.assertIn('negative', response.get_data(as_text=True))
        self.assertEqual(stock['stock'], 3)
        self.assertEqual(self.scalar('SELECT count(*) FROM products'), 10)
        self.assertEqual(self.scalar('SELECT count(*) FROM inventory_movements'), 10)

    def test_purchase_order_partial_receiving_and_terminal_status(self):
        self.login()
        response = self.post('/purchases/new', supplier='Manila Music Supply', date='2026-10-07', product='Yamaha F310 Acoustic',
                             quantity='3', unit_cost='6000.00', status='Draft', notes='Test demo order')
        record_id = response.location.rsplit('/', 1)[-1]
        self.post(f'/purchases/{record_id}/action', action='order')
        original = next(r for r in self.demo_state()['inventory'] if r['name'] == 'Yamaha F310 Acoustic')['stock']
        self.post(f'/purchases/{record_id}/action', action='receive', quantity='1')
        purchase = next(r for r in self.demo_state()['purchases'] if r['id'] == record_id)
        self.assertEqual(purchase['status'], 'Partially received')
        self.post(f'/purchases/{record_id}/action', action='receive', quantity='2')
        self.assertEqual(purchase['status'], 'Received')
        self.post(f'/purchases/{record_id}/action', action='receive', quantity='1')
        self.assertEqual(next(r for r in self.demo_state()['inventory'] if r['name'] == 'Yamaha F310 Acoustic')['stock'], original + 3)
        self.assertEqual(self.client.get(f'/purchases/{record_id}/edit').status_code, 302)
        self.assertEqual(self.scalar('SELECT count(*) FROM purchases'), 10)

    def test_return_receipt_prefill_review_and_refund_report(self):
        self.login()
        page = self.client.get('/returns/new?receipt=TRX-1035').get_data(as_text=True)
        self.assertIn('value="TRX-1035" selected', page)
        response = self.post('/returns/new', receipt='TRX-1035', product='Fender Stratocaster Player', quantity='1', reason='Unopened',
                             condition='Resellable', restock='Yes', refund='47600.00', method='Card')
        self.assertEqual(response.status_code, 302)
        record_id = response.location.rsplit('/', 1)[-1]
        before = next(r for r in self.demo_state()['inventory'] if r['name'] == 'Fender Stratocaster Player')['stock']
        self.post(f'/returns/{record_id}/action', action='complete')
        self.post(f'/returns/{record_id}/action', action='complete')
        self.assertEqual(next(r for r in self.demo_state()['inventory'] if r['name'] == 'Fender Stratocaster Player')['stock'], before + 1)
        returned = next(r for r in self.demo_state()['returns'] if r['id'] == record_id)
        report = self.client.get('/reports', query_string={'section': 'returns', 'from': returned['date'], 'to': returned['date']})
        self.assertIn(record_id, report.get_data(as_text=True))
        self.assertEqual(self.scalar('SELECT count(*) FROM returns'), 10)

    def test_reports_date_range_empty_invalid_and_csv(self):
        self.login()
        page = self.client.get('/reports?from=2026-10-07&to=2026-10-07').get_data(as_text=True)
        self.assertIn('49,112.00', page)
        self.assertNotIn('TRX-1033', page)
        export = self.client.get('/reports?from=2026-10-07&to=2026-10-07&export=csv')
        self.assertIn('TRX-1035', export.get_data(as_text=True))
        self.assertNotIn('TRX-1033', export.get_data(as_text=True))
        self.assertIn('No records found', self.client.get('/reports?from=2027-01-01&to=2027-01-07').get_data(as_text=True))
        self.assertIn('Choose a valid date range', self.client.get('/reports?from=bad&to=also-bad').get_data(as_text=True))
        self.assertEqual(self.client.get('/reports?from=0001-01-01&to=9999-12-31').status_code, 200)

    def test_filters_csv_and_form_validation(self):
        self.login()
        page = self.client.get('/purchases?status=Draft').get_data(as_text=True)
        self.assertIn('PO-2029', page)
        self.assertNotIn('PO-2026', page)
        csv = self.client.get('/customers/export?q=Alex').get_data(as_text=True)
        self.assertIn('Alex Rivera', csv)
        self.assertNotIn('Jamie Santos', csv)
        page = self.client.get('/customers?q=missing').get_data(as_text=True)
        self.assertIn('No records found', page)
        response = self.post('/expenses/new', description='Test', category='Other', amount='-1', date='2026-10-07', method='Cash', status='Paid')
        self.assertIn('valid nonnegative', response.get_data(as_text=True))
        self.assertEqual(len(self.demo_state()['expenses']), 6)
        response = self.post('/expenses/new', description='Test', category='Other', amount='1.999', date='2026-10-07', method='Cash', status='Paid')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.demo_state()['expenses']), 6)
        response = self.post('/expenses/new', description='Sample supplies', category='Supplies', amount='120.50', date='2026-10-07', method='Cash', status='Pending')
        self.assertEqual(response.status_code, 302)
        record_id = response.location.rsplit('/', 1)[-1]
        self.post(f'/expenses/{record_id}/action', action='pay')
        self.assertIn('Sample supplies', self.client.get('/expenses?status=Paid').get_data(as_text=True))

    def test_settings_save_export_reset_and_preserve_real_policy(self):
        self.login()
        self.client.get('/settings')
        response = self.post('/settings?section=shop', shop_name='Preview Shop', address='Demo address', phone='123', email='demo@example.com', receipt_prefix='DEMO', receipt_footer='Come back soon')
        self.assertIn('Preview Shop', self.client.get(response.location).get_data(as_text=True))
        self.post('/settings?section=sales', tax_rate='5', cash='on', gcash='on')
        self.assertEqual(self.demo_state()['settings']['tax_rate'], '5')
        self.assertFalse(self.demo_state()['settings']['card'])
        self.assertEqual(self.scalar("SELECT value_json FROM settings WHERE key = 'tax.rate_basis_points'"), '1200')
        export = self.client.get('/settings?download=demo')
        self.assertEqual(export.json['settings']['shop_name'], 'Preview Shop')
        self.assertNotIn('password', export.get_data(as_text=True))
        self.post('/settings/reset')
        self.assertEqual(self.demo_state()['settings']['shop_name'], "Roel's Guitar Shop")

    def test_staff_actions_are_preview_only(self):
        self.login()
        self.client.get('/users')
        self.post('/users/STAFF-001/action', action='toggle')
        self.assertEqual(self.demo_state()['users'][0]['status'], 'Inactive')
        self.assertEqual(self.scalar("SELECT is_active FROM users WHERE id = 'USR-001'"), 1)
        self.assertEqual(self.client.get('/').status_code, 200)


if __name__ == '__main__':
    unittest.main()
