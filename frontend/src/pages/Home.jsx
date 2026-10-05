import { useState, useEffect } from "react";
import { Users, UserPlus, Calendar, Activity } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Home() {
  const [data, setData] = useState({ patients: [], doctors: [], appointments: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [patientsRes, doctorsRes, appointmentsRes] = await Promise.all([
          fetch(`${API_URL}/patients`),
          fetch(`${API_URL}/doctors`),
          fetch(`${API_URL}/appointments`)
        ]);

        if (!patientsRes.ok || !doctorsRes.ok || !appointmentsRes.ok) {
          throw new Error("Failed to fetch dashboard data");
        }

        const patients = await patientsRes.json();
        const doctors = await doctorsRes.json();
        const appointments = await appointmentsRes.json();

        setData({ patients, doctors, appointments });
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div>Loading Admin Dashboard...</div>;
  if (error) return <div>Error: {error}</div>;

  const getPatientName = (id) => data.patients.find(p => p.id === id)?.name || id;
  const getDoctorName = (id) => data.doctors.find(d => d.id === id)?.name || id;

  return (
    <div>
      <div className="header-row" style={{ marginBottom: "2rem" }}>
        <div>
          <h1>Admin Dashboard</h1>
          <p className="subtitle">High-level overview of clinic performance and daily volumes.</p>
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: "2rem" }}>
        <div className="card stat-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: '#e0e7ff', borderRadius: '50%', color: '#4f46e5' }}>
            <Users size={32} />
          </div>
          <div>
            <span className="stat-value" style={{ fontSize: '1.8rem', display: 'block' }}>{data.patients.length}</span>
            <span className="stat-title" style={{ marginTop: 0 }}>Total Patients</span>
          </div>
        </div>
        
        <div className="card stat-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: '#dcfce7', borderRadius: '50%', color: '#16a34a' }}>
            <Activity size={32} />
          </div>
          <div>
            <span className="stat-value" style={{ fontSize: '1.8rem', display: 'block' }}>{data.doctors.length}</span>
            <span className="stat-title" style={{ marginTop: 0 }}>Active Doctors</span>
          </div>
        </div>

        <div className="card stat-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ padding: '1rem', backgroundColor: '#fef3c7', borderRadius: '50%', color: '#d97706' }}>
            <Calendar size={32} />
          </div>
          <div>
            <span className="stat-value" style={{ fontSize: '1.8rem', display: 'block' }}>{data.appointments.length}</span>
            <span className="stat-title" style={{ marginTop: 0 }}>Total Appointments</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: "1.2rem", marginBottom: "1.5rem", color: "#111827" }}>Upcoming Appointments</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Appointment ID</th>
                <th>Patient</th>
                <th>Doctor</th>
                <th>Date</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {data.appointments.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", color: "#6b7280" }}>
                    No appointments scheduled
                  </td>
                </tr>
              ) : (
                data.appointments.map((apt) => (
                  <tr key={apt.id}>
                    <td style={{ fontWeight: 500, color: "#374151" }}>{apt.id}</td>
                    <td>{getPatientName(apt.patient_id)}</td>
                    <td>{getDoctorName(apt.doctor_id)}</td>
                    <td>{apt.date}</td>
                    <td><span className="pill green" style={{ padding: "0.2rem 0.6rem" }}>{apt.start}</span></td>
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
