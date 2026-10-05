import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ConversationDetail() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await fetch(`${API_URL}/conversations/${id}`);
        if (!res.ok) throw new Error("Failed to fetch conversation");
        const json = await res.json();
        setData(json);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>Not found</div>;

  const getStatusBadge = () => {
    const st = data.outcome.terminal_state;
    const esc = data.outcome.escalation_reason;
    if (st === "escalated") {
      const isUrgent = esc === "clinical_urgent";
      return (
        <div className={`pill ${isUrgent ? "red" : "amber"}`} style={{ fontSize: "1rem", padding: "0.5rem 1rem" }}>
          ESCALATED - {esc === "clinical_urgent" ? "CLINICAL" : esc.toUpperCase()}
        </div>
      );
    }
    if (st === "booked" || st === "rescheduled") {
      return <div className="pill green" style={{ fontSize: "1rem", padding: "0.5rem 1rem" }}>{st.toUpperCase()}</div>;
    }
    return <div className="pill grey" style={{ fontSize: "1rem", padding: "0.5rem 1rem" }}>{st.toUpperCase()}</div>;
  };

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <Link to="/" style={{ display: "inline-flex", alignItems: "center", color: "#6b7280", fontSize: "0.875rem", fontWeight: 500 }}>
          <ArrowLeft size={16} style={{ marginRight: "0.5rem" }} /> Back to queue
        </Link>
      </div>

      <div className="header-row">
        <div>
          <h1>Conversation {id}</h1>
          <p className="subtitle">{data.header}</p>
        </div>
        <div>
          {getStatusBadge()}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "1.5rem" }}>Transcript and tool calls</h2>
          
          {data.events.map((ev, i) => {
            if (ev.kind === "caller" || ev.kind === "agent") {
              return (
                <div key={i} className="transcript-row">
                  <div className="transcript-label">{ev.kind}</div>
                  <div className="transcript-bubble">
                    {ev.text}
                  </div>
                </div>
              );
            }
            if (ev.kind === "tool") {
              const isErr = ev.tool_result_summary?.includes("Error") || ev.tool_result_summary?.includes("failed");
              // Parse tool_args_json nicely if possible
              let displayArgs = ev.tool_args_json;
              try {
                const p = JSON.parse(ev.tool_args_json);
                displayArgs = JSON.stringify(p, null, 2);
              } catch (e) {}

              // Format tool_result_summary nicely if it contains "slots: "
              let displaySummary = ev.tool_result_summary;
              if (displaySummary && displaySummary.includes("slots: ")) {
                const parts = displaySummary.split("slots: ");
                displaySummary = parts[0] + "slots: [" + parts[1] + "]";
              }
              
              return (
                <div key={i} className="transcript-row">
                  <div className="transcript-label">TOOL</div>
                  <div className={`transcript-tool ${isErr ? "error" : ""}`}>
                    <div><strong>{ev.tool_name}</strong></div>
                    <pre style={{ fontSize: "0.75rem", margin: "0.25rem 0", background: "rgba(0,0,0,0.05)", padding: "0.5rem" }}>
                      {displayArgs}
                    </pre>
                    <div style={{ marginTop: "0.5rem", color: isErr ? "#991b1b" : "#4b5563" }}>
                      &rarr; <strong>{displaySummary}</strong>
                    </div>
                  </div>
                </div>
              );
            }
            return null;
          })}

          {data.banner && (
            <div className="banner-red" style={{ marginTop: "1.5rem" }}>
              {data.banner}
            </div>
          )}
        </div>

        <div>
          <div className="card">
            <h2 style={{ fontSize: "1rem", marginBottom: "1.5rem" }}>Outcome</h2>
            <div className="outcome-row">
              <span className="outcome-label">terminal_state</span>
              <span>{data.outcome.terminal_state}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">escalation_reason</span>
              <span>{data.outcome.escalation_reason || "null"}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">patient_id</span>
              <span>{data.outcome.patient_id || "null"}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">appointment_id</span>
              <span>{data.outcome.appointment_id || "null"}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">tool_calls</span>
              <span>{data.outcome.tool_calls}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">turns</span>
              <span>{data.outcome.turns}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">tokens</span>
              <span>{data.outcome.tokens}</span>
            </div>
            <div className="outcome-row">
              <span className="outcome-label">latency</span>
              <span>{(data.outcome.latency_ms / 1000).toFixed(1)}s</span>
            </div>

            <div style={{ marginTop: "2rem" }}>
              <h3 style={{ fontSize: "0.75rem", color: "#6b7280", textTransform: "uppercase", marginBottom: "0.5rem" }}>Determinism</h3>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.875rem", color: "#374151" }}>
                  Same terminal state across {data.determinism.runs} runs.
                </span>
                <span className={`pill ${data.determinism.stable ? "green" : "red"}`}>
                  {data.determinism.stable ? "STABLE" : "UNSTABLE"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
