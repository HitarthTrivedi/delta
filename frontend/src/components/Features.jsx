import React from 'react';
import { motion } from 'framer-motion';
import { ClipboardList, CalendarDays, Gauge } from 'lucide-react';

const agents = [
  {
    icon: ClipboardList,
    name: 'Agent 1',
    title: 'Intake and resume analysis',
    description:
      'Talks with the student once, reads the resume, captures qualification, college, location, interests, goals, constraints, weekly hours, exams, learning style, and any useful personal context.',
  },
  {
    icon: CalendarDays,
    name: 'Agent 2',
    title: 'One-week roadmap strategist',
    description:
      'Creates only the next week of work. It chooses courses, projects, papers, practice, language classes, or exam-only weeks based on pace, deadlines, completed tasks, and long-term goals.',
  },
  {
    icon: Gauge,
    name: 'Agent 3',
    title: 'Progress and opportunity controller',
    description:
      'Studies all progress, keeps the dashboard current, surfaces internships and news, improves resume positioning, and turns completed proof into a clear visual career record.',
  },
];

const Features = () => {
  return (
    <section id="features" style={{ background: '#000', padding: '5rem 1.5rem 4rem' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          style={{ maxWidth: 660, marginBottom: 34 }}
        >
          <p style={{
            color: 'rgba(255,255,255,0.48)',
            fontSize: 13,
            fontWeight: 600,
            margin: '0 0 12px',
          }}>
            A career plan that updates only when the student is ready
          </p>
          <h2 style={{
            color: '#fff',
            fontSize: 'clamp(2rem, 4vw, 3rem)',
            lineHeight: 1.12,
            fontWeight: 700,
            letterSpacing: 0,
            margin: 0,
          }}>
            Three agents, one continuously adjusted path.
          </h2>
        </motion.div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 1,
          background: 'rgba(255,255,255,0.1)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          {agents.map((agent, index) => {
            const Icon = agent.icon;
            return (
              <motion.article
                key={agent.name}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.42, delay: index * 0.06 }}
                style={{
                  minHeight: 288,
                  background: '#050505',
                  padding: 28,
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{
                    width: 42,
                    height: 42,
                    borderRadius: 8,
                    border: '1px solid rgba(255,255,255,0.14)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    marginBottom: 28,
                    background: 'rgba(255,255,255,0.04)',
                  }}>
                    <Icon size={19} strokeWidth={1.8} />
                  </div>
                  <p style={{
                    color: 'rgba(255,255,255,0.38)',
                    fontSize: 12,
                    fontWeight: 700,
                    margin: '0 0 8px',
                  }}>
                    {agent.name}
                  </p>
                  <h3 style={{
                    color: '#fff',
                    fontSize: 22,
                    lineHeight: 1.25,
                    fontWeight: 650,
                    letterSpacing: 0,
                    margin: '0 0 14px',
                  }}>
                    {agent.title}
                  </h3>
                  <p style={{
                    color: 'rgba(255,255,255,0.52)',
                    fontSize: 15,
                    lineHeight: 1.65,
                    margin: 0,
                  }}>
                    {agent.description}
                  </p>
                </div>
              </motion.article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;
