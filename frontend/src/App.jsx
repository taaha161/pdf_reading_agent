import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Analytics } from "@vercel/analytics/react";
import { setApiAuthToken } from "./api/client";
import { useAuth } from "./contexts/AuthContext";
import Landing from "./pages/Landing";
import ScannerPage from "./pages/ScannerPage";
import Dashboard from "./pages/Dashboard";
import AuthPage from "./pages/AuthPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import AccountSettingsPage from "./pages/AccountSettingsPage";
import PrivacyPolicyPage from "./pages/PrivacyPolicyPage";
import TermsOfServicePage from "./pages/TermsOfServicePage";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import PageMeta from "./components/PageMeta";

function AppContent() {
  const { accessToken } = useAuth();
  useEffect(() => {
    setApiAuthToken(() => accessToken ?? null);
  }, [accessToken]);

  return (
    <>
      <PageMeta />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="/forgot-password" element={<AuthPage mode="forgot" />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
        <Route path="/terms-of-service" element={<TermsOfServicePage />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><AccountSettingsPage /></ProtectedRoute>} />
        <Route path="/scanner" element={<ScannerPage />} />
        <Route path="/scanner/:jobId" element={<ScannerPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Analytics />
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

export default App;
