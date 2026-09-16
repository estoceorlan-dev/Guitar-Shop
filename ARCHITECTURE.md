# Roel's Guitar Shop — System Architecture

## 1. Overview

Roel's Guitar Shop is a desktop/local-first inventory, sales, and shop management system built with **React** and **SQLite**.

The system is designed for a small-to-medium guitar/music shop and prioritizes:

- Fast point-of-sale operations
- Product and inventory management
- Purchasing and supplier management
- Customer and sales tracking
- Stock movement and adjustment tracking
- User roles and permissions
- Reports and business monitoring
- Reliable local operation using SQLite
- Clear separation between UI, business logic, and database access

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Language | JavaScript / TypeScript |
| UI | React components + CSS/Tailwind if desired |
| Local database | SQLite |
| Database access | A SQLite-compatible backend/bridge |
| State management | React Context, Zustand, or equivalent |
| Routing | React Router |
| Charts/Reports | Recharts or equivalent |
| Authentication | Local application authentication |
| Packaging | Electron or another desktop shell if a desktop application is required |

### Architecture Style

The application follows a **layered modular architecture**:

```text
React UI
   ↓
Pages / Features
   ↓
Application Services
   ↓
Repositories / Data Access
   ↓
SQLite
```

The UI should not directly execute SQL queries. Database operations should pass through repositories/services so business rules remain centralized and testable.

## 3. Major Modules

### 3.1 Dashboard

Provides an overview of shop activity.

Features:

- Today's sales
- Sales revenue
- Number of transactions
- Low-stock products
- Out-of-stock products
- Recent sales
- Recent stock movements
- Top-selling products
- Purchase summary
- Quick actions

### 3.2 Point of Sale (POS)

The main sales interface.

Features:

- Product search
- Barcode/SKU search
- Product categories
- Add item to cart
- Change quantity
- Remove item
- Apply discount
- Customer selection
- Subtotal calculation
- Tax configuration if required
- Grand total
- Payment recording
- Cash/change calculation
- Multiple payment methods
- Complete sale
- Receipt generation/printing
- Hold/resume transaction if required
- Sale cancellation/void with permission

Payment methods can include:

- Cash
- GCash
- Card
- Bank transfer
- Other configured methods

### 3.3 Products

Manages the shop's products.

Features:

- Product list
- Product creation
- Product editing
- Product archive/deactivation
- SKU
- Barcode
- Product name
- Description
- Category
- Brand
- Cost price
- Selling price
- Stock quantity
- Reorder level
- Unit
- Product image
- Active/inactive status

Example product categories:

- Acoustic Guitars
- Electric Guitars
- Bass Guitars
- Ukuleles
- Guitar Effects
- Amplifiers
- Strings
- Picks
- Cables
- Straps
- Cases
- Stands
- Accessories
- Other Instruments

### 3.4 Categories and Brands

Provides reusable product classifications.

Features:

- Create category
- Edit category
- Archive category
- Create brand
- Edit brand
- Archive brand
- Product counts per category/brand

### 3.5 Inventory

Tracks current stock and stock movements.

Features:

- Current stock
- Stock-in
- Stock-out
- Stock adjustment
- Damaged stock
- Lost stock
- Returned stock
- Stock transfer if multiple locations are added later
- Low-stock alerts
- Out-of-stock alerts
- Inventory history
- Stock movement details

Every inventory-changing operation should create an auditable stock movement record.

### 3.6 Purchases

Records products purchased from suppliers.

Features:

- Create purchase order/record
- Select supplier
- Add products
- Quantity
- Unit cost
- Purchase total
- Purchase status
- Receive stock
- Partial receiving if required
- Purchase history
- Purchase details

Recommended purchase statuses:

- Draft
- Ordered
- Partially Received
- Received
- Cancelled

Receiving a purchase should increase inventory through the inventory service rather than directly modifying stock from the UI.

### 3.7 Suppliers

Manages suppliers and vendor information.

Features:

