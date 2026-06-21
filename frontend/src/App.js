import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

// Landing components
import Header from "./components/Header";
import Hero from "./components/Hero";
import Features from "./components/Features";
import HowItWorks from "./components/HowItWorks";
import Footer from "./components/Footer";

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
      <Features />
      <HowItWorks />
      <Footer />
    </div>
  );
};

import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

// Layout wrapper to conditionally render Navbar depending on whether the user is on the Landing page
function LayoutWrapper({ children }) {
  const location = useLocation();
  const userId = useAuthStore((state) => state.userId);
  const { data: user } = useUserWithSkills(userId);

  const isLanding = location.pathname === "/";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-primary-500/30 selection:text-white">
      {!isLanding && <Navbar user={user} />}
      <div className={!isLanding ? "pb-12" : ""}>
        {children}
      </div>
    </div>
  );
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
  return (
    <LayoutWrapper>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/intake" element={<Onboarding />} />
        <Route path="/weekly-plan" element={<ProtectedRoute><WeeklyPlan /></ProtectedRoute>} />
        <Route path="/roadmap" element={<ProtectedRoute><WeeklyPlan /></ProtectedRoute>} />
        <Route path="/progress-report" element={<ProtectedRoute><ProgressReport /></ProtectedRoute>} />
        <Route path="/resume" element={<ProtectedRoute><ResumePage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><CareerChat /></ProtectedRoute>} />
        <Route path="/ledger" element={<ProtectedRoute><Ledger /></ProtectedRoute>} />
        <Route path="/briefs" element={<ProtectedRoute><Briefs /></ProtectedRoute>} />
        <Route path="/pulse" element={<ProtectedRoute><Pulse /></ProtectedRoute>} />
        <Route path="/calendar" element={<ProtectedRoute><Calendar /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute><Portfolio /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
      </Routes>
    </LayoutWrapper>
  );
}

function App() {
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
