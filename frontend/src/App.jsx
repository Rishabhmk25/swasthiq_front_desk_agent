import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HandoffQueue from "./pages/HandoffQueue";
import ConversationDetail from "./pages/ConversationDetail";
import PlaceholderPage from "./pages/PlaceholderPage";
import Home from "./pages/Home";
import Users from "./pages/Users";
import Calendar from "./pages/Calendar";
import { Settings } from "lucide-react";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HandoffQueue />} />
          <Route path="conversations/:id" element={<ConversationDetail />} />
          <Route path="home" element={<Home />} />
          <Route path="users" element={<Users />} />
          <Route path="calendar" element={<Calendar />} />
          <Route path="settings" element={<PlaceholderPage title="Agent Configuration" description="Tune LLM prompt templates, adjust safety thresholds, and manage API keys." icon={<Settings size={64} />} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
