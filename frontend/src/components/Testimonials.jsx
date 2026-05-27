import React from 'react';
import { motion } from 'framer-motion';
import { testimonialsData } from '../mockData';
import { Star, Quote, Award } from 'lucide-react';
import GlassPanel from './ui/GlassPanel';

const Testimonials = () => {
  return (
    <section style={{ padding: '7rem 1.5rem 6rem', background: 'var(--bg-page)' }} className="relative">
      <div className="absolute top-0 left-0 w-[400px] h-[400px] bg-indigo-500/5 rounded-full blur-[180px] pointer-events-none" />

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
            <Award size={10} className="animate-bounce" /> Proof of Concept
          </div>
          <h2 className="heading-1 text-3xl font-black uppercase tracking-wider text-white mb-4">
            Success Stories from Our Community
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm uppercase tracking-wider">
            Real individuals achieving real career transformations with Delta.
          </p>
        </motion.div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonialsData.map((testimonial, index) => (
            <motion.div
              key={testimonial.id}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              className="group cursor-pointer select-none"
            >
              <GlassPanel className="p-6 border-white/5 group-hover:border-indigo-500/20 transition-all duration-300 flex flex-col justify-between min-h-[260px] font-mono relative overflow-hidden bg-slate-950/40">
                {/* Visual Accent */}
                <div className="absolute top-0 left-0 right-0 h-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-r from-indigo-500 to-violet-500" />
                
                <div>
                  {/* Quote Icon and Rating */}
                  <div className="flex justify-between items-center mb-4">
                    <Quote size={24} className="text-indigo-400/20" />
                    <div className="flex gap-0.5 select-none">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <Star key={i} size={12} className="fill-indigo-400 text-indigo-400 drop-shadow-[0_0_2px_rgba(99,102,241,0.5)]" />
                      ))}
                    </div>
                  </div>

                  {/* Quote content */}
                  <p className="text-slate-300 text-xs leading-relaxed uppercase tracking-wide mb-6 text-justify">
                    "{testimonial.quote.replace("Delta", "Delta OS")}"
                  </p>
                </div>

                {/* Author profile */}
                <div className="flex items-center gap-3 border-t border-white/5 pt-4">
                  <img
                    src={testimonial.image}
                    alt={testimonial.name}
                    className="w-10 h-10 rounded-lg border border-white/10 object-cover shrink-0 select-none group-hover:scale-105 transition-transform"
                  />
                  <div>
                    <div className="text-xs font-bold text-white uppercase tracking-wider">
                      {testimonial.name}
                    </div>
                    <div className="text-[10px] text-slate-500 uppercase tracking-widest mt-0.5">
                      {testimonial.role} // {testimonial.company}
                    </div>
                  </div>
                </div>

              </GlassPanel>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
