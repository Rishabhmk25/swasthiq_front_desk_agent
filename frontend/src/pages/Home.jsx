import React from 'react';

export default function Home() {
  return (
    <div className="page-container" style={{ padding: '2rem' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '1rem' }}>Dashboard Overview</h1>
      <p style={{ color: '#6b7280' }}>Welcome to SwasthiQ Clinic Management System.</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginTop: '2rem' }}>
        <div style={{ padding: '1.5rem', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '0.5rem' }}>Total Appointments Today</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold' }}>24</p>
        </div>
        <div style={{ padding: '1.5rem', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '0.5rem' }}>AI Handoffs Pending</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#ef4444' }}>5</p>
        </div>
        <div style={{ padding: '1.5rem', backgroundColor: '#fff', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '0.5rem' }}>Active Doctors</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold' }}>3</p>
        </div>
      </div>
    </div>
  );
}
