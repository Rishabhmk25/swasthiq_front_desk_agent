import { Outlet, Link, useLocation } from "react-router-dom";
import { Home, Users, Inbox, Calendar, Settings } from "lucide-react";

export default function Layout() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  
  return (
    <div className="app-container">
      <aside className="sidebar">
        <Link to="/home" className={`sidebar-icon ${location.pathname === "/home" ? "active" : ""}`}>
          <Home size={20} />
        </Link>
        <Link to="/users" className={`sidebar-icon ${location.pathname === "/users" ? "active" : ""}`}>
          <Users size={20} />
        </Link>
        <Link to="/" className={`sidebar-icon ${isHome || location.pathname.startsWith("/conversations") ? "active" : ""}`}>
          <Inbox size={20} />
        </Link>
        <Link to="/calendar" className={`sidebar-icon ${location.pathname === "/calendar" ? "active" : ""}`}>
          <Calendar size={20} />
        </Link>
        <Link to="/settings" className={`sidebar-icon ${location.pathname === "/settings" ? "active" : ""}`}>
          <Settings size={20} />
        </Link>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