- Supplier list
- Add supplier
- Edit supplier
- Archive supplier
- Contact person
- Phone
- Email
- Address
- Notes
- Purchase history

### 3.8 Sales

Provides historical transaction management.

Features:

- Sales history
- Search/filter sales
- Sale details
- Customer information
- Payment information
- Itemized products
- Discounts
- Receipt reprint
- Refund/return handling
- Void/cancellation with permission

### 3.9 Customers

Stores customer information where needed.

Features:

- Customer list
- Add customer
- Edit customer
- Customer search
- Purchase history
- Contact information
- Notes
- Optional loyalty/customer statistics

Customer information should be optional for ordinary walk-in cash sales.

### 3.10 Returns and Refunds

Handles products returned by customers.

Features:

- Locate original sale
- Select returned items
- Return quantity
- Return reason
- Refund amount
- Restock returned item when appropriate
- Mark damaged/non-resellable return
- Record refund method
- Return history

Returns should create inventory movements rather than silently changing stock.

### 3.11 Expenses

Tracks shop expenses.

Features:

- Add expense
- Expense category
- Amount
- Date
- Description
- Payment method
- Recorded by
- Expense history

Example categories:

- Utilities
- Rent
- Transportation
- Supplies
- Maintenance
- Marketing
- Other

### 3.12 Reports

Provides business reports.

Reports may include:

- Daily sales
- Weekly sales
- Monthly sales
- Sales by date range
- Sales by product
- Sales by category
- Sales by brand
- Best-selling products
- Low-stock report
- Inventory valuation
- Purchase report
- Supplier purchase report
- Returns/refunds
- Expenses
- Profit estimate
- Cash/payment-method summary

Reports should preferably be generated from database queries/services rather than duplicating business calculations in individual pages.

### 3.13 Users, Roles, and Permissions

Controls access to system functionality.

Suggested roles:

#### Administrator

Full access.

#### Manager

- Dashboard
- POS
- Products
- Inventory
- Purchases
- Suppliers
- Sales
- Customers
- Reports
- Expenses
- Limited user management

#### Cashier

- POS
- Customers
- Sales history
- Basic product lookup
- Receipt printing

Sensitive actions such as voiding sales, changing prices, adjusting inventory, or issuing refunds should require appropriate permissions.

### 3.14 Settings

System configuration.

Features:

- Shop information
- Logo
- Address/contact information
- Currency
- Tax settings
- Receipt settings
- Payment methods
- Product settings
- Inventory/reorder settings
- User settings
- Database backup/restore
- Application preferences

## 4. Database Architecture

SQLite should be the primary persistent data store.

### Core Tables

```text
users
roles
permissions
role_permissions

products
categories
brands

suppliers
customers

purchases
purchase_items

sales
sale_items
payments

inventory_movements

returns
return_items

expenses

settings
audit_logs
```

### Suggested Relationships

```text
categories ────────┐
                    ├── products
brands ────────────┘

suppliers ─────────── purchases ─── purchase_items ─── products

customers ─────────── sales ─────── sale_items ─────── products
                         │
                         └──────── payments

sales ─────────────── returns ───── return_items

products ─────────── inventory_movements

users ────────────── sales
users ────────────── purchases
users ────────────── inventory_movements
users ────────────── audit_logs
```

## 5. Important Database Design Rules

### Product Stock

Do not rely only on manually edited `products.stock_quantity`.

The system should treat inventory movements as the audit trail.

A product can have:

```text
Opening Stock
+ Purchase Received
+ Customer Return
+ Stock Adjustment In
- Sale
- Supplier Return
- Damaged/Lost Stock
= Current Stock
```

A cached `stock_quantity` field may still be maintained for fast POS queries, but all changes must go through the inventory service.

### Money

Store monetary values using integer minor units where practical.

For Philippine pesos:

```text
₱150.50 → 15050 centavos
```

This avoids floating-point rounding problems.

### IDs

Use stable primary keys. UUIDs or generated string IDs are preferable if the system may later synchronize with a server.

### Timestamps

