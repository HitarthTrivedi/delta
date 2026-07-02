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
    <section id="features" className="bg-bone px-6 pt-20 pb-16">
      <div className="max-w-[1120px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="max-w-[660px] mb-9"
        >
          <p className="kicker mb-3">
            A career plan that updates only when the student is ready
          </p>
          <h2 className="font-display text-oxblood font-medium leading-[1.12] m-0" style={{ fontSize: 'clamp(2rem, 4vw, 3rem)' }}>
            Three agents, one continuously adjusted path.
          </h2>
        </motion.div>

        <div className="grid gap-px bg-rule border border-rule" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
          {agents.map((agent, index) => {
            const Icon = agent.icon;
            return (
              <motion.article
                key={agent.name}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.42, delay: index * 0.06 }}
                className="min-h-[288px] bg-paper p-7 flex flex-col justify-between"
              >
                <div>
                  <div className="w-[42px] h-[42px] border border-rule bg-accent-surface flex items-center justify-center text-oxblood mb-7">
                    <Icon size={19} strokeWidth={1.8} />
                  </div>
                  <p className="kicker mb-2">
                    {agent.name}
                  </p>
                  <h3 className="font-display text-ink text-[1.4rem] leading-[1.25] font-semibold m-0 mb-3.5">
                    {agent.title}
                  </h3>
                  <p className="text-ink-soft text-[15px] leading-[1.65] m-0">
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
