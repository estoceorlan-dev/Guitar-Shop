"""Interactive placeholder screens backed by temporary per-browser memory."""

import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from copy import deepcopy
from uuid import uuid4

from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, session, url_for

from demo_data import MODULES, allowed_roles, fixtures

demo = Blueprint('demo', __name__)
TODAY = lambda: datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def preview_data():
    key = session.setdefault('preview_id', uuid4().hex)
    store = current_app.extensions['demo_ui']
    if key not in store:
        store[key] = fixtures()
    return store[key]


def find_record(module, record_id):
    record = next((row for row in preview_data()[module] if row['id'] == record_id), None)
    if record is None:
        abort(404)
    return record


def module_config(module):
    config = deepcopy(MODULES[module])
    data = preview_data()
    choices = {
        'product': [r['name'] for r in data['products'] if r['status'] == 'Active'],
        'supplier': [r['name'] for r in data['suppliers'] if r['status'] == 'Active'],
        'category': [r['name'] for r in data['categories'] if r['status'] == 'Active'],
        'brand': [r['name'] for r in data['brands'] if r['status'] == 'Active'],
        'receipt': [r['id'] for r in data['sales'] if r['status'] == 'Completed'],
    }
    for item in config['fields']:
        if item['type'] == 'select' and item['name'] in choices and not (item['name'] == 'category' and module == 'expenses'):
            item['options'] = choices[item['name']]
    return config


def filtered_rows(module):
    rows = preview_data()[module]
    query = request.args.get('q', '').strip().lower()
    status = request.args.get('status', '')
    return [row for row in rows if (not status or row.get('status') == status)
            and (not query or query in ' '.join(str(value) for value in row.values()).lower())]


def stat(label, value, kind='number', note=''):
    return {'label': label, 'value': value, 'kind': kind, 'note': note}


