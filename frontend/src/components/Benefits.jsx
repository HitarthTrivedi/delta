import React from 'react';
import { motion } from 'framer-motion';
import { benefitsData } from '../mockData';
import { Check, Target } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const Benefits = () => {
  return (
    <section style={{ padding: '7rem 1.5rem 6rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute top-0 right-1/4 w-[450px] h-[450px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none" />

      <div className="container max-w-7xl mx-auto">
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
            <Target size={10} className="animate-pulse" /> TARGET PROFILES
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Tailored for Every Career Stage
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            Whether you're starting out, switching careers, or leveling up—Delta compiles your path.
          </p>
        </motion.div>

        {/* Benefits Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {benefitsData.map((benefit, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              className="group cursor-pointer select-none"
            >
              <GlassPanel className="p-6 border-white/5 bg-slate-950/40 group-hover:border-indigo-500/20 transition-all duration-300 flex flex-col justify-between min-h-[300px] font-mono relative overflow-hidden">
                {/* Visual Glow line on hover */}
                <div className="absolute top-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-indigo-500 to-violet-500" />

                <div>
                  {/* Top monospaced label */}
                  <div className="text-[7px] text-slate-500 uppercase tracking-widest font-black mb-3">
                    <span>STAGE PROFILE // 0{index + 1}</span>
                  </div>

                  {/* Title */}
                  <h3 className="text-base font-bold uppercase tracking-wider text-white mb-2 group-hover:text-indigo-300 transition-colors">
                    {benefit.title}
                  </h3>

                  {/* Description */}
                  <p className="text-slate-400 text-[11px] leading-relaxed uppercase tracking-wider mb-6 pb-4 border-b border-white/5">
                    {benefit.description}
                  </p>

                  {/* Points list */}
                  <ul className="space-y-2.5">
                    {benefit.points.map((point, idx) => (
                      <li key={idx} className="flex items-center gap-2.5">
                        <div className="w-4 h-4 rounded border border-indigo-500/20 bg-indigo-500/10 flex items-center justify-center shrink-0 select-none">
                          <Check size={10} className="text-indigo-400 animate-pulse" strokeWidth={3} />
                        </div>
                        <span className="text-xs text-slate-300 uppercase tracking-wider font-mono">
                          {point}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Bottom status decorative text */}
                <div className="mt-6 text-[7px] text-slate-600 uppercase tracking-widest font-black text-right">
                  <span>SYSTEM SYNCHRONIZED</span>
                </div>

              </GlassPanel>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Benefits;
