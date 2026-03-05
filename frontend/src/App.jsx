import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./pages/Landing";
import ScannerPage from "./pages/ScannerPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/scanner" element={<ScannerPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
