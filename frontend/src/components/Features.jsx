import React from 'react';
import { motion } from 'framer-motion';
import { featuresData } from '../mockData';
import { Target, TrendingUp, FileText, Linkedin, BarChart3, Brain } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const iconMap = {
  1: Target,
  2: TrendingUp,
  3: FileText,
  4: Linkedin,
  5: BarChart3,
  6: Brain
};

const Features = () => {
  return (
    <section id="features" style={{ padding: '7rem 1.5rem 5rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute top-1/2 left-1/2 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none transform -translate-x-1/2 -translate-y-1/2" />

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
            <Brain size={10} className="animate-pulse" /> Core Capabilities
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Intelligent Features for Your Success
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            AI-powered tools that adapt to your unique career journey and accelerate your growth.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featuresData.map((feature, index) => {
            const Icon = iconMap[feature.id];
            const glowColor = 
              feature.color === 'accent-orange' ? 'group-hover:border-orange-500/30' :
              feature.color === 'accent-blue' ? 'group-hover:border-blue-500/30' :
              feature.color === 'accent-purple' ? 'group-hover:border-purple-500/30' :
              feature.color === 'accent-pink' ? 'group-hover:border-pink-500/30' :
              feature.color === 'accent-green' ? 'group-hover:border-emerald-500/30' :
              'group-hover:border-indigo-500/30';

            const iconBg = 
              feature.color === 'accent-orange' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
              feature.color === 'accent-blue' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
              feature.color === 'accent-purple' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
              feature.color === 'accent-pink' ? 'bg-pink-500/10 text-pink-400 border-pink-500/20' :
              feature.color === 'accent-green' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
              'bg-slate-900 text-indigo-400 border-white/5';

            return (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                className="group cursor-pointer select-none"
              >
                <GlassPanel className={`p-6 border-white/5 group-hover:bg-slate-950/60 transition-all duration-300 flex flex-col justify-between min-h-[220px] font-mono relative overflow-hidden ${glowColor}`}>
                  
                  {/* Subtle top indicator line on hover */}
                  <div className={`absolute top-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r ${
                    feature.color === 'accent-orange' ? 'from-orange-500 to-amber-500' :
                    feature.color === 'accent-blue' ? 'from-blue-500 to-cyan-500' :
                    feature.color === 'accent-purple' ? 'from-purple-500 to-indigo-500' :
                    feature.color === 'accent-pink' ? 'from-pink-500 to-purple-500' :
                    feature.color === 'accent-green' ? 'from-emerald-500 to-cyan-500' :
                    'from-indigo-500 to-violet-500'
                  }`} />

                  <div>
                    <div className={`w-11 h-11 rounded-lg border flex items-center justify-center mb-4 transition-transform group-hover:scale-110 ${iconBg}`}>
                      <Icon size={18} strokeWidth={2} />
                    </div>
                    <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2 group-hover:text-indigo-300 transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-slate-400 text-xs leading-relaxed font-mono uppercase tracking-wide text-justify">
                      {feature.description}
                    </p>
                  </div>

                  {/* Outlined status label */}
                  <div className="mt-4 flex justify-between items-center text-[7px] text-slate-600 uppercase tracking-widest font-black">
                    <span>SYSTEM COMPILATION</span>
                    <span className="text-indigo-500/60 group-hover:text-indigo-400 transition-colors">ACTIVE // INTEGRATED</span>
                  </div>

                </GlassPanel>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;
