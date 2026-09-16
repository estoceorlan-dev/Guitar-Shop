import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MonitorPlay, 
  Package, 
  ArchiveRestore,
  ShoppingBag,
  Users,
  Settings,
  Guitar
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/pos', icon: MonitorPlay, label: 'Point of Sale' },
  { path: '/products', icon: Guitar, label: 'Products' },
  { path: '/inventory', icon: Package, label: 'Inventory' },
  { path: '/sales', icon: ShoppingBag, label: 'Sales History' },
  { path: '/customers', icon: Users, label: 'Customers' },
  { path: '/returns', icon: ArchiveRestore, label: 'Returns' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header">
        <div className="logo-container">
          <Guitar className="logo-icon" size={28} />
          <h1 className="logo-text">Roel's<br/><span>Guitar Shop</span></h1>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path} 
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <item.icon className="nav-icon" size={20} />
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="avatar">A</div>
          <div className="user-info">
            <span className="user-name">Admin User</span>
            <span className="user-role">Administrator</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
