import React from 'react';
import { motion } from 'framer-motion';
import { howItWorksData } from '../mockData';
import { ArrowRight, Compass } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const HowItWorks = () => {
  return (
    <section id="how-it-works" style={{ padding: '7rem 1.5rem 6rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-indigo-500/5 rounded-full blur-[150px] pointer-events-none" />

      <div className="container max-w-4xl mx-auto">
        {/* Section Header */}
        <motion.div
          style={{ textAlign: 'center', marginBottom: '4rem', maxWidth: '700px', marginLeft: 'auto', marginRight: 'auto' }}
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="font-mono text-center"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-[10px] uppercase font-bold tracking-widest text-indigo-400 mb-4 select-none">
            <Compass size={10} className="animate-spin" style={{ animationDuration: '6s' }} /> Operational Protocol
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Your Journey in Four Protocols
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            From raw ambition to synchronized reality—here's how Delta compiles your career trajectory.
          </p>
        </motion.div>

        {/* Steps Timeline */}
        <div className="space-y-12 relative">
          {/* Vertical Grid Line for Cyber HUD timeline */}
          <div className="absolute left-[39px] top-6 bottom-6 w-[1px] bg-indigo-500/10 hidden sm:block" />

          {howItWorksData.map((step, index) => (
            <motion.div
              key={step.step}
              className="flex flex-col sm:flex-row gap-6 items-start relative z-10"
              initial={{ opacity: 0, x: -15 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              {/* Step circle */}
              <div className="w-20 h-20 rounded-lg border border-indigo-500/20 bg-slate-950/80 text-white flex items-center justify-center font-mono text-xl font-bold shrink-0 shadow-lg shadow-indigo-500/5 select-none transition-transform hover:scale-105">
                0{step.step}
              </div>

              {/* Step info glass card */}
              <GlassPanel className="p-6 border-white/5 bg-slate-950/40 font-mono flex-1 hover:border-indigo-500/20 transition-all duration-300">
                <div className="flex justify-between items-center text-[7px] text-slate-500 uppercase tracking-widest font-black mb-2 select-none">
                  <span>STAGE {index + 1} // NEURAL SEED</span>
                  <span className="text-indigo-400">READY</span>
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">
                  {step.title}
                </h3>
                <p className="text-slate-400 text-xs leading-relaxed uppercase tracking-wide text-justify">
                  {step.description === "Tell us about your career ambitions, current skills, and where you want to be in the future."
                    ? "Establish your target domain, sync your PDF resume, and feed your messy aspirations into the intake socket."
                    : step.description}
                </p>
              </GlassPanel>
            </motion.div>
          ))}
        </div>

        {/* CTA Button */}
        <motion.div
          className="text-center mt-12"
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <button
            className="btn-primary px-8 py-3.5 text-xs font-mono font-bold uppercase tracking-widest flex items-center justify-center gap-2 border border-white/10 shadow-lg shadow-white/5 transition-all duration-300 rounded-lg mx-auto"
            onClick={() => window.location.href = '/onboarding'}
          >
            Start Ingestion Protocol
            <ArrowRight size={14} />
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default HowItWorks;
