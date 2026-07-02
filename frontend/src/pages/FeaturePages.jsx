import React from 'react';
import { motion } from 'framer-motion';
import GlassPanel from '../components/ui/GlassPanel';
import { BookOpen, FileText, TrendingUp, Calendar as CalendarIcon, FolderOpen, User, Zap, Lock } from 'lucide-react';

const PageHeader = ({ title, icon: Icon, description }) => (
  <div className="mb-8">
    <div className="flex items-center gap-3 mb-2">
      <div className="p-2.5 rounded-xl bg-primary-500/10 border border-primary-500/20 text-primary-400">
        <Icon size={20} />
      </div>
      <h1 className="font-display text-3xl font-semibold text-oxblood">{title}</h1>
    </div>
    <p className="text-xs font-mono text-ink-soft uppercase tracking-wider">{description}</p>
  </div>
);

const ComingSoonBadge = () => (
  <div className="mt-8 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-yellow-500/5 border border-amber-600/20 text-amber-600 text-[9px] font-mono font-bold uppercase tracking-widest w-fit">
    <Lock size={10} />
    AWAITING GEMINI UI INITIALIZATION
  </div>
);

export function Ledger() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Ledger"
        icon={BookOpen}
        description="Chronological immutable log of all verified skill points, certificates, and evidence."
      />
      <GlassPanel className="relative overflow-hidden border-emerald-500/10 bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-emerald-700 mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-emerald-400/20" /> Active Ledger Status: Online
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          The Skill Ledger records all proof-of-work achievements. Integrate your GitHub, upload certifications, or submit links to build an bulletproof, AI-validated professional record.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}

export function Briefs() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Growth Briefs"
        icon={FileText}
        description="Weekly custom intelligence briefs detailing high-priority, tailored steps."
      />
      <GlassPanel className="relative overflow-hidden border-primary-500/10 bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500/5 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-primary-400 mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-primary-400/20" /> Next Brief Release: Monday
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          Each Monday morning, your customized dashboard updates with high-priority growth steps, curated roadmaps, and targeted learning tasks mapped directly to closing local industry market demands.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}

export function Pulse() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Market Pulse"
        icon={TrendingUp}
        description="Live demand tracking of regional technical skills for AI & engineering roles."
      />
      <GlassPanel className="relative overflow-hidden border-oxblood/10 bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-oxblood/5 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-oxblood mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-oxblood/20" /> Data Source: AI Analysis Engines
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          Live index of hot skill clusters in major tech hubs (Bengaluru, NCR, Hyderabad, Mumbai). Instantly compare your active capabilities with real hiring demands.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}

export function Calendar() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Event Horizon"
        icon={CalendarIcon}
        description="Aggregated schedule of relevant local hackathons, Kaggle/LeetCode sprints, and events."
      />
      <GlassPanel className="relative overflow-hidden border-purple-500/10 bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/5 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-oxblood mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-purple-400/20" /> Synchronization: Dynamic
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          Tracks active competitions, community build days, and hiring tests, ensuring you never miss a prime opportunity to earn verified evidence credentials.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}

export function Portfolio() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Dossier"
        icon={FolderOpen}
        description="Shareable, proof-of-work powered developer portfolio that stands out to recruiters."
      />
      <GlassPanel className="relative overflow-hidden border-pink-500/10 bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-pink-500/5 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-oxblood mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-pink-400/20" /> Status: Generated
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          Replaces standard resumes with interactive proof of capability, showcasing your real GitHub commits, build weights, and actual AI-assessed skill levels.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}

export function Profile() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="pt-24 px-6 max-w-7xl mx-auto min-h-screen text-ink"
    >
      <PageHeader
        title="Identity Core"
        icon={User}
        description="User settings, intake personalization profile, and target role configurations."
      />
      <GlassPanel className="relative overflow-hidden border-rule bg-gradient-to-br from-bone via-bone to-bone">
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-surface/50 rounded-full blur-[120px] pointer-events-none" />
        <h2 className="text-sm font-mono font-bold uppercase text-ink-soft mb-4 flex items-center gap-2">
          <Zap size={14} className="fill-ink-soft/20" /> Target Profile: CS / AI
        </h2>
        <p className="text-sm font-mono leading-relaxed text-ink-soft max-w-xl">
          Edit your study duration availability, learning preferences, target role categories, and view structured intake results utilized by our growth brief models.
        </p>
        <ComingSoonBadge />
      </GlassPanel>
    </motion.div>
  );
}
