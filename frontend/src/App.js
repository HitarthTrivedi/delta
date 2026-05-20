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
import Benefits from "./components/Benefits";
import Testimonials from "./components/Testimonials";
import Pricing from "./components/Pricing";
import FAQ from "./components/FAQ";
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
      <Benefits />
      <Testimonials />
      <Pricing />
      <FAQ />
      <Footer />
    </div>
  );
};

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

function AppContent() {
  return (
    <LayoutWrapper>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/ledger" element={<Ledger />} />
        <Route path="/briefs" element={<Briefs />} />
        <Route path="/pulse" element={<Pulse />} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/profile" element={<Profile />} />
        
        {/* Placeholder paths that Gemini will override */}
        <Route path="/dashboard" element={
          <div className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-slate-400 font-mono text-center">
            <h1 className="text-3xl font-black text-white tracking-widest uppercase mb-4">Dashboard Loading...</h1>
            <p className="text-sm">Awaiting Gemini frontend component injection (DashboardConnected.jsx / Dashboard.jsx)</p>
          </div>
        } />
        <Route path="/chat" element={
          <div className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-slate-400 font-mono text-center">
            <h1 className="text-3xl font-black text-white tracking-widest uppercase mb-4">Career AI Core</h1>
            <p className="text-sm">Awaiting Gemini frontend component injection (CareerChat.jsx)</p>
          </div>
        } />
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
