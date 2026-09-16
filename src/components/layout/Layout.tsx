import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import './Layout.css';

export const Layout: React.FC = () => {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <header className="top-header glass-panel">
          <div className="header-search">
            <input type="text" placeholder="Search anywhere..." className="search-input" />
          </div>
          <div className="header-actions">
            <div className="status-indicator">
              <span className="pulse-dot"></span>
              <span className="status-text">System Online</span>
            </div>
          </div>
        </header>
        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
