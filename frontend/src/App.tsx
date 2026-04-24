import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ChatScreen } from "@/screens/ChatScreen";
import { HomeScreen } from "@/screens/HomeScreen";
import { VoiceScreen } from "@/screens/VoiceScreen";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomeScreen />} />
        <Route path="/voice" element={<VoiceScreen />} />
        <Route path="/chat" element={<ChatScreen />} />
      </Routes>
    </BrowserRouter>
  );
}
