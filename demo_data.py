"""Fictional UI fixtures. These records never write to the shop database."""

from copy import deepcopy


def field(name, label, kind='text', options=None, required=True):
    return {'name': name, 'label': label, 'type': kind, 'options': options or [], 'required': required}


PRODUCT_NAMES = ['Fender Stratocaster Player', 'Yamaha F310 Acoustic', 'Ernie Ball Regular Slinky',
                 'Boss DS-1 Distortion', 'Focusrite Scarlett 2i2', 'Tortex Picks (12-pack)',
                 'Hercules Guitar Stand', 'Marshall MG15G Amp', 'Cort CR200 Gold Top', 'Korg Pitchclip 2']
CATEGORIES = ['Electric Guitars', 'Acoustic Guitars', 'Strings', 'Pedals', 'Audio Interfaces', 'Accessories', 'Amplifiers']
BRANDS = ['Fender', 'Yamaha', 'Ernie Ball', 'Boss', 'Focusrite', 'Dunlop', 'Hercules', 'Marshall', 'Cort', 'Korg']
CUSTOMERS = ['Alex Rivera', 'Jamie Santos', 'Pat Reyes', 'Chris Mendoza', 'Sam Cruz', 'Walk-in customer']
SUPPLIERS = ['Manila Music Supply', 'Soundhouse Distribution', 'Guitar Avenue Trading', 'Audio Essentials PH']
PAYMENTS = ['Cash', 'GCash', 'Card', 'Bank transfer']

