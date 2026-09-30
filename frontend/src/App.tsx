import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Layout, PublicLayout } from "./components/ui";
import { useAuth } from "./lib/auth";
import { LoginPage, SignupPage } from "./pages/AuthPages";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { MatchesPage } from "./pages/MatchesPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ProfilePage } from "./pages/ProfilePage";

// Redirect guests away from auth pages once logged in
function GuestOnly() {
  const { session } = useAuth();
  if (session) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

// Require a valid session for protected routes
function RequireAuth() {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  return <Layout />;
}

export default function App() {
  return (
    <Routes>
      {/* Public pages — home, login, signup */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
      </Route>

      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>

      {/* Authenticated app */}
      <Route element={<RequireAuth />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/matches" element={<MatchesPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
