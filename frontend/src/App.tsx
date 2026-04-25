import { useEffect } from "react";
import {
  BrowserRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { Toaster } from "sonner";

import { ChatScreen } from "@/screens/ChatScreen";
import { HomeScreen } from "@/screens/HomeScreen";
import { VoiceScreen } from "@/screens/VoiceScreen";
import { deriveModeFromPath, useMode } from "@/store/mode";

function ModeSyncer() {
  const location = useLocation();
  const setMode = useMode((s) => s.setMode);
  useEffect(() => {
    setMode(deriveModeFromPath(location.pathname));
  }, [location.pathname, setMode]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <ModeSyncer />
      <Routes>
        <Route path="/" element={<HomeScreen />} />
        <Route path="/voice" element={<VoiceScreen />} />
        <Route path="/chat" element={<ChatScreen />} />
      </Routes>
      <Toaster position="bottom-right" theme="dark" richColors />
    </BrowserRouter>
  );
}
