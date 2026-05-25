import { Navigate, Route, Routes } from "react-router";

import { AppShell } from "./components/appShell";

function App() {
  return (
    <Routes>
      <Route path="/app" element={<AppShell initialTab="cv" />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

export default App;
