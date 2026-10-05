import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HandoffQueue from "./pages/HandoffQueue";
import ConversationDetail from "./pages/ConversationDetail";
import { Settings } from "lucide-react";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HandoffQueue />} />
          <Route path="conversations/:id" element={<ConversationDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
