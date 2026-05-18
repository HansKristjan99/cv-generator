import { Navigate, Route, Routes } from "react-router";

import { AppShell } from "./components/appShell";

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />} />
      <Route path="/app" element={<AppShell initialTab="cv" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
