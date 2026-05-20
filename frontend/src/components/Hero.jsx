import React from 'react';
import { motion } from 'motion/react';
import { ArrowRight, Sparkles } from 'lucide-react';
import ParticleBackground from './ParticleBackground';
import FloatingShapes from './FloatingShapes';
import { heroData, statsData } from '../mockData';

const Hero = () => {
  return (
    <section className="hero-section" style={{ position: 'relative', overflow: 'hidden' }}>
      <FloatingShapes />
      <ParticleBackground />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32 flex flex-col items-center text-center">
        {/* Announcement Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <div className="hero-announcement inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/50 backdrop-blur-sm border border-white/10 text-sm font-medium text-secondary-foreground">
            <Sparkles size={14} className="text-primary" />
            <span>{heroData.announcement}</span>
          </div>
        </motion.div>

        {/* Main Heading */}
        <motion.h1
          className="heading-hero hero-title text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight mb-6 max-w-4xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}>

          Your{' '}
          <span style={{
            fontFamily: "'DM Serif Display', serif",
            background: 'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 50%, #FFA07A 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            fontStyle: 'italic'
          }}>
            Personalized
          </span>
          {' '}Path to Career Success
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="body-large hero-subtitle text-lg sm:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}>

          {heroData.subtitle}
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          className="flex flex-col sm:flex-row gap-4 justify-center items-center w-full sm:w-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}>

          <button
            className="btn-primary flex items-center justify-center gap-2 px-8 py-4 text-lg w-full sm:w-auto"
            onClick={() => window.location.href = '/onboarding'}
          >
            {heroData.ctaPrimary}
            <ArrowRight size={20} />
          </button>
          <button className="btn-secondary px-8 py-4 text-lg w-full sm:w-auto">
            {heroData.ctaSecondary}
          </button>
        </motion.div>

        {/* Stats */}
        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-8 mt-20 max-w-4xl mx-auto w-full"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}>

          {statsData.map((stat, index) =>
            <div key={index} className="text-center p-4 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 transition-colors">
              <div className="text-3xl lg:text-4xl font-bold mb-2 text-foreground">
                {stat.value}
              </div>
              <div className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                {stat.label}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </section>);

};

export default Hero;