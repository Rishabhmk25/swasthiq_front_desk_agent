import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function HandoffQueue() {
  const [stats, setStats] = useState(null);
  const [handoffs, setHandoffs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    try {
      const [statsRes, handoffsRes] = await Promise.all([
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/handoffs?status=open`)
      ]);
      
      if (!statsRes.ok || !handoffsRes.ok) throw new Error("Failed to fetch data");
      
      const statsData = await statsRes.json();
      const handoffsData = await handoffsRes.json();
      
      setStats(statsData);
      setHandoffs(handoffsData);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleResolve = async (id) => {
    try {
      const res = await fetch(`${API_URL}/handoffs/${id}/resolve`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to resolve");
      await fetchData(); // refresh data
    } catch (err) {
      alert(err.message);
    }
  };

  const getPillClass = (reason) => {
    if (reason === "clinical_urgent" || reason === "CLINICAL") return "pill red";
    if (reason === "medical_advice") return "pill red"; // red-ish
    if (reason === "not_authorised" || reason === "ambiguous_patient") return "pill amber";
    return "pill grey";
  };
  
  const formatReason = (reason) => {
    if (reason === "clinical_urgent") return "CLINICAL";
    return reason.replace(/_/g, ' ').toUpperCase();
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <div className="header-row">
        <div>
          <h1>Handoff Queue</h1>
          <p className="subtitle">Sunrise Clinic, Dehradun - conversations the agent escalated</p>
        </div>
        <div className="pill grey" style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
          {stats?.escalated_open || 0} OPEN
        </div>
      </div>

      <div className="stat-grid">
        <div className="card stat-card">
          <span className="stat-title">Conversations</span>
          <span className="stat-value">{stats?.conversations || 0}</span>
          <span className="stat-sub">today</span>
        </div>
        <div className="card stat-card">
          <span className="stat-title">Completed by agent</span>
          <span className="stat-value">{stats?.completed_by_agent || 0}</span>
          <span className="stat-sub">{stats?.completed_pct || 0}%</span>
        </div>
        <div className="card stat-card">
          <span className="stat-title">Escalated</span>
          <span className="stat-value">{stats?.escalated || 0}</span>
          <span className="stat-sub blue">{stats?.escalated_open || 0} still open</span>
        </div>
        <div className="card stat-card">
          <span className="stat-title">Urgent</span>
          <span className="stat-value">{stats?.urgent_unresolved || 0}</span>
          <span className="stat-sub">clinical, unresolved</span>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Conversation</th>
                <th>Caller Said</th>
                <th>Reason</th>
                <th>Time</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {handoffs.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", color: "#6b7280" }}>
                    No open handoffs
                  </td>
                </tr>
              ) : (
                handoffs.map((h) => (
                  <tr key={h.conversation_id}>
                    <td>
                      <Link to={`/conversations/${h.conversation_id}`} style={{ color: "#2563eb", fontWeight: 500 }}>
                        {h.conversation_id}
                      </Link>
                    </td>
                    <td><strong>"{h.caller_said}"</strong></td>
                    <td>
                      <span className={getPillClass(h.reason)}>
                        {formatReason(h.reason)}
                      </span>
                    </td>
                    <td>{h.created_at}</td>
                    <td>
                      <button 
                        className={`btn ${h.reason === 'clinical_urgent' ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => handleResolve(h.conversation_id)}
                      >
                        Resolve
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
