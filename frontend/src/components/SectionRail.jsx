import React, { useEffect, useState } from 'react';

// Fixed left progress rail — dots per landing section, active one shows
// its "NN · NAME" label in oxblood mono, matching the memorandum site.
const sections = [
  { id: 'cover', label: 'Cover' },
  { id: 'showcase', label: 'In Action' },
  { id: 'how-it-works', label: 'Workflow' },
  { id: 'feedback', label: 'Contact' },
];

const SectionRail = () => {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const idx = sections.findIndex((s) => s.id === entry.target.id);
            if (idx !== -1) setActive(idx);
          }
        });
      },
      { rootMargin: '-45% 0px -45% 0px' }
    );
    sections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="hidden xl:flex fixed left-6 top-1/2 -translate-y-1/2 z-40 flex-col gap-5">
      {sections.map((s, i) => (
        <button
          key={s.id}
          onClick={() => document.getElementById(s.id)?.scrollIntoView({ behavior: 'smooth' })}
          className="flex items-center gap-3 bg-transparent border-none p-0 cursor-pointer group"
          aria-label={s.label}
        >
          <span
            className={`rounded-full transition-all duration-300 ${
              i === active ? 'w-2 h-2 bg-oxblood' : 'w-1.5 h-1.5 bg-rule group-hover:bg-ink-soft'
            }`}
          />
          <span
            className={`font-mono text-[10px] uppercase tracking-[0.22em] transition-opacity duration-300 ${
              i === active ? 'text-oxblood opacity-100' : 'opacity-0 group-hover:opacity-60 text-ink-soft'
            }`}
          >
            0{i} &middot; {s.label}
          </span>
        </button>
      ))}
    </div>
  );
};

export default SectionRail;
