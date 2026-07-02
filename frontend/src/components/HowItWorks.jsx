import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

const steps = [
  {
    label: 'Profile',
    title: 'The intake agent learns the student properly.',
    detail:
      'It collects identity, place, qualification, college, resume evidence, interests, future goals, constraints, available hours, exams, preferred learning style, and anything unusual that can change the plan.',
  },
  {
    label: 'Week',
    title: 'The planner chooses the next useful week.',
    detail:
      'It does not dump a full-year checklist. Every week it decides whether to assign a course, paper, project, language class, revision block, internship prep, or a complete exam pause.',
  },
  {
    label: 'Proof',
    title: 'The progress report turns work into momentum.',
    detail:
      'Progress, completed tasks, project depth, resume improvements, internship signals, news, and visual summaries are maintained by the progress agent.',
  },
  {
    label: 'Adjust',
    title: 'The system keeps listening.',
    detail:
      'The weekly chat asks whether the pace is right and whether exams, deadlines, health, placement drives, or new goals should shift the next week.',
  },
];

const HowItWorks = () => {
  return (
    <section id="how-it-works" className="bg-bone px-6 pt-24 pb-28">
      <div className="max-w-[1140px] mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="max-w-[820px] mb-14"
        >
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] m-0 mb-6">
            <span className="text-oxblood">02</span>
            <span className="text-ink-soft"> / Workflow</span>
          </p>
          <h2 className="font-display text-ink font-normal leading-[1.05] m-0 mb-5" style={{ fontSize: 'clamp(2.2rem, 5vw, 3.6rem)' }}>
            Built for years of guidance, <em>planned one week at a time.</em>
          </h2>
          <p className="font-display italic text-ink-soft text-[1.15rem] leading-[1.6] max-w-[660px] m-0">
            Delta should understand long timelines like masters abroad, fourth-year deadlines, German classes, placements, and exam seasons without forcing the student into a rigid template.
          </p>
        </motion.div>

        <div className="border-t border-rule">
          {steps.map((step, index) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.38, delay: index * 0.05 }}
              className="delta-workflow-row grid gap-8 py-10 border-b border-rule items-start"
              style={{ gridTemplateColumns: '120px minmax(0, 380px) minmax(0, 1fr)' }}
            >
              <span className="font-display text-oxblood font-normal leading-none" style={{ fontSize: 'clamp(2.6rem, 5vw, 4rem)' }}>
                0{index + 1}
              </span>
              <h3 className="font-display text-ink font-medium leading-[1.2] m-0" style={{ fontSize: 'clamp(1.4rem, 2.6vw, 1.9rem)' }}>
                {step.title}
              </h3>
              <p className="text-ink-soft text-[15px] leading-[1.7] m-0">
                {step.detail}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="mt-12"
        >
          <button
            onClick={() => window.location.href = '/intake'}
            className="bg-oxblood text-bone border border-oxblood font-mono text-[11px] uppercase tracking-[0.18em] px-8 py-[15px] cursor-pointer inline-flex items-center gap-2 hover:bg-ink hover:border-ink transition-colors"
          >
            Start intake
            <ArrowRight size={14} />
          </button>
        </motion.div>
      </div>

      <style>{`
        @media (max-width: 860px) {
          .delta-workflow-row {
            grid-template-columns: 1fr !important;
            gap: 12px !important;
          }
        }
      `}</style>
    </section>
  );
};

export default HowItWorks;
