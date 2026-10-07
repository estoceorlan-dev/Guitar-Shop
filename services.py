"""Server-side catalog, cart totals, and atomic sale posting."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from database import get_setting, transaction


def catalog(db, search='', category=''):
    return db.execute('''SELECT * FROM product_inventory WHERE is_active = 1
        AND (instr(lower(name), lower(?)) > 0 OR instr(lower(sku), lower(?)) > 0
             OR instr(lower(category_name), lower(?)) > 0)
        AND (? = '' OR category_name = ?) ORDER BY name''',
        (search, search, search, category, category)).fetchall()


def cart_totals(db, cart):
    items = []
    for product_id, quantity in cart.items():
        product = db.execute('SELECT * FROM product_inventory WHERE id = ? AND is_active = 1', (product_id,)).fetchone()
        if not product or type(quantity) is not int or quantity <= 0:
            raise ValueError('An item in the cart is no longer available. Clear the cart and try again.')
        items.append({'product': product, 'quantity': quantity})
    subtotal = sum(item['product']['selling_price'] * item['quantity'] for item in items)
    rate = get_setting(db, 'tax.rate_basis_points', 1200)
    if type(rate) is not int or not 0 <= rate <= 10000:
        raise ValueError('Invalid tax configuration.')
    inclusive = get_setting(db, 'tax.price_inclusive', False)
    # Integer half-up rounding: money never uses floating point calculations.
    tax = 0 if inclusive else (subtotal * rate + 5000) // 10000
    return {'items': items, 'subtotal': subtotal, 'tax': tax, 'total': subtotal + tax,
            'tax_percent': f'{rate / 100:g}', 'tax_inclusive': inclusive}


def complete_sale(db, cart, cashier_id, method):
    if method not in ('cash', 'card', 'gcash'):
        raise ValueError('Choose a valid payment method.')
    if not cart:
        raise ValueError('Add items before completing payment.')
    with transaction(db):
        totals = cart_totals(db, cart)
        if totals['total'] <= 0:
            raise ValueError('The sale total must be greater than zero.')
        for item in totals['items']:
            if item['quantity'] > item['product']['stock_quantity']:
                raise ValueError(f"Insufficient stock for {item['product']['name']}.")
        sale_id = uuid4().hex
        receipt = 'TRX-' + sale_id.upper()
        stamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        db.execute('''INSERT INTO sales (id, receipt_number, cashier_id, subtotal, tax_amount)
            VALUES (?, ?, ?, ?, ?)''', (sale_id, receipt, cashier_id, totals['subtotal'], totals['tax']))
        for item in totals['items']:
            product = item['product']
            db.execute('''INSERT INTO sale_items
                (id, sale_id, product_id, product_name, sku, quantity, unit_price, unit_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (uuid4().hex, sale_id, product['id'], product['name'], product['sku'], item['quantity'],
                 product['selling_price'], product['cost_price']))
        db.execute('''INSERT INTO payments (id, sale_id, method, status, amount, paid_at)
            VALUES (?, ?, ?, 'completed', ?, ?)''', (uuid4().hex, sale_id, method, totals['total'], stamp))
        # Existing schema triggers validate totals and post inventory exactly once.
        db.execute("UPDATE sales SET status = 'completed', completed_at = ? WHERE id = ?", (stamp, sale_id))
        db.execute('''INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, new_value)
            VALUES (?, ?, 'sale.completed', 'sales', ?, ?)''',
            (uuid4().hex, cashier_id, sale_id, json.dumps({'receipt_number': receipt, 'total_amount': totals['total']})))
    return receipt
