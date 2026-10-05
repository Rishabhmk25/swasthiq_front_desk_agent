import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HandoffQueue from "./pages/HandoffQueue";
import ConversationDetail from "./pages/ConversationDetail";
import Home from "./pages/Home";
import CalendarView from "./pages/CalendarView";
import UsersList from "./pages/UsersList";
import SettingsPage from "./pages/Settings";
import { Settings } from "lucide-react";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HandoffQueue />} />
          <Route path="conversations/:id" element={<ConversationDetail />} />
          <Route path="home" element={<Home />} />
          <Route path="calendar" element={<CalendarView />} />
          <Route path="users" element={<UsersList />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
