import React, { useEffect, Suspense, lazy } from "react";
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
import SectionRail from "./components/SectionRail";

// UI Layout Components (eager — always rendered)
import Navbar from "./components/ui/Navbar";

// Route pages are code-split with React.lazy so they ship as separate chunks
// and aren't downloaded until visited (keeps the initial/landing bundle small).
const AboutPage = lazy(() => import("./pages/AboutPage"));
const CareersPage = lazy(() => import("./pages/CareersPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const PartnersPage = lazy(() => import("./pages/PartnersPage"));
const InvestorsPage = lazy(() => import("./pages/InvestorsPage"));
const EarlyAccessPage = lazy(() => import("./pages/EarlyAccessPage"));
const PrivacyPolicy = lazy(() => import("./pages/PrivacyPolicy"));
const TermsOfService = lazy(() => import("./pages/TermsOfService"));

// Supplementary feature pages (named exports → map to default for lazy)
const Ledger = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Ledger })));
const Briefs = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Briefs })));
const Pulse = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Pulse })));
const Calendar = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Calendar })));
const Portfolio = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Portfolio })));
const Profile = lazy(() => import("./pages/FeaturePages").then((m) => ({ default: m.Profile })));

// Core high-fidelity custom pages
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const WeeklyPlan = lazy(() => import("./pages/WeeklyPlan"));
const ProgressReport = lazy(() => import("./pages/ProgressReport"));
const ResumePage = lazy(() => import("./pages/ResumePage"));
const TrophyCabinet = lazy(() => import("./pages/TrophyCabinet"));
const Opportunities = lazy(() => import("./pages/Opportunities"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

// Core connection hooks
import { useUserWithSkills } from "./hooks/useUser";
import { useAuthStore } from "./store/authStore";

// Initialize Query Client for caching.
// Global staleTime keeps data fresh across remounts/navigation so pages don't
// refetch the same (slow) endpoints on every mount; gcTime keeps it in memory.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 60000,
      gcTime: 5 * 60 * 1000,
    },
  },
});

const LandingPage = () => {
  return (
    <div style={{ background: 'var(--bg-page)' }}>
      <Header />
      <SectionRail />
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
    <div className="min-h-screen bg-bone text-ink selection:bg-primary-500/30 selection:text-ink">
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
        background: 'var(--bone)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: "'Inter', sans-serif"
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <Loader2 style={{ animation: 'spin 1s linear infinite', color: '#fff' }} size={24} />
          <span style={{ color: 'var(--ink-soft)', fontSize: '0.85rem' }}>Authenticating session...</span>
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
        background: 'var(--bone)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: "'Inter', sans-serif"
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <Loader2 style={{ animation: 'spin 1s linear infinite', color: '#fff' }} size={24} />
          <span style={{ color: 'var(--ink-soft)', fontSize: '0.85rem' }}>Loading profile status...</span>
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
      <div className="min-h-screen bg-bone flex flex-col items-center justify-center text-ink">
        <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <LayoutWrapper>
      <Suspense fallback={
        <div className="min-h-screen bg-bone flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
        </div>
      }>
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
        <Route path="/achievements" element={<RequireAuth><ProtectedRoute><TrophyCabinet /></ProtectedRoute></RequireAuth>} />
        <Route path="/opportunities" element={<RequireAuth><ProtectedRoute><Opportunities /></ProtectedRoute></RequireAuth>} />
        <Route path="/dashboard" element={<RequireAuth><ProtectedRoute><Dashboard /></ProtectedRoute></RequireAuth>} />
        <Route path="/chat" element={<Navigate to="/roadmap" replace />} />
        <Route path="/ledger" element={<RequireAuth><ProtectedRoute><Ledger /></ProtectedRoute></RequireAuth>} />
        <Route path="/briefs" element={<RequireAuth><ProtectedRoute><Briefs /></ProtectedRoute></RequireAuth>} />
        <Route path="/pulse" element={<RequireAuth><ProtectedRoute><Pulse /></ProtectedRoute></RequireAuth>} />
        <Route path="/calendar" element={<RequireAuth><ProtectedRoute><Calendar /></ProtectedRoute></RequireAuth>} />
        <Route path="/portfolio" element={<RequireAuth><ProtectedRoute><Portfolio /></ProtectedRoute></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProtectedRoute><Profile /></ProtectedRoute></RequireAuth>} />
      </Routes>
      </Suspense>
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
