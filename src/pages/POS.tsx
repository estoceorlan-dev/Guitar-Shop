import React, { useState } from 'react';
import { 
  Search, 
  ShoppingCart, 
  Trash2, 
  Plus, 
  Minus,
  CreditCard,
  Banknote,
  Smartphone
} from 'lucide-react';
import './POS.css';

const mockProducts = [
  { id: 1, name: "Fender Stratocaster", price: 42500, stock: 5, category: "Electric Guitars", image: "🎸" },
  { id: 2, name: "Yamaha F310 Acoustic", price: 8500, stock: 12, category: "Acoustic Guitars", image: "🎸" },
  { id: 3, name: "Ernie Ball Strings", price: 450, stock: 45, category: "Accessories", image: "🧵" },
  { id: 4, name: "Boss DS-1 Distortion", price: 3200, stock: 8, category: "Pedals", image: "🎛️" },
  { id: 5, name: "Focusrite Scarlett 2i2", price: 9500, stock: 4, category: "Audio Interfaces", image: "🎙️" },
  { id: 6, name: "Tortex Picks (12-pack)", price: 250, stock: 100, category: "Accessories", image: "🎸" },
  { id: 7, name: "Hercules Guitar Stand", price: 1200, stock: 15, category: "Accessories", image: "🎸" },
  { id: 8, name: "Marshall MG15G Amp", price: 6500, stock: 6, category: "Amplifiers", image: "📻" },
];

interface CartItem {
  product: typeof mockProducts[0];
  quantity: number;
}

export const POS: React.FC = () => {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState("");

  const addToCart = (product: typeof mockProducts[0]) => {
    setCart(prev => {
      const existing = prev.find(item => item.product.id === product.id);
      if (existing) {
        return prev.map(item => 
          item.product.id === product.id 
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { product, quantity: 1 }];
    });
  };

  const updateQuantity = (id: number, delta: number) => {
    setCart(prev => prev.map(item => {
      if (item.product.id === id) {
        const newQ = item.quantity + delta;
        return newQ > 0 ? { ...item, quantity: newQ } : item;
      }
      return item;
    }));
  };

  const removeFromCart = (id: number) => {
    setCart(prev => prev.filter(item => item.product.id !== id));
  };

  const subtotal = cart.reduce((sum, item) => sum + (item.product.price * item.quantity), 0);
  const tax = subtotal * 0.12;
  const total = subtotal + tax;

  const filteredProducts = mockProducts.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="pos-container fade-in">
      {/* Left Side - Product Grid */}
      <div className="pos-products">
        <div className="pos-header">
          <h2>Point of Sale</h2>
          <div className="search-bar glass-panel">
            <Search size={20} className="text-muted" />
            <input 
              type="text" 
              placeholder="Search products by name or category..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="categories-pills">
          <button className="pill active">All</button>
          <button className="pill">Guitars</button>
          <button className="pill">Accessories</button>
          <button className="pill">Pedals</button>
          <button className="pill">Amps</button>
        </div>

        <div className="product-grid">
          {filteredProducts.map(product => (
            <div 
              key={product.id} 
              className="product-card card"
              onClick={() => addToCart(product)}
            >
              <div className="product-emoji">{product.image}</div>
              <div className="product-card-info">
                <div className="product-card-price">₱{product.price.toLocaleString()}</div>
                <div className="product-card-name">{product.name}</div>
                <div className="product-card-stock">{product.stock} in stock</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Side - Cart */}
      <div className="pos-cart glass-panel">
        <div className="cart-header">
          <h3>Current Sale</h3>
          <ShoppingCart size={20} className="text-accent" />
        </div>

        <div className="cart-items">
          {cart.length === 0 ? (
            <div className="empty-cart">
              <ShoppingCart size={40} className="text-muted mb-3" />
              <p>Cart is empty</p>
              <span className="text-muted text-sm">Add items from the left to begin</span>
            </div>
          ) : (
            cart.map(item => (
              <div key={item.product.id} className="cart-item">
                <div className="cart-item-details">
                  <div className="cart-item-name">{item.product.name}</div>
                  <div className="cart-item-price">₱{item.product.price.toLocaleString()}</div>
                </div>
                <div className="cart-item-actions">
                  <div className="qty-control">
                    <button onClick={() => updateQuantity(item.product.id, -1)}><Minus size={14} /></button>
                    <span>{item.quantity}</span>
                    <button onClick={() => updateQuantity(item.product.id, 1)}><Plus size={14} /></button>
                  </div>
                  <button className="btn-remove" onClick={() => removeFromCart(item.product.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="cart-summary">
          <div className="summary-row">
            <span>Subtotal</span>
            <span>₱{subtotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
          </div>
          <div className="summary-row">
            <span>Tax (12%)</span>
            <span>₱{tax.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
          </div>
          <div className="summary-row total-row">
            <span>Total</span>
            <span className="total-amount">₱{total.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
          </div>
        </div>

        <div className="payment-section">
          <div className="payment-methods">
            <button className="payment-btn active">
              <Banknote size={20} />
              <span>Cash</span>
            </button>
            <button className="payment-btn">
              <CreditCard size={20} />
              <span>Card</span>
            </button>
            <button className="payment-btn">
              <Smartphone size={20} />
              <span>GCash</span>
            </button>
          </div>
          <button className="btn btn-primary btn-checkout" disabled={cart.length === 0}>
            Complete Payment
          </button>
        </div>
      </div>
    </div>
  );
};