MODULES = {
    'products': {'title': 'Products', 'subtitle': 'Manage instruments, accessories, and catalog details.', 'icon': 'guitar', 'group': 'Catalog',
        'action': 'Add product', 'statuses': ['Active', 'Archived'],
        'columns': [('sku', 'SKU', 'muted'), ('name', 'Product', 'strong'), ('category', 'Category', 'text'), ('brand', 'Brand', 'text'), ('cost', 'Cost', 'money'), ('price', 'Price', 'money'), ('stock', 'Stock', 'number'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Product name'), field('sku', 'SKU'), field('barcode', 'Barcode', required=False), field('category', 'Category', 'select', CATEGORIES), field('brand', 'Brand', 'select', BRANDS), field('cost', 'Cost price (PHP)', 'money'), field('price', 'Selling price (PHP)', 'money'), field('reorder', 'Reorder level', 'number'), field('unit', 'Unit', 'select', ['Piece', 'Set', 'Pack']), field('description', 'Description', 'textarea', required=False)]},
    'inventory': {'title': 'Inventory', 'subtitle': 'Keep every instrument and accessory accounted for.', 'icon': 'package', 'group': 'Catalog',
        'action': 'Adjust stock', 'statuses': ['In stock', 'Low stock', 'Out of stock'],
        'columns': [('name', 'Product', 'strong'), ('sku', 'SKU', 'muted'), ('category', 'Category', 'text'), ('stock', 'On hand', 'number'), ('reorder', 'Reorder at', 'number'), ('value', 'Stock value', 'money'), ('status', 'Status', 'badge')],
        'fields': [field('product', 'Product', 'select', PRODUCT_NAMES), field('movement', 'Adjustment type', 'select', ['Stock in', 'Stock out', 'Damaged', 'Lost']), field('quantity', 'Quantity', 'number'), field('reason', 'Reason', 'textarea')]},
    'purchases': {'title': 'Purchases', 'subtitle': 'Order from suppliers and track incoming stock.', 'icon': 'truck', 'group': 'Operations',
        'action': 'New purchase', 'statuses': ['Draft', 'Ordered', 'Partially received', 'Received', 'Cancelled'],
        'columns': [('id', 'Purchase order', 'strong'), ('supplier', 'Supplier', 'text'), ('date', 'Order date', 'date'), ('product', 'Product', 'text'), ('quantity', 'Quantity', 'number'), ('total', 'Total', 'money'), ('status', 'Status', 'badge')],
        'fields': [field('supplier', 'Supplier', 'select', SUPPLIERS), field('date', 'Order date', 'date'), field('product', 'Product', 'select', PRODUCT_NAMES), field('quantity', 'Quantity', 'number'), field('unit_cost', 'Unit cost (PHP)', 'money'), field('status', 'Status', 'select', ['Draft', 'Ordered']), field('notes', 'Notes', 'textarea', required=False)]},
    'suppliers': {'title': 'Suppliers', 'subtitle': 'Your partners in keeping the shop stocked.', 'icon': 'truck', 'group': 'Operations',
        'action': 'Add supplier', 'statuses': ['Active', 'Archived'],
        'columns': [('name', 'Supplier', 'strong'), ('contact', 'Contact person', 'text'), ('email', 'Email', 'text'), ('phone', 'Phone', 'text'), ('orders', 'Orders', 'number'), ('spend', 'Total purchases', 'money'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Company name'), field('contact', 'Contact person'), field('email', 'Email', 'email'), field('phone', 'Phone', 'tel'), field('address', 'Address', 'textarea'), field('notes', 'Notes', 'textarea', required=False)]},
    'sales': {'title': 'Sales History', 'subtitle': 'Find receipts, review payments, and follow every sale.', 'icon': 'receipt', 'group': 'Shop',
        'action': None, 'statuses': ['Completed', 'Held', 'Cancelled'],
        'columns': [('id', 'Receipt', 'strong'), ('date', 'Date', 'date'), ('customer', 'Customer', 'text'), ('items', 'Items', 'number'), ('method', 'Payment', 'text'), ('total', 'Total', 'money'), ('status', 'Status', 'badge')], 'fields': []},
    'customers': {'title': 'Customers', 'subtitle': 'Get to know the musicians who shop with you.', 'icon': 'users', 'group': 'Shop',
        'action': 'Add customer', 'statuses': ['Active', 'Archived'],
        'columns': [('name', 'Customer', 'strong'), ('email', 'Email', 'text'), ('phone', 'Phone', 'text'), ('visits', 'Visits', 'number'), ('spend', 'Total spent', 'money'), ('last_visit', 'Last visit', 'date'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Full name'), field('email', 'Email', 'email', required=False), field('phone', 'Phone', 'tel', required=False), field('address', 'Address', 'textarea', required=False), field('notes', 'Notes', 'textarea', required=False)]},
    'returns': {'title': 'Returns & Refunds', 'subtitle': 'Handle returns carefully and keep a clear record.', 'icon': 'return', 'group': 'Operations',
        'action': 'New return', 'statuses': ['Requested', 'Completed', 'Rejected'],
        'columns': [('id', 'Return', 'strong'), ('receipt', 'Original receipt', 'text'), ('customer', 'Customer', 'text'), ('product', 'Product', 'text'), ('quantity', 'Quantity', 'number'), ('refund', 'Refund', 'money'), ('status', 'Status', 'badge')],
        'fields': [field('receipt', 'Original receipt', 'select', ['TRX-1035', 'TRX-1034', 'TRX-1033', 'TRX-1032', 'TRX-1031']), field('product', 'Returned product', 'select', PRODUCT_NAMES), field('quantity', 'Quantity', 'number'), field('reason', 'Return reason', 'textarea'), field('condition', 'Condition', 'select', ['Resellable', 'Damaged', 'Defective']), field('restock', 'Restock item', 'select', ['Yes', 'No']), field('refund', 'Refund amount (PHP)', 'money'), field('method', 'Refund method', 'select', PAYMENTS)]},
    'expenses': {'title': 'Expenses', 'subtitle': 'Track the everyday costs of running your shop.', 'icon': 'cash', 'group': 'Finance',
        'action': 'Add expense', 'statuses': ['Paid', 'Pending'],
        'columns': [('description', 'Expense', 'strong'), ('category', 'Category', 'text'), ('date', 'Date', 'date'), ('amount', 'Amount', 'money'), ('method', 'Payment', 'text'), ('recorded_by', 'Recorded by', 'text'), ('status', 'Status', 'badge')],
        'fields': [field('description', 'Description'), field('category', 'Category', 'select', ['Rent', 'Utilities', 'Transportation', 'Supplies', 'Maintenance', 'Marketing', 'Other']), field('amount', 'Amount (PHP)', 'money'), field('date', 'Date', 'date'), field('method', 'Payment method', 'select', PAYMENTS), field('status', 'Status', 'select', ['Paid', 'Pending']), field('reference', 'Reference number', required=False), field('notes', 'Notes', 'textarea', required=False)]},
    'categories': {'title': 'Categories', 'subtitle': 'Organize the catalog so products are easy to find.', 'icon': 'layers', 'group': 'Catalog',
        'action': 'Add category', 'statuses': ['Active', 'Archived'], 'cards': True,
        'columns': [('name', 'Category', 'strong'), ('description', 'Description', 'text'), ('products', 'Products', 'number'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Category name'), field('description', 'Description', 'textarea', required=False)]},
    'brands': {'title': 'Brands', 'subtitle': 'The names behind your instruments and gear.', 'icon': 'tag', 'group': 'Catalog',
        'action': 'Add brand', 'statuses': ['Active', 'Archived'], 'cards': True,
        'columns': [('name', 'Brand', 'strong'), ('description', 'Description', 'text'), ('products', 'Products', 'number'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Brand name'), field('description', 'Description', 'textarea', required=False)]},
    'users': {'title': 'Staff & Permissions', 'subtitle': 'Manage your team and review who can do what.', 'icon': 'shield', 'group': 'Administration',
        'action': 'Add staff member', 'statuses': ['Active', 'Inactive'],
        'columns': [('name', 'Staff member', 'strong'), ('username', 'Username', 'muted'), ('role', 'Role', 'text'), ('email', 'Email', 'text'), ('last_active', 'Last active', 'text'), ('status', 'Status', 'badge')],
        'fields': [field('name', 'Full name'), field('username', 'Username'), field('email', 'Email', 'email'), field('role', 'Role', 'select', ['Administrator', 'Manager', 'Cashier']), field('status', 'Status', 'select', ['Active', 'Inactive'])]},
}

NAVIGATION = [
    ('Shop', [('dashboard', 'Dashboard', 'dashboard', ['Administrator', 'Manager']), ('pos', 'Point of Sale', 'cart', ['Administrator', 'Manager', 'Cashier']), ('sales', 'Sales History', 'receipt', ['Administrator', 'Manager', 'Cashier']), ('customers', 'Customers', 'users', ['Administrator', 'Manager', 'Cashier'])]),
    ('Catalog', [(key, MODULES[key]['title'], MODULES[key]['icon'], ['Administrator', 'Manager']) for key in ['inventory', 'categories', 'brands']]),
    ('Operations', [(key, MODULES[key]['title'], MODULES[key]['icon'], ['Administrator', 'Manager']) for key in ['purchases', 'suppliers', 'returns']]),
    ('Finance', [('expenses', 'Expenses', 'cash', ['Administrator', 'Manager']), ('reports', 'Reports', 'chart', ['Administrator', 'Manager'])]),
    ('Administration', [('users', 'Staff & Permissions', 'shield', ['Administrator']), ('settings', 'Settings', 'settings', ['Administrator'])]),
]
NAVIGATION[1][1].insert(0, ('products', 'Products', 'guitar', ['Administrator', 'Manager']))


def allowed_roles(module):
    if module in ('users', 'settings'):
        return ['Administrator']
    if module in ('sales', 'customers'):
        return ['Administrator', 'Manager', 'Cashier']
    return ['Administrator', 'Manager']


def fixtures():
    prices = [4250000, 850000, 45000, 320000, 950000, 25000, 120000, 650000, 2200000, 85000]
    costs = [3500000, 600000, 30000, 220000, 780000, 12000, 80000, 450000, 1800000, 50000]
    quantities = [5, 12, 45, 8, 4, 100, 15, 6, 0, 2]
    cats = [0, 1, 2, 3, 4, 5, 5, 6, 0, 5]
    skus = ['STR-PL-BLK', 'YAM-F310-NAT', 'ERN-2221-1046', 'BOS-DS1-DIS', 'FOC-SCA-2I2', 'TOR-PIC-114', 'HER-GS414B', 'MAR-MG15G', 'COR-CR200-GT', 'KOR-PCH-CLP']
    inventory = [{'id': f'PRD-{i+1:03}', 'name': name, 'sku': skus[i], 'category': CATEGORIES[cats[i]],
                  'brand': BRANDS[i], 'stock': quantities[i], 'reorder': 5, 'cost': costs[i], 'price': prices[i],
                  'value': quantities[i] * costs[i], 'status': 'Out of stock' if quantities[i] == 0 else 'Low stock' if quantities[i] <= 5 else 'In stock'} for i, name in enumerate(PRODUCT_NAMES)]
    sales = []
    for i, (product, quantity, day, method) in enumerate([(0, 1, 7, 'Card'), (2, 3, 7, 'Cash'), (1, 1, 6, 'GCash'), (3, 1, 5, 'Cash'), (5, 2, 4, 'Cash'), (7, 1, 3, 'Card'), (2, 4, 2, 'GCash'), (9, 1, 1, 'Cash')]):
        subtotal = prices[product] * quantity
        sales.append({'id': f'TRX-{1035-i}', 'date': f'2026-10-{day:02}', 'time': f'{10+i:02}:24', 'customer': CUSTOMERS[i % 6], 'items': quantity,
                      'product': PRODUCT_NAMES[product], 'quantity': quantity, 'unit_price': prices[product], 'subtotal': subtotal, 'tax': subtotal * 12 // 100,
                      'total': subtotal * 112 // 100, 'method': method, 'cashier': 'Juan Cruz' if i % 2 else 'Maria Reyes', 'status': 'Completed'})
    sales += [{'id': 'TRX-1027', 'date': '2026-10-07', 'time': '14:05', 'customer': CUSTOMERS[1], 'items': 1, 'product': PRODUCT_NAMES[4], 'quantity': 1, 'unit_price': prices[4], 'subtotal': prices[4], 'tax': 114000, 'total': 1064000, 'method': 'Cash', 'cashier': 'Juan Cruz', 'status': 'Held'}]
    purchases = [{'id': f'PO-{2026+i}', 'supplier': SUPPLIERS[i % 4], 'date': f'2026-10-{6-i:02}', 'product': PRODUCT_NAMES[i], 'quantity': [3, 8, 50, 10, 4, 25][i],
                  'unit_cost': costs[i], 'total': costs[i] * [3, 8, 50, 10, 4, 25][i], 'received': [0, 4, 50, 0, 4, 0][i],
                  'status': ['Ordered', 'Partially received', 'Received', 'Draft', 'Received', 'Cancelled'][i], 'notes': 'Delivery to the shop. Inspect items before receiving.'} for i in range(6)]
    customers = [{'id': f'CUS-{i+1:03}', 'name': name, 'email': f'{name.split()[0].lower()}@example.com', 'phone': f'0900 000 {i+1:04}',
                  'visits': [8, 5, 12, 3, 6][i], 'spend': [7250000, 3400000, 825000, 980000, 1625000][i], 'last_visit': f'2026-10-{7-i:02}',
                  'address': 'Sample address, Quezon City', 'notes': ['Prefers electric guitars.', 'Acoustic player.', 'Regular string customer.', 'Interested in pedals.', 'Bass player.'][i], 'status': 'Active'} for i, name in enumerate(CUSTOMERS[:-1])]
    suppliers = [{'id': f'SUP-{i+1:03}', 'name': name, 'contact': ['Nico Garcia', 'Lea Torres', 'Mark Aquino', 'Ria Lim'][i],
                  'email': f'sales{i+1}@example.com', 'phone': f'02 8000 {i+1:04}', 'address': 'Sample business address, Metro Manila',
                  'orders': [12, 8, 5, 3][i], 'spend': [48500000, 19200000, 13500000, 7800000][i], 'notes': 'Typical lead time: 3–5 business days.', 'status': 'Active'} for i, name in enumerate(SUPPLIERS)]
    returns = [{'id': 'RMA-301', 'receipt': 'TRX-1032', 'customer': CUSTOMERS[3], 'product': PRODUCT_NAMES[3], 'quantity': 1, 'refund': 358400, 'method': 'Cash', 'reason': 'Switch to a different pedal.', 'condition': 'Resellable', 'restock': 'Yes', 'date': '2026-10-07', 'status': 'Requested'},
               {'id': 'RMA-300', 'receipt': 'TRX-1034', 'customer': CUSTOMERS[1], 'product': PRODUCT_NAMES[2], 'quantity': 1, 'refund': 50400, 'method': 'Cash', 'reason': 'Unopened duplicate purchase.', 'condition': 'Resellable', 'restock': 'Yes', 'date': '2026-10-06', 'status': 'Completed'},
               {'id': 'RMA-299', 'receipt': 'TRX-1031', 'customer': CUSTOMERS[4], 'product': PRODUCT_NAMES[5], 'quantity': 1, 'refund': 28000, 'method': 'GCash', 'reason': 'Packaging damaged.', 'condition': 'Damaged', 'restock': 'No', 'date': '2026-10-04', 'status': 'Rejected'}]
    expenses = [{'id': f'EXP-{401+i}', 'description': description, 'category': category, 'amount': amount, 'date': f'2026-10-{7-i:02}',
                 'method': 'Bank transfer' if i == 0 else 'Cash', 'recorded_by': 'Maria Reyes', 'status': 'Pending' if i == 4 else 'Paid', 'reference': f'EXPREF-{401+i}', 'notes': ''}
                for i, (description, category, amount) in enumerate([('October shop rent', 'Rent', 1800000), ('Electricity bill', 'Utilities', 350000), ('Receipt rolls and bags', 'Supplies', 85000), ('Supplier delivery', 'Transportation', 50000), ('Display rack repair', 'Maintenance', 95000), ('Social media promotion', 'Marketing', 150000)])]
    users = [{'id': f'STAFF-{i+1:03}', 'name': name, 'username': username, 'role': role, 'email': f'{username}@example.com', 'status': 'Inactive' if i == 4 else 'Active', 'last_active': 'Today, 10:24 AM' if i < 3 else 'Oct 5, 2026'}
             for i, (name, username, role) in enumerate([('Roel Santos', 'roel', 'Administrator'), ('Maria Reyes', 'maria', 'Manager'), ('Juan Cruz', 'juan', 'Cashier'), ('Ana Garcia', 'ana', 'Cashier'), ('Paolo Mendoza', 'paolo', 'Manager')])]
    movements = [{'id': 'MOV-501', 'date': '2026-10-07', 'product': PRODUCT_NAMES[0], 'movement': 'Sale', 'delta': -1, 'reason': 'TRX-1035', 'by': 'Maria Reyes'},
                 {'id': 'MOV-500', 'date': '2026-10-06', 'product': PRODUCT_NAMES[1], 'movement': 'Purchase', 'delta': 4, 'reason': 'PO-2027', 'by': 'Maria Reyes'},
                 {'id': 'MOV-499', 'date': '2026-10-06', 'product': PRODUCT_NAMES[2], 'movement': 'Return', 'delta': 1, 'reason': 'RMA-300', 'by': 'Roel Santos'}]
    return deepcopy({'products': [dict(p, status='Active', unit='Piece', description='Demo catalog item', barcode=f'DEMO-{i+1:08}') for i, p in enumerate(inventory)], 'inventory': inventory, 'sales': sales, 'purchases': purchases, 'customers': customers, 'suppliers': suppliers,
                     'returns': returns, 'expenses': expenses, 'users': users, 'movements': movements,
                     'categories': [{'id': f'CAT-{i+1:03}', 'name': name, 'description': f'{name} and related gear.', 'products': sum(p['category'] == name for p in inventory), 'status': 'Active'} for i, name in enumerate(CATEGORIES)],
                     'brands': [{'id': f'BRD-{i+1:03}', 'name': name, 'description': f'Instruments and accessories by {name}.', 'products': 1, 'status': 'Active'} for i, name in enumerate(BRANDS)],
                     'settings': {'shop_name': "Roel's Guitar Shop", 'address': 'Sample address, Manila, Philippines', 'phone': '02 8000 1234', 'email': 'shop@example.com',
                                  'currency': 'PHP', 'timezone': 'Asia/Manila', 'tax_rate': '12', 'price_inclusive': False, 'receipt_footer': 'Thank you for shopping with us!', 'receipt_prefix': 'TRX', 'reorder_level': '5', 'cash': True, 'card': True, 'gcash': True}})
