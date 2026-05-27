import React from 'react';
import { motion } from 'framer-motion';
import { pricingData } from '../mockData';
import { Check, ArrowRight, Shield } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const Pricing = () => {
  return (
    <section id="pricing" style={{ padding: '7rem 1.5rem 6rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute top-1/2 left-1/4 w-[450px] h-[450px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none" />

      <div className="container max-w-6xl mx-auto">
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
            <Shield size={10} className="animate-pulse" /> Memory License
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            Choose the synchronization license that fits your trajectory.
          </p>
        </motion.div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {pricingData.map((plan, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              className="group relative select-none"
            >
              <GlassPanel className={`p-6 flex flex-col justify-between h-full font-mono relative overflow-hidden bg-slate-950/40 transition-all duration-300 ${
                plan.popular 
                  ? 'border-indigo-500/40 shadow-xl shadow-indigo-500/5 group-hover:border-indigo-500/60' 
                  : 'border-white/5 group-hover:border-indigo-500/20'
              }`}>
                {/* Visual Glow line for popular card */}
                {plan.popular && (
                  <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />
                )}

                <div>
                  {/* License Type Badge */}
                  <div className="flex justify-between items-center text-[7px] text-slate-500 uppercase tracking-widest font-black mb-3">
                    <span>LICENSE MODULE</span>
                    {plan.popular && <span className="text-indigo-400 animate-pulse">RECOMMENDED</span>}
                  </div>

                  {/* Plan Name */}
                  <h3 className="text-base font-bold uppercase tracking-wider text-white mb-1">
                    {plan.name}
                  </h3>

                  {/* Price */}
                  <div className="flex items-baseline gap-1.5 mb-3">
                    <span className="text-3xl font-black text-white">
                      {plan.price === 'Custom' ? plan.price : `$${plan.price}`}
                    </span>
                    {plan.price !== 'Custom' && (
                      <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                        /{plan.period}
                      </span>
                    )}
                  </div>

                  {/* Description */}
                  <p className="text-slate-400 text-[11px] leading-relaxed uppercase tracking-wider mb-6 border-b border-white/5 pb-4">
                    {plan.description}
                  </p>

                  {/* Features List */}
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2.5">
                        <div className="w-4 h-4 rounded border border-indigo-500/20 bg-indigo-500/10 flex items-center justify-center shrink-0 mt-0.5 select-none">
                          <Check size={10} className="text-indigo-400" strokeWidth={3} />
                        </div>
                        <span className="text-xs text-slate-300 uppercase tracking-wider font-mono">
                          {feature}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CTA Button */}
                <button 
                  onClick={() => window.location.href = '/onboarding'}
                  className={`w-full py-3 text-xs font-mono font-bold uppercase tracking-widest rounded-lg transition-all duration-300 flex items-center justify-center gap-1.5 border ${
                    plan.popular
                      ? 'bg-indigo-500 hover:bg-indigo-600 text-slate-950 border-indigo-400'
                      : 'bg-white/5 border-white/5 hover:bg-white/10 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {plan.cta}
                  <ArrowRight size={12} />
                </button>

              </GlassPanel>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;
