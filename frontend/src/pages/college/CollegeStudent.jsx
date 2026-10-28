import React from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { collegeAPI } from '../../lib/api';
import { HBars, Stat, SubpageShell, WeekBars, day, errText } from './shared';

// One student, as their college may see them: readiness, skills, practice
// with integrity notes, and activity. Never chats, résumé, jobs or social.

const TYPE_ORDER = ['theory', 'coding', 'interview'];

export default function CollegeStudent() {
  const { userId } = useParams();
  const [params] = useSearchParams();
  const cid = params.get('cid');
  const { data, isLoading, error } = useQuery({
    queryKey: ['college-student', cid, userId],
    queryFn: () => collegeAPI.student(cid, userId),
    enabled: !!cid,
  });

  if (isLoading) return <SubpageShell cid={cid}><Loader2 className="h-6 w-6 animate-spin text-ink-soft" /></SubpageShell>;
  if (!data) return <SubpageShell cid={cid}><p className="text-ink-soft">{errText(error, 'Could not load this student.')}</p></SubpageShell>;

  const { student: s, readiness: r, activity: a } = data;
  return (
    <SubpageShell cid={cid}>
      {s.batch && <Link to={`/college/batches/${s.batch.id}?cid=${cid}`} className="text-[13px] text-oxblood underline">{s.batch.name}</Link>}
      <h1 className="font-display text-[clamp(1.7rem,4vw,2.3rem)] font-semibold text-oxblood m-0 mt-1">{s.name}</h1>
      <p className="text-ink-soft text-[13px] m-0 mt-1">
        {s.roll_no || 'no roll no.'} · {s.verified ? 'on your roster' : 'not on your roster'} · joined {day(s.joined_on)}
        {s.cgpa != null && ` · CGPA ${s.cgpa}`}{s.backlogs != null && ` · ${s.backlogs} backlogs`}
      </p>
      {data.risk.length > 0 && <p className="m-0 mt-3 border-l-2 border-oxblood pl-3 text-[14px] text-ink">{data.risk.join(' · ')}</p>}

      <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Stat label="Readiness" value={r.readiness ?? '—'} hint={r.label} />
        <Stat label="Tried" value={`${r.coverage}/${r.coverage_total}`} hint={r.field_label} />
        <Stat label="Last active" value={a.last_active ? day(a.last_active) : 'never'} hint={`${a.active_days_30d} active days in 30`} />
        <Stat label="Last practice" value={a.last_practice ? day(a.last_practice) : 'never'} />
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="border border-rule bg-paper p-4">
          <h2 className="m-0 mb-3 text-[15px] font-semibold">By practice type</h2>
          <ul className="m-0 p-0 list-none grid gap-1 text-[14px]">
            {TYPE_ORDER.filter((t) => r.applicable_types.includes(t)).map((t) => {
              const x = r.by_type[t];
              return <li key={t}>{x.label}: <span className="text-ink-soft">{x.count ? `${x.count} done · recent avg ${x.average ?? '—'} · best ${x.best ?? '—'}` : 'not tried yet'}</span></li>;
            })}
          </ul>
          {r.rubric.length > 0 && (
            <>
              <h3 className="m-0 mt-4 mb-1 text-[14px] font-semibold">Mock interview areas (out of 10)</h3>
              <ul className="m-0 p-0 list-none grid gap-1 text-[14px]">
                {r.rubric.map((x) => <li key={x.key}>{x.label}: <span className="text-ink-soft tabular-nums">{x.score}</span></li>)}
              </ul>
            </>
          )}
        </section>
        <section className="border border-rule bg-paper p-4">
          <h2 className="m-0 mb-3 text-[15px] font-semibold">Active days each week</h2>
          <WeekBars caption="Active days each week" max={7} format={(v) => `${v ?? 0} d`}
            weeks={a.weeks.map((w) => ({ week_of: w.week_of, value: w.active_days }))} />
        </section>
      </div>

      <section className="mt-6 border border-rule bg-paper p-4">
        <h2 className="m-0 mb-3 text-[15px] font-semibold">Skills</h2>
        {r.skills.length ? (
          <HBars caption="Score by skill" max={100} items={r.skills.map((x) => ({
            label: x.skill, value: x.score, display: `${x.score}% · ${x.questions} q${x.coding_problems ? ` · ${x.coding_problems} coding` : ''}`,
          }))} />
        ) : <p className="m-0 text-[14px] text-ink-soft">No skill results yet.</p>}
      </section>

      <section className="mt-6">
        <h2 className="m-0 text-[15px] font-semibold">Recent practice</h2>
        <p className="m-0 mt-1 text-[13px] text-ink-soft">
          {data.integrity.sessions} finished · {data.integrity.timed} timed · {data.integrity.with_notes} with notes on how they were taken. Notes are facts, not verdicts.
        </p>
        <ul className="m-0 mt-2 p-0 list-none border border-rule bg-paper divide-y divide-rule">
          {data.practice.map((p) => (
            <li key={p.id} className="px-4 py-3 text-[14px]">
              <span className="text-ink">{p.title}</span> <span className="text-ink-soft">· {p.score}% · {day(p.date)}</span>
              {p.notes.length > 0 && <p className="m-0 text-[12.5px] text-ink-soft">{p.notes.join(' · ')}</p>}
            </li>
          ))}
          {!data.practice.length && <li className="px-4 py-3 text-[14px] text-ink-soft">No practice yet.</li>}
        </ul>
      </section>
    </SubpageShell>
  );
}