Store timestamps consistently, preferably in ISO 8601/UTC internally, while displaying them in the user's local timezone.

### Soft Deletion

Products, categories, brands, suppliers, customers, and users should generally be archived/deactivated rather than physically deleted when historical transactions reference them.

## 6. Application Structure

Recommended React project structure:

```text
src/
├── app/
│   ├── App.tsx
│   ├── routes.tsx
│   └── providers/
│
├── components/
│   ├── ui/
│   ├── forms/
│   ├── tables/
│   ├── modals/
│   └── layout/
│
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── pos/
│   ├── products/
│   ├── categories/
│   ├── brands/
│   ├── inventory/
│   ├── purchases/
│   ├── suppliers/
│   ├── sales/
│   ├── customers/
│   ├── returns/
│   ├── expenses/
│   ├── reports/
│   ├── users/
│   └── settings/
│
├── services/
│   ├── auth/
│   ├── inventory/
│   ├── sales/
│   ├── purchases/
│   ├── reports/
│   └── printing/
│
├── repositories/
│   ├── productRepository.ts
│   ├── saleRepository.ts
│   ├── purchaseRepository.ts
│   ├── inventoryRepository.ts
│   └── ...
│
├── database/
│   ├── connection.ts
│   ├── migrations/
│   ├── schema/
│   └── seed/
│
├── hooks/
├── utils/
├── types/
├── constants/
└── main.tsx
```

## 7. Feature Responsibilities

Each feature should contain its own UI and feature-specific logic where practical.

Example:

```text
features/pos/
├── pages/
│   └── POSPage.tsx
├── components/
│   ├── ProductSearch.tsx
│   ├── Cart.tsx
│   ├── CartItem.tsx
│   ├── PaymentModal.tsx
│   └── ReceiptPreview.tsx
├── hooks/
│   └── useCart.ts
├── pos.types.ts
└── pos.utils.ts
```

The POS UI should call a sales/application service:

```text
POSPage
   ↓
SaleService
   ↓
SaleRepository
   ↓
SQLite
```

## 8. Transaction Boundaries

Sales and purchases must use database transactions.

### Completing a Sale

Conceptually:

```text
BEGIN TRANSACTION

1. Validate cart
2. Validate product availability
3. Create sale
4. Create sale items
5. Create payment records
6. Decrease product stock
7. Create inventory movement records
8. Create audit log

COMMIT
```

If any critical step fails:

```text
ROLLBACK
```

This prevents situations such as a completed sale with unchanged inventory.

### Receiving a Purchase

```text
BEGIN TRANSACTION

1. Validate purchase
2. Mark purchase as received
3. Create/update purchase items
4. Increase stock
5. Create inventory movements
6. Create audit log

COMMIT
```

## 9. Authentication and Authorization

Authentication should be handled separately from authorization.

```text
Login
  ↓
Verify credentials
  ↓
Load user
  ↓
Load role/permissions
  ↓
Create authenticated session
  ↓
Allow/deny feature actions
```

Passwords must never be stored as plaintext. Use a strong password hashing algorithm supported by the application runtime.

Authorization should be enforced in application services, not only by hiding UI buttons.

For example:

```text
Cashier sees "Void Sale" → permission denied
Manager sees "Void Sale" → permission checked → allowed
```

## 10. Audit Logging

Important business actions should be recorded.

Examples:

- Login
- Logout
- Product creation/edit
- Price change
- Stock adjustment
- Purchase received
- Sale completed
- Sale voided
- Refund issued
- User/role changes
- Settings changes

Suggested fields:

```text
audit_logs
├── id
├── user_id
├── action
├── entity_type
├── entity_id
├── old_value
├── new_value
├── created_at
└── metadata
```

## 11. Navigation

Recommended main navigation:

```text
Dashboard
POS
Sales
Products
Inventory
Purchases
Suppliers
Customers
Returns
Expenses
Reports
Users
Settings
```

Navigation items should be filtered according to the authenticated user's permissions.

## 12. POS Workflow

