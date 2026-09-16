import React from 'react';
import { 
  TrendingUp, 
  DollarSign, 
  ShoppingBag, 
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Guitar
} from 'lucide-react';
import './Dashboard.css';

const kpiData = [
  { 
    title: "Today's Sales", 
    value: "₱12,450.00", 
    trend: "+15%", 
    isPositive: true,
    icon: DollarSign,
    color: "var(--accent-primary)"
  },
  { 
    title: "Transactions", 
    value: "24", 
    trend: "+5%", 
    isPositive: true,
    icon: ShoppingBag,
    color: "var(--accent-secondary)"
  },
  { 
    title: "Low Stock Items", 
    value: "8", 
    trend: "-2", 
    isPositive: true,
    icon: AlertTriangle,
    color: "var(--accent-warning)"
  },
  { 
    title: "Total Revenue (Month)", 
    value: "₱145,200.00", 
    trend: "+8%", 
    isPositive: true,
    icon: TrendingUp,
    color: "var(--accent-success)"
  }
];

const recentSales = [
  { id: "TRX-1029", time: "10:24 AM", items: "Fender Stratocaster, Strings", total: "₱45,500.00", status: "Completed" },
  { id: "TRX-1028", time: "09:45 AM", items: "Ernie Ball Strings (x3)", total: "₱1,200.00", status: "Completed" },
  { id: "TRX-1027", time: "09:12 AM", items: "Focusrite Scarlett 2i2", total: "₱9,500.00", status: "Completed" },
  { id: "TRX-1026", time: "08:50 AM", items: "Guitar Stand, Picks", total: "₱850.00", status: "Completed" },
];

const topProducts = [
  { name: "Ernie Ball Regular Slinky", category: "Strings", sales: 124, stock: 45 },
  { name: "Fender Stratocaster Player", category: "Electric Guitars", sales: 12, stock: 3 },
  { name: "Boss DS-1 Distortion", category: "Pedals", sales: 28, stock: 15 },
  { name: "Yamaha F310", category: "Acoustic Guitars", sales: 45, stock: 8 },
];

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-container fade-in">
      <div className="dashboard-header flex-between">
        <div>
          <h1>Dashboard</h1>
          <p className="text-muted">Welcome back, here's what's happening at the shop today.</p>
        </div>
        <div className="date-badge glass-panel">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>

      <div className="kpi-grid">
        {kpiData.map((kpi, idx) => (
          <div className="kpi-card card" key={idx}>
            <div className="kpi-header flex-between">
              <span className="kpi-title">{kpi.title}</span>
              <div className="kpi-icon-wrapper" style={{ backgroundColor: `${kpi.color}20`, color: kpi.color }}>
                <kpi.icon size={20} />
              </div>
            </div>
            <div className="kpi-body">
              <h2 className="kpi-value">{kpi.value}</h2>
              <div className={`kpi-trend ${kpi.isPositive ? 'trend-up' : 'trend-down'}`}>
                {kpi.isPositive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                <span>{kpi.trend} from last week</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-content">
        <div className="recent-sales card">
          <div className="card-header flex-between">
            <h3>Recent Sales</h3>
            <button className="btn btn-secondary">View All</button>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Time</th>
                  <th>Items</th>
                  <th>Total</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentSales.map(sale => (
                  <tr key={sale.id}>
                    <td className="font-medium text-accent">{sale.id}</td>
                    <td>{sale.time}</td>
                    <td>{sale.items}</td>
                    <td className="font-bold">{sale.total}</td>
                    <td><span className="badge badge-success">{sale.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="top-products card">
          <div className="card-header flex-between">
            <h3>Top Selling Products</h3>
            <Guitar size={20} className="text-muted" />
          </div>
          <div className="product-list">
            {topProducts.map((product, idx) => (
              <div className="product-list-item flex-between" key={idx}>
                <div className="product-info">
                  <div className="product-name">{product.name}</div>
                  <div className="product-category text-muted">{product.category}</div>
                </div>
                <div className="product-stats">
                  <div className="product-sales font-bold">{product.sales} sold</div>
                  <div className={`product-stock text-muted ${product.stock < 10 ? 'text-warning' : ''}`}>
                    {product.stock} in stock
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
