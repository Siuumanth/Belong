import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Layout } from "./components/ui";
import { useAuth } from "./lib/auth";
import { LoginPage, SignupPage } from "./pages/AuthPages";
import { MatchesPage } from "./pages/MatchesPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ProfilePage } from "./pages/ProfilePage";

function GuestOnly() {
  const { session } = useAuth();
  if (session) return <Navigate to="/profile" replace />;
  return <Outlet />;
}

function RequireAuth() {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  return <Layout />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/matches" element={<MatchesPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/profile" replace />} />
    </Routes>
  );
}
