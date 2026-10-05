import React from 'react';

export default function Home() {
  return (
    <div>
      <div className="header-row">
        <div>
          <h1>Dashboard Overview</h1>
          <p className="subtitle">Welcome to SwasthiQ Clinic Management System.</p>
        </div>
      </div>
      
      <div className="stat-grid">
        <div className="card stat-card">
          <span className="stat-title">Total Appointments Today</span>
          <span className="stat-value">24</span>
        </div>
        <div className="card stat-card">
          <span className="stat-title">AI Handoffs Pending</span>
          <span className="stat-value" style={{ color: '#dc2626' }}>5</span>
        </div>
        <div className="card stat-card">
          <span className="stat-title">Active Doctors</span>
          <span className="stat-value">3</span>
        </div>
      </div>
    </div>
  );
}
