import React, { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { collegeAPI } from '../../lib/api';
import { ExportButton, HBars, Stat, SubpageShell, WeekBars, day, errText, input, pct } from './shared';

// One batch for the placement team: readiness spread, weekly activity, the
// skills most students are weak in, who needs a nudge, and every student.

export default function CollegeBatch() {
  const { batchId } = useParams();
  const [params] = useSearchParams();
  const cid = params.get('cid');
  const [q, setQ] = useState('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['college-batch-dashboard', cid, batchId],
    queryFn: () => collegeAPI.batchDashboard(cid, batchId),
    enabled: !!cid,
  });
  const studentLink = (uid) => `/college/students/${uid}?cid=${cid}`;

  if (isLoading) return <SubpageShell cid={cid}><Loader2 className="h-6 w-6 animate-spin text-ink-soft" /></SubpageShell>;
  if (!data) return <SubpageShell cid={cid}><p className="text-ink-soft">{errText(error, 'Could not load this batch.')}</p></SubpageShell>;

  const students = data.students_list.filter((s) => !q || `${s.name} ${s.roll_no || ''}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <SubpageShell cid={cid}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-[clamp(1.7rem,4vw,2.3rem)] font-semibold text-oxblood m-0">{data.batch.name}</h1>
          <p className="text-ink-soft text-[13px] m-0 mt-1">Active students only · updated {day(data.as_of)} (refreshes every few minutes)</p>
        </div>
        <span className="flex flex-wrap gap-2">
          <ExportButton cid={cid} kind="batch_readiness" params={{ batch_id: batchId }}>Readiness CSV</ExportButton>
          <ExportButton cid={cid} kind="roster_status" params={{ batch_id: batchId }}>Roster CSV</ExportButton>
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        <Stat label="Students" value={data.students} />
        <Stat label="Avg readiness" value={data.avg_readiness ?? '—'} hint="of those who've practised" />
        <Stat label="Coverage" value={pct(data.coverage_pct)} hint="practice types tried" />
        <Stat label="Active 7 days" value={pct(data.active_7d_pct)} />
        <Stat label="Active 30 days" value={pct(data.active_30d_pct)} />
        <Stat label="Need a nudge" value={data.at_risk} />
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="border border-rule bg-paper p-4">
          <h2 className="m-0 mb-3 text-[15px] font-semibold">Readiness</h2>
          <HBars caption="Students by readiness level" items={data.buckets.map((b) => ({ label: b.label, value: b.students }))} />
        </section>
        <section className="border border-rule bg-paper p-4">
          <h2 className="m-0 mb-3 text-[15px] font-semibold">Students active each week</h2>
          <WeekBars caption="Share of students active each week" weeks={data.trend.map((w) => ({ week_of: w.week_of, value: w.active_pct }))} />
        </section>
      </div>

      <section className="mt-6 border border-rule bg-paper p-4">
        <h2 className="m-0 text-[15px] font-semibold">Weakest skills</h2>
        <p className="m-0 mt-1 mb-3 text-[13px] text-ink-soft">Skills where the most students score under 70% (with at least 2 questions answered).</p>
        {data.weak_skills.length ? (
          <HBars caption="Students weak in each skill" items={data.weak_skills.map((w) => ({
            label: w.skill, value: w.students_weak, display: `${w.students_weak} of ${w.students_tested} · avg ${w.avg_score}%`,
          }))} />
        ) : <p className="m-0 text-[14px] text-ink-soft">Not enough test results yet.</p>}
      </section>

      <section className="mt-6">
        <h2 className="m-0 text-[15px] font-semibold">Need a nudge ({data.at_risk_students.length})</h2>
        <ul className="m-0 mt-2 p-0 list-none border border-rule bg-paper divide-y divide-rule">
          {data.at_risk_students.map((s) => (
            <li key={s.user_id} className="px-4 py-3 text-[14px]">
              <Link to={studentLink(s.user_id)} className="text-ink font-semibold underline-offset-2 hover:underline">{s.name}</Link>
              <span className="text-ink-soft"> · {s.roll_no || 'no roll no.'} · last active {s.last_active ? day(s.last_active) : 'never'}</span>
              <p className="m-0 text-[13px] text-ink-soft">{s.reasons.join(' · ')}</p>
            </li>
          ))}
          {!data.at_risk_students.length && <li className="px-4 py-3 text-[14px] text-ink-soft">No one right now.</li>}
        </ul>
      </section>

      <section className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 text-[15px] font-semibold">All students</h2>
          <input className={input} placeholder="Search name or roll no." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search students" />
        </div>
        <div className="mt-2 overflow-x-auto border border-rule bg-paper">
          <table className="w-full text-[13.5px] border-collapse">
            <thead>
              <tr className="text-left text-ink-soft font-mono text-[10.5px] uppercase tracking-[0.1em]">
                <th className="px-3 py-2 font-normal">Student</th><th className="px-3 py-2 font-normal">Roll no.</th>
                <th className="px-3 py-2 font-normal">Readiness</th><th className="px-3 py-2 font-normal">Tried</th>
                <th className="px-3 py-2 font-normal">Practice</th><th className="px-3 py-2 font-normal">Last active</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.user_id} className="border-t border-rule">
                  <td className="px-3 py-2"><Link to={studentLink(s.user_id)} className="text-ink underline-offset-2 hover:underline">{s.name}</Link>{!s.verified && <span className="text-ink-soft"> · not on roster</span>}</td>
                  <td className="px-3 py-2 text-ink-soft">{s.roll_no || '—'}</td>
                  <td className="px-3 py-2 tabular-nums">{s.readiness ?? '—'} <span className="text-ink-soft">{s.label}</span></td>
                  <td className="px-3 py-2 tabular-nums text-ink-soft">{s.coverage}/{s.coverage_total}</td>
                  <td className="px-3 py-2 tabular-nums text-ink-soft">{s.tests} tests · {s.coding} coding · {s.interviews} interviews</td>
                  <td className="px-3 py-2 text-ink-soft">{s.last_active ? day(s.last_active) : 'never'}</td>
                </tr>
              ))}
              {!students.length && <tr><td colSpan={6} className="px-3 py-3 text-ink-soft">No students{q ? ' match' : ' yet'}.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </SubpageShell>
  );
}
