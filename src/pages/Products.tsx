import React, { useState } from 'react';
import { 
  Plus, 
  Search, 
  Filter, 
  MoreVertical,
  Edit2,
  Trash2,
  Archive
} from 'lucide-react';
import './Products.css';

const mockProductsData = [
  { id: "PRD-001", sku: "STR-PL-BLK", name: "Fender Stratocaster Player", category: "Electric Guitars", brand: "Fender", cost: 35000, price: 42500, stock: 5, status: "Active" },
  { id: "PRD-002", sku: "YAM-F310-NAT", name: "Yamaha F310 Acoustic", category: "Acoustic Guitars", brand: "Yamaha", cost: 6000, price: 8500, stock: 12, status: "Active" },
  { id: "PRD-003", sku: "ERN-2221-1046", name: "Ernie Ball Regular Slinky", category: "Strings", brand: "Ernie Ball", cost: 300, price: 450, stock: 45, status: "Active" },
  { id: "PRD-004", sku: "BOS-DS1-DIS", name: "Boss DS-1 Distortion", category: "Pedals", brand: "Boss", cost: 2200, price: 3200, stock: 8, status: "Active" },
  { id: "PRD-005", sku: "FOC-SCA-2I2", name: "Focusrite Scarlett 2i2", category: "Audio Interfaces", brand: "Focusrite", cost: 7800, price: 9500, stock: 4, status: "Active" },
  { id: "PRD-006", sku: "TOR-PIC-114", name: "Tortex Picks (12-pack)", category: "Accessories", brand: "Dunlop", cost: 120, price: 250, stock: 100, status: "Active" },
  { id: "PRD-007", sku: "HER-GS414B", name: "Hercules Guitar Stand", category: "Accessories", brand: "Hercules", cost: 800, price: 1200, stock: 15, status: "Active" },
  { id: "PRD-008", sku: "MAR-MG15G", name: "Marshall MG15G Amp", category: "Amplifiers", brand: "Marshall", cost: 4500, price: 6500, stock: 6, status: "Active" },
  { id: "PRD-009", sku: "COR-CR200-GT", name: "Cort CR200 Gold Top", category: "Electric Guitars", brand: "Cort", cost: 18000, price: 22000, stock: 0, status: "Out of Stock" },
  { id: "PRD-010", sku: "KOR-PCH-CLP", name: "Korg Pitchclip 2", category: "Accessories", brand: "Korg", cost: 500, price: 850, stock: 2, status: "Low Stock" },
];

export const Products: React.FC = () => {
  const [search, setSearch] = useState("");

  const filteredProducts = mockProductsData.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.sku.toLowerCase().includes(search.toLowerCase()) ||
    p.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="products-container fade-in">
      <div className="products-header flex-between">
        <div>
          <h1>Products</h1>
          <p className="text-muted">Manage your inventory, pricing, and product details.</p>
        </div>
        <button className="btn btn-primary">
          <Plus size={18} />
          <span>Add Product</span>
        </button>
      </div>

      <div className="products-toolbar card flex-between">
        <div className="search-wrapper">
          <Search size={18} className="text-muted" />
          <input 
            type="text" 
            placeholder="Search by name, SKU, or category..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="toolbar-search"
          />
        </div>
        <div className="toolbar-actions">
          <button className="btn btn-secondary">
            <Filter size={18} />
            <span>Filter</span>
          </button>
          <button className="btn btn-secondary">
            <span>Export</span>
          </button>
        </div>
      </div>

      <div className="products-table-container card">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Brand</th>
                <th>Cost</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map(product => (
                <tr key={product.id}>
                  <td className="text-muted font-medium">{product.sku}</td>
                  <td className="font-bold">{product.name}</td>
                  <td>{product.category}</td>
                  <td>{product.brand}</td>
                  <td className="text-muted">₱{product.cost.toLocaleString()}</td>
                  <td className="text-accent font-bold">₱{product.price.toLocaleString()}</td>
                  <td>
                    <span className={`stock-indicator ${product.stock === 0 ? 'stock-out' : product.stock < 5 ? 'stock-low' : 'stock-good'}`}>
                      {product.stock}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${
                      product.status === 'Active' ? 'badge-success' : 
                      product.status === 'Low Stock' ? 'badge-warning' : 
                      'badge-danger'
                    }`}>
                      {product.status}
                    </span>
                  </td>
                  <td>
                    <div className="action-menu">
                      <button className="action-btn"><Edit2 size={16} /></button>
                      <button className="action-btn text-danger"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="pagination flex-between">
          <div className="text-muted">Showing {filteredProducts.length} of {mockProductsData.length} products</div>
          <div className="page-controls">
            <button className="btn btn-secondary" disabled>Previous</button>
            <button className="btn btn-secondary">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
};