def module_stats(module):
    rows = preview_data()[module]
    active = sum(row.get('status') in ('Active', 'Paid', 'Completed', 'Received', 'In stock') for row in rows)
    if module == 'inventory':
        return [stat('Stock value', sum(r['value'] for r in rows), 'money', 'At cost price'), stat('Units on hand', sum(r['stock'] for r in rows)), stat('Low stock', sum(r['status'] == 'Low stock' for r in rows), note='Ready to reorder'), stat('Out of stock', sum(r['stock'] == 0 for r in rows))]
    if module == 'sales':
        completed = [r for r in rows if r['status'] == 'Completed']
        return [stat('Gross sales', sum(r['total'] for r in completed), 'money'), stat('Completed sales', len(completed)), stat('Average sale', sum(r['total'] for r in completed) // max(len(completed), 1), 'money'), stat('Held sales', sum(r['status'] == 'Held' for r in rows))]
    if module == 'purchases':
        return [stat('Total orders', len(rows)), stat('Awaiting delivery', sum(r['status'] in ('Ordered', 'Partially received') for r in rows)), stat('Received orders', active), stat('Order value', sum(r['total'] for r in rows if r['status'] != 'Cancelled'), 'money')]
    if module == 'returns':
        return [stat('Return requests', len(rows)), stat('Awaiting review', sum(r['status'] == 'Requested' for r in rows)), stat('Refunded', sum(r['refund'] for r in rows if r['status'] == 'Completed'), 'money'), stat('Restocked units', sum(r['quantity'] for r in rows if r['status'] == 'Completed' and r['restock'] == 'Yes'))]
    if module == 'expenses':
        return [stat('Total expenses', sum(r['amount'] for r in rows), 'money'), stat('Paid', sum(r['amount'] for r in rows if r['status'] == 'Paid'), 'money'), stat('Pending', sum(r['amount'] for r in rows if r['status'] == 'Pending'), 'money'), stat('Expense records', len(rows))]
    if module in ('customers', 'suppliers'):
        return [stat('Total ' + module, len(rows)), stat('Active', active), stat('Total ' + ('spent' if module == 'customers' else 'purchases'), sum(r['spend'] for r in rows), 'money'), stat('Visits' if module == 'customers' else 'Purchase orders', sum(r.get('visits', r.get('orders', 0)) for r in rows))]
    if module == 'products':
        return [stat('Catalog products', len(rows)), stat('Active products', active), stat('Categories', len({r['category'] for r in rows})), stat('Brands', len({r['brand'] for r in rows}))]
    if module == 'users':
        return [stat('Team members', len(rows)), stat('Active staff', active), stat('Administrators', sum(r['role'] == 'Administrator' for r in rows)), stat('Cashiers', sum(r['role'] == 'Cashier' for r in rows))]
    return [stat('Total ' + module, len(rows)), stat('Active', active), stat('Catalog products', sum(r['products'] for r in rows)), stat('Archived', len(rows) - active)]


@demo.before_request
def protect_preview():
    module = (request.view_args or {}).get('module')
    if module and module not in MODULES:
        abort(404)
    if not g.user:
        return redirect(url_for('login', next=request.path))
    module = module or ('settings' if request.endpoint in ('demo.settings', 'demo.reset') else 'reports')
    if g.user['role'] not in allowed_roles(module):
        return redirect(url_for('pos' if g.user['role'] == 'Cashier' else 'dashboard'))


def list_page(module):
    rows = filtered_rows(module)
    return render_template('products.html' if module == 'products' else 'management.html', module=module, config=MODULES[module], rows=rows,
                           total=len(preview_data()[module]), stats=module_stats(module), search=request.args.get('q', ''),
                           selected_status=request.args.get('status', ''), movements=preview_data()['movements'],
                           tab=request.args.get('tab', 'stock'), preview=True)


def form_values(module, record):
    values = dict(record or {})
    values.setdefault('date', TODAY())
    values.setdefault('reorder', 5)
    for item in module_config(module)['fields']:
        if item['type'] == 'money' and item['name'] in values:
            values[item['name']] = f"{values[item['name']] / 100:.2f}"
    return values


def parse_form(module):
    values = {}
    for item in module_config(module)['fields']:
        raw = request.form.get(item['name'], '').strip()
        if len(raw) > 2000:
            raise ValueError(f"{item['label']} is too long.")
        if not raw and item['required']:
            raise ValueError(f"Enter {item['label'].lower()}.")
        if item['type'] == 'select' and raw not in item['options']:
            raise ValueError(f"Choose a valid {item['label'].lower()}.")
        if item['type'] in ('number', 'money'):
            try:
                number = Decimal(raw)
                if not number.is_finite() or number < 0 or number > 10000000:
                    raise ValueError
                if item['type'] == 'number' and number != int(number):
                    raise ValueError
                if item['type'] == 'money' and number * 100 != int(number * 100):
                    raise ValueError
                values[item['name']] = int(number * 100) if item['type'] == 'money' else int(number)
            except (InvalidOperation, ValueError, OverflowError):
                raise ValueError(f"Enter a valid nonnegative {item['label'].lower()}.") from None
            if item['name'] == 'quantity' and values[item['name']] == 0:
                raise ValueError('Quantity must be greater than zero.')
        else:
            if item['type'] == 'date':
                try:
                    date.fromisoformat(raw)
                except ValueError:
                    raise ValueError('Enter a valid date.') from None
            if item['type'] == 'email' and raw and ('@' not in raw or '.' not in raw.split('@')[-1]):
                raise ValueError('Enter a valid email address.')
            values[item['name']] = raw
    return values


def inventory_adjust(product_name, delta, movement, reason):
    data = preview_data()
    product = next((r for r in data['inventory'] if r['name'] == product_name), None)
    if product is None:
        raise ValueError('Product not found in the demo inventory.')
    if product['stock'] + delta < 0:
        raise ValueError('The adjustment would make stock negative.')
    product['stock'] += delta
    product['value'] = product['stock'] * product['cost']
    product['status'] = 'Out of stock' if product['stock'] == 0 else 'Low stock' if product['stock'] <= product['reorder'] else 'In stock'
    catalog_product = next((r for r in data['products'] if r['id'] == product['id']), None)
    if catalog_product:
        catalog_product['stock'] = product['stock']
    data['movements'].insert(0, {'id': 'MOV-' + uuid4().hex[:8].upper(), 'date': TODAY(), 'product': product_name, 'movement': movement, 'delta': delta, 'reason': reason, 'by': g.user['name']})


@demo.route('/<module>/new', methods=['GET', 'POST'])
@demo.route('/<module>/<record_id>/edit', methods=['GET', 'POST'])
def form_page(module, record_id=None):
    config = module_config(module)
    if not config['action'] or (module == 'inventory' and record_id):
        abort(404)
    record = find_record(module, record_id) if record_id else None
    if record and ((module == 'purchases' and record['status'] in ('Received', 'Partially received', 'Cancelled'))
                   or (module == 'returns' and record['status'] != 'Requested')):
        return redirect(url_for('demo.detail_page', module=module, record_id=record_id))
    values = form_values(module, record)
    if module == 'returns' and not record:
        receipt = request.args.get('receipt')
        sale = next((r for r in preview_data()['sales'] if r['id'] == receipt and r['status'] == 'Completed'), None)
        if sale:
            values.update(receipt=sale['id'], product=sale['product'], quantity=1, refund=f"{sale['unit_price'] * 112 / 10000:.2f}")
    error = None
    if request.method == 'POST':
        values = request.form.to_dict()
        try:
            parsed = parse_form(module)
            data = preview_data()
            if module == 'inventory':
                delta = parsed['quantity'] * (1 if parsed['movement'] == 'Stock in' else -1)
                inventory_adjust(parsed['product'], delta, parsed['movement'], parsed['reason'])
                flash('Demo stock adjustment saved.', 'success')
                return redirect(url_for('demo.list_page', module=module))
            if module == 'returns':
                sale = next((r for r in data['sales'] if r['id'] == parsed['receipt'] and r['status'] == 'Completed'), None)
                if not sale or sale['product'] != parsed['product'] or parsed['quantity'] > sale['quantity'] or parsed['refund'] > sale['total']:
                    raise ValueError('Choose an item from the original receipt and a quantity/refund within that sale.')
                if parsed['condition'] != 'Resellable' and parsed['restock'] == 'Yes':
                    raise ValueError('Damaged or defective items cannot be restocked.')
                parsed['customer'] = sale['customer']
            if module == 'products' and any(r['sku'].lower() == parsed['sku'].lower() and r['id'] != record_id for r in data['products']):
                raise ValueError('That SKU is already in the demo catalog.')
            previous_name = record.get('name') if record else None
            if record:
                record.update(parsed)
            else:
                prefixes = {'products': 'PRD', 'purchases': 'PO', 'suppliers': 'SUP', 'customers': 'CUS', 'returns': 'RMA', 'expenses': 'EXP', 'categories': 'CAT', 'brands': 'BRD', 'users': 'STAFF'}
                record = {'id': prefixes[module] + '-' + uuid4().hex[:6].upper(), 'status': 'Requested' if module == 'returns' else 'Active',
                          'stock': 0, 'products': 0, 'visits': 0, 'orders': 0, 'spend': 0, 'last_visit': '—', 'last_active': 'Not yet active', 'date': TODAY(), **parsed}
                data[module].insert(0, record)
            if module == 'purchases':
                record['total'] = record['quantity'] * record['unit_cost']
                record.setdefault('received', 0)
            if module == 'products':
                stock_record = next((r for r in data['inventory'] if r['id'] == record['id']), None)
                if stock_record is None:
                    stock_record = dict(record, stock=0, value=0, status='Out of stock')
                    data['inventory'].insert(0, stock_record)
                else:
                    stock_record.update({key: record[key] for key in ('name', 'sku', 'category', 'brand', 'cost', 'price', 'reorder')})
                    stock_record['value'] = stock_record['stock'] * stock_record['cost']
                    stock_record['status'] = 'Out of stock' if stock_record['stock'] == 0 else 'Low stock' if stock_record['stock'] <= stock_record['reorder'] else 'In stock'
            if module in ('categories', 'brands') and previous_name:
                reference = 'category' if module == 'categories' else 'brand'
                for row in data['products'] + data['inventory']:
                    if row[reference] == previous_name:
                        row[reference] = record['name']
            for key, reference in [('categories', 'category'), ('brands', 'brand')]:
                for row in data[key]:
                    row['products'] = sum(p[reference] == row['name'] and p['status'] == 'Active' for p in data['products'])
            if module == 'expenses':
                record['recorded_by'] = g.user['name']
            flash('Demo record saved.', 'success')
            return redirect(url_for('demo.detail_page', module=module, record_id=record['id']))
        except ValueError as caught:
            error = str(caught)
    return render_template('record_form.html', module=module, config=config, values=values, record=record, error=error, preview=True)


@demo.get('/<module>/<record_id>')
def detail_page(module, record_id):
    record = find_record(module, record_id)
    data = preview_data()
    related = []
    if module == 'customers':
        related = [r for r in data['sales'] if r['customer'] == record['name']]
    elif module == 'suppliers':
        related = [r for r in data['purchases'] if r['supplier'] == record['name']]
    elif module in ('products', 'inventory'):
        related = [r for r in data['movements'] if r['product'] == record['name']]
    return render_template('record_detail.html', module=module, config=MODULES[module], record=record, related=related, preview=True)


@demo.post('/<module>/<record_id>/action')
def record_action(module, record_id):
    record = find_record(module, record_id)
    action = request.form.get('action')
    try:
        if action == 'archive' and module in ('products', 'suppliers', 'customers', 'categories', 'brands'):
            record['status'] = 'Active' if record['status'] == 'Archived' else 'Archived'
        elif action == 'toggle' and module == 'users':
            record['status'] = 'Inactive' if record['status'] == 'Active' else 'Active'
        elif action == 'order' and module == 'purchases' and record['status'] == 'Draft':
            record['status'] = 'Ordered'
        elif action == 'receive' and module == 'purchases' and record['status'] in ('Ordered', 'Partially received'):
            quantity = request.form.get('quantity', '')
            if not quantity.isdigit() or not 0 < int(quantity) <= record['quantity'] - record['received']:
                raise ValueError('Enter a quantity within the outstanding order.')
            quantity = int(quantity)
            inventory_adjust(record['product'], quantity, 'Purchase', record['id'])
            record['received'] += quantity
            record['status'] = 'Received' if record['received'] == record['quantity'] else 'Partially received'
        elif action == 'cancel' and module == 'purchases' and record['status'] in ('Draft', 'Ordered'):
            record['status'] = 'Cancelled'
        elif action in ('complete', 'reject') and module == 'returns' and record['status'] == 'Requested':
            if action == 'complete':
                sale = next(r for r in preview_data()['sales'] if r['id'] == record['receipt'])
                posted = [r for r in preview_data()['returns'] if r['receipt'] == record['receipt'] and r['status'] == 'Completed']
                if sum(r['quantity'] for r in posted) + record['quantity'] > sale['quantity'] or sum(r['refund'] for r in posted) + record['refund'] > sale['total']:
                    raise ValueError('This return exceeds the remaining original sale quantity or amount.')
                if record['restock'] == 'Yes':
                    inventory_adjust(record['product'], record['quantity'], 'Return', record['id'])
            record['status'] = 'Completed' if action == 'complete' else 'Rejected'
        elif action == 'pay' and module == 'expenses' and record['status'] == 'Pending':
            record['status'] = 'Paid'
        elif action == 'cancel' and module == 'sales' and record['status'] == 'Held':
            record['status'] = 'Cancelled'
        else:
            raise ValueError('That action is not available for this record.')
        flash('Demo record updated.', 'success')
    except ValueError as error:
        flash(str(error), 'error')
    return redirect(url_for('demo.detail_page', module=module, record_id=record_id))


def csv_response(columns, rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([label for _, label, _ in columns])
    for row in rows:
        values = []
        for key, _, kind in columns:
            value = row.get(key, '')
            if kind == 'money':
                value = f'{value / 100:.2f}'
            value = str(value)
            values.append("'" + value if kind not in ('money', 'number') and value.startswith(('=', '+', '-', '@')) else value)
        writer.writerow(values)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}.csv"'})


@demo.get('/<module>/export')
def export(module):
    if module == 'inventory' and request.args.get('tab') == 'movements':
        return csv_response([('date', 'Date', 'date'), ('product', 'Product', 'text'), ('movement', 'Movement', 'text'), ('delta', 'Quantity change', 'number'), ('reason', 'Reference / reason', 'text'), ('by', 'Recorded by', 'text')], preview_data()['movements'], 'stock-movements-demo')
    return csv_response(MODULES[module]['columns'], filtered_rows(module), module + '-demo')


@demo.get('/reports')
def reports():
    data = preview_data()
    start = request.args.get('from', '2026-10-01')
    end = request.args.get('to', '2026-10-07')
    error = None
    try:
        if date.fromisoformat(start) > date.fromisoformat(end):
            raise ValueError
    except ValueError:
        error = 'Choose a valid date range with the start before the end.'
        start, end = '2026-10-01', '2026-10-07'
    section = request.args.get('section', 'sales')
    if section not in ('sales', 'inventory', 'expenses', 'returns'):
        section = 'sales'
    sales = [r for r in data['sales'] if r['status'] == 'Completed' and start <= r['date'] <= end]
    expenses = [r for r in data['expenses'] if start <= r['date'] <= end]
    returns = [r for r in data['returns'] if r['status'] == 'Completed' and start <= r['date'] <= end]
    revenue, refunds, spend = sum(r['total'] for r in sales), sum(r['refund'] for r in returns), sum(r['amount'] for r in expenses)
    costs = {r['name']: r['cost'] for r in data['products']}
    profit = revenue - refunds - spend - sum(costs.get(r['product'], 0) * r['quantity'] for r in sales)
    chart = []
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    # At most seven bins; long date ranges are grouped instead of truncated.
    step = max(1, ((last - first).days + 7) // 7)
    for offset in range(0, (last - first).days + 1, step):
        day = first + timedelta(days=offset)
        until = day + timedelta(days=min(step - 1, (last - day).days))
        chart.append({'label': day.strftime('%b %d'), 'amount': sum(r['total'] for r in sales if day.isoformat() <= r['date'] <= until.isoformat())})
    maximum = max((r['amount'] for r in chart), default=1) or 1
    for bar in chart:
        bar['height'] = bar['amount'] * 100 / maximum
    payments = [{'name': method, 'amount': sum(r['total'] for r in sales if r['method'] == method)} for method in ['Cash', 'Card', 'GCash', 'Bank transfer']]
    rows = sales if section == 'sales' else data['inventory'] if section == 'inventory' else expenses if section == 'expenses' else returns
    if request.args.get('export') == 'csv':
        return csv_response(MODULES[section]['columns'], rows, 'report-' + section)
    return render_template('reports.html', module='reports', stats=[stat('Gross sales', revenue, 'money'), stat('Refunds', refunds, 'money'), stat('Operating expenses', spend, 'money'), stat('Estimated profit', profit, 'money', 'After product costs, refunds, and expenses')],
                           start=start, end=end, section=section, chart=chart, payments=payments, revenue=revenue, config=MODULES[section], rows=rows, error=error, preview=True)


@demo.route('/settings', methods=['GET', 'POST'])
def settings():
    values = preview_data()['settings']
    section = request.args.get('section', 'shop')
    if section not in ('shop', 'sales', 'inventory', 'data'):
        section = 'shop'
    error = None
    if request.method == 'POST':
        keys = {'shop': ['shop_name', 'address', 'phone', 'email', 'receipt_footer', 'receipt_prefix'], 'sales': ['tax_rate'], 'inventory': ['reorder_level'], 'data': []}[section]
        changes = {key: request.form.get(key, '').strip() for key in keys}
        try:
            if any(len(value) > 1000 for value in changes.values()):
                raise ValueError('Keep each setting under 1,000 characters.')
            if section == 'shop' and not changes['shop_name']:
                raise ValueError('Enter the shop name.')
            if section == 'sales':
                rate = Decimal(changes['tax_rate'])
                if not rate.is_finite() or not 0 <= rate <= 100:
                    raise ValueError('Enter a tax rate from 0 to 100.')
                changes.update({key: key in request.form for key in ('price_inclusive', 'cash', 'card', 'gcash')})
            if section == 'inventory' and (not changes['reorder_level'].isdigit() or int(changes['reorder_level']) > 100000):
                raise ValueError('Enter a valid reorder level.')
            values.update(changes)
            flash('Demo settings saved.', 'success')
            return redirect(url_for('demo.settings', section=section))
        except (ValueError, InvalidOperation) as caught:
            error = str(caught) or 'Enter a valid number.'
    if request.args.get('download') == 'demo':
        return Response(json.dumps(preview_data(), indent=2), mimetype='application/json', headers={'Content-Disposition': 'attachment; filename="shop-ui-demo.json"'})
    rate = Decimal(values['tax_rate'])
    receipt_total = 850000 if values['price_inclusive'] else 850000 + int(Decimal(850000) * rate / 100)
    return render_template('settings.html', module='settings', values=values, section=section, error=error, receipt_total=receipt_total, preview=True)


@demo.post('/settings/reset')
def reset():
    current_app.extensions['demo_ui'][session['preview_id']] = fixtures()
    flash('Demo changes reset to the sample records.', 'success')
    return redirect(url_for('demo.settings', section='data'))


def init_app(app):
    app.extensions['demo_ui'] = {}
    app.register_blueprint(demo)


# Explicit paths preserve 404/405 behavior for unrelated application URLs.
for module in MODULES:
    demo.add_url_rule('/' + module, endpoint='list_page', view_func=list_page, defaults={'module': module}, methods=['GET'])
