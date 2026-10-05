import { useState, useEffect } from "react";
import { Search } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Users() {
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const res = await fetch(`${API_URL}/patients`);
        if (!res.ok) throw new Error("Failed to fetch patients");
        const data = await res.json();
        setPatients(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchPatients();
  }, []);

  const filteredPatients = patients.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) || 
    p.phone.includes(search)
  );

  if (loading) return <div>Loading User Dashboard...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <div className="header-row" style={{ marginBottom: "2rem" }}>
        <div>
          <h1>Patient Directory</h1>
          <p className="subtitle">Manage patient records and communication preferences.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "2rem" }}>
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          <Search size={20} style={{ position: "absolute", left: "1rem", color: "#9ca3af" }} />
          <input 
            type="text" 
            placeholder="Search patients by name or phone number..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ 
              width: "100%", 
              padding: "0.75rem 1rem 0.75rem 3rem", 
              borderRadius: "0.5rem", 
              border: "1px solid #d1d5db",
              fontSize: "1rem",
              outline: "none"
            }}
          />
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Full Name</th>
                <th>Phone Number</th>
                <th>Date of Birth</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredPatients.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", color: "#6b7280" }}>
                    No patients found
                  </td>
                </tr>
              ) : (
                filteredPatients.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 500, color: "#4f46e5" }}>{p.id}</td>
                    <td style={{ fontWeight: 500, color: "#111827" }}>{p.name}</td>
                    <td>{p.phone}</td>
                    <td>{p.dob}</td>
                    <td><span className="pill grey">Active</span></td>
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
