import { useState, useEffect } from "react";
import { Calendar as CalendarIcon, Clock } from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const START_HOUR = 8;
const END_HOUR = 18;
const HOURS = Array.from({ length: END_HOUR - START_HOUR + 1 }, (_, i) => i + START_HOUR);
const HOUR_HEIGHT = 55; // height of one hour block in pixels

const DOCTOR_COLORS = [
  { bg: "#dbeafe", text: "#1e40af", border: "#bfdbfe", hover: "#eff6ff" },
  { bg: "#dcfce7", text: "#166534", border: "#bbf7d0", hover: "#f0fdf4" },
  { bg: "#fef3c7", text: "#92400e", border: "#fde68a", hover: "#fffbeb" },
  { bg: "#f3e8ff", text: "#6b21a8", border: "#e9d5ff", hover: "#faf5ff" },
  { bg: "#ffe4e6", text: "#9f1239", border: "#fecdd3", hover: "#fff1f2" },
  { bg: "#e0e7ff", text: "#3730a3", border: "#c7d2fe", hover: "#eef2ff" }
];

export default function Calendar() {
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        const res = await fetch(`${API_URL}/doctors`);
        if (!res.ok) throw new Error("Failed to fetch doctors");
        const data = await res.json();
        setDoctors(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDoctors();
  }, []);

  if (loading) return <div>Loading Schedules...</div>;
  if (error) return <div>Error: {error}</div>;

  const formatHour = (h) => {
    if (h === 12) return "12 PM";
    return h > 12 ? `${h - 12} PM` : `${h} AM`;
  };

  // Convert HH:MM to fractional hours relative to START_HOUR
  const timeToOffset = (timeStr) => {
    const [h, m] = timeStr.split(":").map(Number);
    return (h - START_HOUR) + (m / 60);
  };

  // Generate all event blocks
  const getEventsForDay = (day) => {
    const events = [];
    doctors.forEach((doc, docIndex) => {
      if (!doc.windows) return;
      doc.windows.forEach(win => {
        if (win.day === day) {
          const startOffset = timeToOffset(win.start);
          const endOffset = timeToOffset(win.end);
          if (endOffset > startOffset) {
            events.push({
              id: `${doc.id}-${win.start}`,
              doctorId: doc.id,
              name: doc.name,
              specialty: doc.specialty,
              start: win.start,
              end: win.end,
              top: startOffset * HOUR_HEIGHT,
              height: (endOffset - startOffset) * HOUR_HEIGHT,
              color: DOCTOR_COLORS[docIndex % DOCTOR_COLORS.length]
            });
          }
        }
      });
    });
    
    // Sort events by start time to handle overlapping visually (simple stacking)
    return events.sort((a, b) => a.top - b.top);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="header-row" style={{ marginBottom: "1.5rem", flexShrink: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <div style={{ padding: '0.75rem', backgroundColor: '#e0e7ff', borderRadius: '12px' }}>
              <CalendarIcon size={24} color="#3730a3" />
            </div>
            <h1 style={{ marginBottom: 0, fontSize: "1.75rem" }}>Master Schedule</h1>
          </div>
          <p className="subtitle" style={{ marginBottom: 0, marginTop: "0.5rem" }}>Weekly practitioner schedule overview.</p>
        </div>
      </div>

      <div className="card" style={{ flex: 1, padding: 0, overflow: "hidden", display: "flex", flexDirection: "column", backgroundColor: "white" }}>
        
        {/* Header: Days of the week */}
        <div style={{ 
          display: "grid", 
          gridTemplateColumns: "80px repeat(6, 1fr)",
          borderBottom: "1px solid #e5e7eb",
          backgroundColor: "#f9fafb",
          borderTopLeftRadius: "12px",
          borderTopRightRadius: "12px"
        }}>
          <div style={{ borderRight: "1px solid #e5e7eb" }}></div>
          {DAYS.map(day => (
            <div key={day} style={{ 
              textAlign: "center", 
              padding: "1rem 0",
              fontWeight: 600, 
              color: "#374151",
              borderRight: day !== "Sat" ? "1px solid #e5e7eb" : "none"
            }}>
              {day}
            </div>
          ))}
        </div>
        
        {/* Grid Body */}
        <div style={{ flex: 1, overflowY: "auto", position: "relative" }}>
          <div style={{ display: "grid", gridTemplateColumns: "80px repeat(6, 1fr)" }}>
            
            {/* Column 1: Time Labels */}
            <div style={{ borderRight: "1px solid #e5e7eb", backgroundColor: "#f9fafb", position: "relative" }}>
              {/* Spacer so the first label isn't cut off */}
              <div style={{ height: "12px" }}></div>
              {HOURS.map((hour, i) => (
                <div key={hour} style={{ 
                  height: `${HOUR_HEIGHT}px`, 
                  position: "relative"
                }}>
                  <span style={{ 
                    position: "absolute", 
                    top: "-10px", 
                    right: "12px", 
                    fontSize: "0.75rem", 
                    fontWeight: 500, 
                    color: "#6b7280",
                    backgroundColor: "#f9fafb",
                    padding: "0 4px"
                  }}>
                    {formatHour(hour)}
                  </span>
                </div>
              ))}
            </div>
            
            {/* Columns 2-7: Day Columns with Absolute Events */}
            {DAYS.map((day, dayIndex) => {
              const events = getEventsForDay(day);
              
              return (
                <div key={day} style={{ 
                  position: "relative", 
                  borderRight: dayIndex < 5 ? "1px solid #e5e7eb" : "none",
                  minHeight: `${HOURS.length * HOUR_HEIGHT + 12}px`
                }}>
                  {/* Background grid lines */}
                  {HOURS.map((hour, i) => (
                    <div key={`bg-${hour}`} style={{ 
                      height: `${HOUR_HEIGHT}px`, 
                      borderBottom: i < HOURS.length - 1 ? "1px solid #f3f4f6" : "none",
                      width: "100%",
                      position: "absolute",
                      top: `${i * HOUR_HEIGHT + 12}px`,
                      pointerEvents: "none"
                    }} />
                  ))}
                  
                  {/* Event Blocks */}
                  {events.map((event, i) => {
                    const overlaps = events.filter(e => e !== event && e.top < event.top + event.height && e.top + e.height > event.top);
                    const overlapIndex = overlaps.filter(e => e.top < event.top || (e.top === event.top && e.id < event.id)).length;
                    
                    const leftOffset = 4 + (overlapIndex * 15);
                    const width = `calc(100% - ${8 + (overlapIndex * 15)}px)`;
                    
                    return (
                      <div key={event.id} style={{
                        position: "absolute",
                        top: `${event.top + 12}px`,
                        left: `${leftOffset}px`,
                        width: width,
                        height: `${event.height - 2}px`, // -2 for slight gap
                        backgroundColor: event.color.bg,
                        border: `1px solid ${event.color.border}`,
                        borderLeft: `4px solid ${event.color.text}`,
                        borderRadius: "6px",
                        padding: "0.5rem",
                        overflow: "hidden",
                        zIndex: 10 + overlapIndex,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
                        cursor: "pointer",
                        transition: "transform 0.2s, box-shadow 0.2s"
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = "translateY(-2px)";
                        e.currentTarget.style.boxShadow = "0 4px 6px rgba(0,0,0,0.1)";
                        e.currentTarget.style.zIndex = 50;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "none";
                        e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.1)";
                        e.currentTarget.style.zIndex = 10 + overlapIndex;
                      }}
                      >
                        <div style={{ fontWeight: 600, color: event.color.text, fontSize: "0.875rem", marginBottom: "0.25rem", whiteSpace: "nowrap" }}>
                          {event.name}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: event.color.text, opacity: 0.8, fontSize: "0.75rem" }}>
                          <Clock size={12} />
                          {event.start} - {event.end}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