```text
Open POS
   ↓
Search / scan product
   ↓
Add to cart
   ↓
Adjust quantity
   ↓
Optional customer
   ↓
Apply discount
   ↓
Review total
   ↓
Select payment
   ↓
Confirm payment
   ↓
Complete transaction
   ↓
Update inventory
   ↓
Save audit log
   ↓
Print/show receipt
```

## 13. Inventory Workflow

```text
Purchase Received ──→ Stock IN
Customer Return ─────→ Stock IN
Adjustment IN ───────→ Stock IN

Sale ────────────────→ Stock OUT
Supplier Return ─────→ Stock OUT
Damage/Loss ─────────→ Stock OUT
Adjustment OUT ──────→ Stock OUT
```

All of these should produce an `inventory_movements` record.

## 14. Reporting Architecture

Reports should use dedicated query/service functions.

```text
Reports Page
   ↓
Report Service
   ↓
Report Queries
   ↓
SQLite
   ↓
Aggregated Report Data
   ↓
Charts / Tables / Export
```

Avoid loading all transactions into React and performing large aggregations in the browser.

## 15. SQLite Considerations

SQLite is appropriate for a local-first shop system because it is:

- Lightweight
- Serverless
- Easy to deploy
- Reliable for a single-shop/small deployment
- Transactional
- Suitable for local inventory and POS workloads

Enable foreign keys:

```sql
PRAGMA foreign_keys = ON;
```

Use indexes on frequently queried fields such as:

```text
products.sku
products.barcode
products.name
products.category_id
sales.created_at
sales.customer_id
sale_items.sale_id
sale_items.product_id
inventory_movements.product_id
purchases.created_at
```

## 16. Backup and Recovery

The system should provide database backup functionality.

Recommended approach:

```text
Application
   ↓
SQLite database
   ↓
Backup command/service
   ↓
Timestamped .db backup
```

Backups should not be created by simply copying a live database file while uncontrolled writes are occurring. Use SQLite's supported backup mechanisms or ensure a safe backup transaction/state.

Recommended user-facing features:

- Create backup
- Restore backup
- Show last backup date
- Confirm before restore
- Validate backup before restoration

## 17. Offline-First Design

The application should remain fully functional without an internet connection.

Core operations that should work offline:

- Login
- Product lookup
- POS
- Sales
- Inventory
- Purchases
- Customers
- Reports
- Settings

Internet-dependent features, if added later, should be isolated from the core local system.

## 18. Future Expansion

The architecture should leave room for future features without requiring a major rewrite.

Possible future modules:

- Multiple branches
- Cloud synchronization
- Online store
- Customer loyalty
- Barcode scanner integration
- Receipt printer integration
- Cash drawer integration
- Supplier purchase orders
- Serial-number tracking for guitars/electronics
- Warranty tracking
- Product variants
- Consignment inventory
- Employee attendance
- Advanced accounting
- Cloud backup

### Multi-Branch Future Model

If multiple branches are eventually required, add concepts such as:

```text
branches
branch_users
branch_inventory
stock_transfers
```

The current SQLite design should avoid hard-coding the assumption that a product can only ever exist in one location.

## 19. Security Principles

- Hash passwords securely.
- Never store plaintext passwords.
- Validate all user input.
- Use parameterized SQL queries.
- Enforce authorization in services.
- Record sensitive operations in audit logs.
- Do not expose raw database access to arbitrary UI components.
- Validate inventory quantities before committing changes.
- Use transactions for financial/inventory operations.
- Restrict database backup/restore actions to authorized users.

## 20. Core Architectural Principle

The most important rule for the system is:

> **The UI requests business operations; services enforce business rules; repositories handle persistence; SQLite stores the data.**

For example, the POS should not do:

```text
React → UPDATE products SET stock = stock - 1
```

Instead:

```text
React POS
   ↓
SaleService.completeSale()
   ↓
InventoryService
   ↓
SaleRepository + InventoryRepository
   ↓
SQLite transaction
```

This keeps the system maintainable, prevents inconsistent inventory, and makes the application easier to extend later.
