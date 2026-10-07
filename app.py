"""Roel's Guitar Shop: Flask routes rendering Jinja HTML templates."""

import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

from database import DEFAULT_DATABASE, get_db, init_app, initialize_database, open_database
from database.seed import verify_password
from services import cart_totals, catalog, complete_sale

ROLES = ('Administrator', 'Manager', 'Cashier')
MANILA = timezone(timedelta(hours=8))


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get('SHOP_DB_PATH', str(DEFAULT_DATABASE)),
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        DEMO_LOGIN=os.environ.get('SHOP_DEMO_LOGIN', 'true').lower() == 'true',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        key_path = Path(app.instance_path) / 'secret-key'
        try:
            with key_path.open('x', encoding='utf-8') as key_file:
                key_file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        app.config['SECRET_KEY'] = key_path.read_text(encoding='utf-8')
    init_app(app)
    db = open_database(app.config['DATABASE'])
    try:
        initialize_database(db)
    finally:
        db.close()

    def csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return session['csrf_token']

    @app.before_request
    def load_user_and_check_csrf():
        g.user = None
        if session.get('user_id'):
            g.user = get_db().execute('''SELECT u.id, u.full_name AS name, r.name AS role
                FROM users u JOIN roles r ON r.id = u.role_id
                WHERE u.id = ? AND u.is_active = 1 AND r.is_active = 1''', (session['user_id'],)).fetchone()
            if g.user is None or g.user['role'] not in ROLES:
                session.clear()
                g.user = None
        if request.method == 'POST':
            expected = session.get('csrf_token', '')
            submitted = request.form.get('csrf_token', '')
            if not expected or not hmac.compare_digest(expected, submitted):
                abort(400, description='The form expired. Reload the page and try again.')

    @app.context_processor
    def template_context():
        return {'user': g.user, 'csrf_token': csrf_token}

    @app.template_filter('money')
    def money(centavos):
        whole, cents = divmod(int(centavos), 100)
        return f'₱{whole:,}.{cents:02d}'

    def default_page():
        return 'pos' if g.user and g.user['role'] == 'Cashier' else 'dashboard'

    def roles_required(*roles):
        def decorate(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if not g.user:
                    return redirect(url_for('login', next=request.path))
                if g.user['role'] not in roles:
                    return redirect(url_for(default_page()))
                return view(*args, **kwargs)
            return wrapped
        return decorate

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if g.user:
            return redirect(url_for(default_page()))
        if request.method == 'POST':
            db = get_db()
            account = None
            role = request.form.get('role')
            if role and app.config['DEMO_LOGIN'] and role in ROLES:
                # Only the original fictional seed accounts can use the role buttons.
                demo_id = {'Administrator': 'USR-001', 'Manager': 'USR-002', 'Cashier': 'USR-003'}[role]
                account = db.execute('''SELECT u.*, r.name AS role FROM users u JOIN roles r ON r.id = u.role_id
                    WHERE u.id = ? AND r.name = ? AND u.is_active = 1 AND r.is_active = 1
                    AND u.username IN ('admin.demo', 'staff2.demo', 'staff3.demo')''', (demo_id, role)).fetchone()
            elif not role:
                account = db.execute('''SELECT u.*, r.name AS role FROM users u JOIN roles r ON r.id = u.role_id
                    WHERE u.username = ? AND u.is_active = 1 AND r.is_active = 1''',
                    (request.form.get('username', '').strip(),)).fetchone()
                if account and not verify_password(request.form.get('password', ''), account['password_hash']):
                    account = None
            if account and account['role'] in ROLES:
                session.clear()
                session['user_id'] = account['id']
                destination = request.form.get('next', '')
                allowed = ('/pos',) if account['role'] == 'Cashier' else ('/', '/products', '/pos')
                return redirect(destination if destination in allowed else ('/pos' if account['role'] == 'Cashier' else '/'))
            flash('Unable to sign in. Check your credentials or initialize the demo database.', 'error')
        return render_template('login.html', roles=ROLES, demo_login=app.config['DEMO_LOGIN'], next_page=request.args.get('next', ''))

    @app.post('/logout')
    @roles_required(*ROLES)
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @roles_required('Administrator', 'Manager')
    def dashboard():
        db = get_db()
        today = datetime.now(MANILA)
        daily = db.execute('SELECT * FROM daily_sales WHERE sale_date = ?', (today.date().isoformat(),)).fetchone()
        monthly = db.execute('SELECT coalesce(sum(gross_sales), 0) FROM daily_sales WHERE substr(sale_date, 1, 7) = ?',
                             (today.strftime('%Y-%m'),)).fetchone()[0]
        low_stock = db.execute('SELECT count(*) FROM product_inventory WHERE is_active = 1 AND stock_quantity <= reorder_level').fetchone()[0]
        recent_sales = db.execute('''SELECT s.*, strftime('%H:%M', s.completed_at, '+8 hours') AS local_time,
            (SELECT group_concat(product_name, ', ') FROM sale_items WHERE sale_id = s.id) AS items_summary
            FROM sales s WHERE s.status = 'completed' ORDER BY s.completed_at DESC LIMIT 10''').fetchall()
        top_products = db.execute('''SELECT p.name, p.category_name, p.stock_quantity, sum(i.quantity) AS sold
            FROM sale_items i JOIN sales s ON s.id = i.sale_id JOIN product_inventory p ON p.id = i.product_id
            WHERE s.status = 'completed' GROUP BY p.id ORDER BY sold DESC LIMIT 4''').fetchall()
        return render_template('dashboard.html', today=today.strftime('%A, %B %d, %Y'),
                               sales=daily['gross_sales'] if daily else 0, transactions=daily['transactions'] if daily else 0,
                               monthly=monthly, low_stock=low_stock, recent_sales=recent_sales, top_products=top_products)

    @app.get('/products')
    @roles_required('Administrator', 'Manager')
    def products():
        search = request.args.get('q', '').strip()
        return render_template('products.html', products=catalog(get_db(), search), search=search,
                               total_products=get_db().execute('SELECT count(*) FROM products WHERE is_active = 1').fetchone()[0])

    @app.get('/pos')
    @roles_required(*ROLES)
    def pos():
        db = get_db()
        search = request.args.get('q', '').strip()
        category = request.args.get('category', '')
        cart = session.get('cart', {})
        try:
            totals = cart_totals(db, cart)
        except ValueError as error:
            flash(str(error), 'error')
            session.pop('cart', None)
            totals = cart_totals(db, {})
        return render_template('pos.html', products=catalog(db, search, category), search=search, category=category,
                               categories=db.execute('SELECT name FROM categories WHERE is_active = 1 ORDER BY name').fetchall(), **totals)

    @app.post('/pos/cart')
    @roles_required(*ROLES)
    def update_cart():
        cart = dict(session.get('cart', {}))
        product_id = request.form.get('product_id', '')
        action = request.form.get('action')
        if action == 'clear':
            cart = {}
        elif action == 'remove':
            cart.pop(product_id, None)
        elif action in ('add', 'decrease'):
            product = get_db().execute('SELECT * FROM product_inventory WHERE id = ? AND is_active = 1', (product_id,)).fetchone()
            if not product:
                abort(404)
            quantity = cart.get(product_id, 0) + (1 if action == 'add' else -1)
            if quantity <= 0:
                cart.pop(product_id, None)
            elif quantity > product['stock_quantity']:
                flash('Not enough stock for that quantity.', 'error')
            else:
                cart[product_id] = quantity
        else:
            abort(400)
        session['cart'] = cart
        return redirect(url_for('pos', q=request.form.get('q', ''), category=request.form.get('category', '')))

    @app.post('/pos/checkout')
    @roles_required(*ROLES)
    def checkout():
        try:
            receipt = complete_sale(get_db(), session.get('cart', {}), g.user['id'], request.form.get('method', 'cash'))
        except (ValueError, sqlite3.IntegrityError) as error:
            flash(str(error), 'error')
        else:
            session.pop('cart', None)
            flash(f'Payment recorded. Receipt: {receipt}', 'success')
        return redirect(url_for('pos'))

    @app.errorhandler(400)
    @app.errorhandler(404)
    def error_page(error):
        return render_template('error.html', error=error), error.code

    return app


if __name__ == '__main__':
    create_app().run()
