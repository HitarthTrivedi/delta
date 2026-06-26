import React, { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { Loader2 } from "lucide-react";

// Landing components
import Header from "./components/Header";
import Hero from "./components/Hero";
import Features from "./components/Features";
import HowItWorks from "./components/HowItWorks";
import Showcase from "./components/Showcase";
import Feedback from "./components/Feedback";
import Footer from "./components/Footer";

// Public pages (separate routes, not landing sections)
import AboutPage from "./pages/AboutPage";
import CareersPage from "./pages/CareersPage";
import ContactPage from "./pages/ContactPage";
import PartnersPage from "./pages/PartnersPage";
import InvestorsPage from "./pages/InvestorsPage";
import EarlyAccessPage from "./pages/EarlyAccessPage";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import TermsOfService from "./pages/TermsOfService";

// UI Layout Components
import Navbar from "./components/ui/Navbar";

// Supplementary feature pages (with beautiful HUD styling)
import {
  Ledger,
  Briefs,
  Pulse,
  Calendar,
  Portfolio,
  Profile
} from "./pages/FeaturePages";

// Core high-fidelity custom pages
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import CareerChat from "./pages/CareerChat";
import WeeklyPlan from "./pages/WeeklyPlan";
import ProgressReport from "./pages/ProgressReport";
import ResumePage from "./pages/ResumePage";
import LoginPage from "./pages/LoginPage";

// Core connection hooks
import { useUserWithSkills } from "./hooks/useUser";
import { useAuthStore } from "./store/authStore";

// Initialize Query Client for caching
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const LandingPage = () => {
  return (
    <div style={{ background: 'var(--bg-page)' }}>
      <Header />
      <Hero />
      <Showcase />
      <HowItWorks />
      <Feedback />
      <Footer />
    </div>
  );
};

// Layout wrapper to conditionally render Navbar depending on whether the user is on the Landing or Login page
function LayoutWrapper({ children }) {
  const location = useLocation();
  const userId = useAuthStore((state) => state.userId);
  const { data: user } = useUserWithSkills(userId);

  const isLanding = location.pathname === "/";
  const isLogin = location.pathname === "/login";
  const isPublicPage = ["/about", "/careers", "/contact", "/partners", "/investors", "/early-access"].includes(location.pathname);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-primary-500/30 selection:text-white">
      {!isLanding && !isLogin && !isPublicPage && <Navbar user={user} />}
      <div className={(!isLanding && !isLogin && !isPublicPage) ? "pb-12" : ""}>
        {children}
      </div>
    </div>
  );
}

// RequireAuth component to restrict access until authenticated
function RequireAuth({ children }) {
  const userId = useAuthStore((state) => state.userId);
  const loading = useAuthStore((state) => state.loading);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: '#000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: "'Inter', sans-serif"
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <Loader2 style={{ animation: 'spin 1s linear infinite', color: '#fff' }} size={24} />
          <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.85rem' }}>Authenticating session...</span>
        </div>
      </div>
    );
  }

  if (!userId) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// Protected Route Component to restrict access until onboarding is 100% complete
function ProtectedRoute({ children }) {
  const userId = useAuthStore((state) => state.userId);
  const { data: user, isLoading } = useUserWithSkills(userId);

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: '#000',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: "'Inter', sans-serif"
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <Loader2 style={{ animation: 'spin 1s linear infinite', color: '#fff' }} size={24} />
          <span style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.85rem' }}>Loading profile status...</span>
        </div>
      </div>
    );
  }

  const isComplete = user?.onboarding_complete || (user?.onboarding_percentage && user.onboarding_percentage >= 100);

  if (!isComplete) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}

function AppContent() {
  const loading = useAuthStore((state) => state.loading);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center text-white">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <LayoutWrapper>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/careers" element={<CareersPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/partners" element={<PartnersPage />} />
        <Route path="/investors" element={<InvestorsPage />} />
        <Route path="/early-access" element={<EarlyAccessPage />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/login" element={<LoginPage />} />
        
        {/* Onboarding & Intake are protected by auth but do not require completed onboarding */}
        <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
        <Route path="/intake" element={<RequireAuth><Onboarding /></RequireAuth>} />
        
        {/* All other core app pages require both auth AND completed onboarding */}
        <Route path="/weekly-plan" element={<RequireAuth><ProtectedRoute><WeeklyPlan /></ProtectedRoute></RequireAuth>} />
        <Route path="/roadmap" element={<RequireAuth><ProtectedRoute><WeeklyPlan /></ProtectedRoute></RequireAuth>} />
        <Route path="/progress-report" element={<RequireAuth><ProtectedRoute><ProgressReport /></ProtectedRoute></RequireAuth>} />
        <Route path="/resume" element={<RequireAuth><ProtectedRoute><ResumePage /></ProtectedRoute></RequireAuth>} />
        <Route path="/dashboard" element={<RequireAuth><ProtectedRoute><Dashboard /></ProtectedRoute></RequireAuth>} />
        <Route path="/chat" element={<Navigate to="/roadmap" replace />} />
        <Route path="/ledger" element={<RequireAuth><ProtectedRoute><Ledger /></ProtectedRoute></RequireAuth>} />
        <Route path="/briefs" element={<RequireAuth><ProtectedRoute><Briefs /></ProtectedRoute></RequireAuth>} />
        <Route path="/pulse" element={<RequireAuth><ProtectedRoute><Pulse /></ProtectedRoute></RequireAuth>} />
        <Route path="/calendar" element={<RequireAuth><ProtectedRoute><Calendar /></ProtectedRoute></RequireAuth>} />
        <Route path="/portfolio" element={<RequireAuth><ProtectedRoute><Portfolio /></ProtectedRoute></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProtectedRoute><Profile /></ProtectedRoute></RequireAuth>} />
      </Routes>
    </LayoutWrapper>
  );
}

function App() {
  const initializeAuth = useAuthStore((state) => state.initializeAuth);

  useEffect(() => {
    // Sync initial session and listen to changes
    initializeAuth();
  }, [initializeAuth]);

  return (
    <QueryClientProvider client={queryClient}>
      <div className="App">
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
        <Toaster theme="dark" position="bottom-right" richColors />
      </div>
    </QueryClientProvider>
  );
}

export default App;
