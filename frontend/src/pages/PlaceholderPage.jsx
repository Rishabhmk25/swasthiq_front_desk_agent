export default function PlaceholderPage({ title, description, icon }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center', alignItems: 'center', color: '#6b7280' }}>
      <div style={{ marginBottom: '1.5rem', opacity: 0.5 }}>
        {icon}
      </div>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: '#111827' }}>{title}</h1>
      <p style={{ fontSize: '1.1rem', maxWidth: '400px', textAlign: 'center', lineHeight: '1.5' }}>
        {description}
      </p>
      
      <div style={{ marginTop: '3rem', padding: '1.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.5rem', border: '1px dashed #d1d5db', width: '100%', maxWidth: '500px' }}>
        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Production Status</h3>
        <p style={{ fontSize: '0.875rem' }}>This module is currently disabled pending the Phase 2 backend release. Data sources for this view have not yet been migrated to the new PostgreSQL architecture.</p>
      </div>
    </div>
  );
}
