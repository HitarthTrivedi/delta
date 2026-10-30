import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Check, X, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import { recruiterAPI } from '../../lib/api';
import { RoadmapReview } from './RecruiterRoadmaps';
import AiUsageAdmin from './AiUsageAdmin';

const TABS = ['pending', 'approved', 'rejected', 'roadmaps', 'ai usage'];

/** Admin-only (ADMIN_EMAILS on the backend): approve or reject recruiter accounts. */
export default function RecruiterAdmin() {
  const [tab, setTab] = useState('pending');
  const [rows, setRows] = useState(null);
  const [forbidden, setForbidden] = useState(false);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    setRows(null);
    if (tab === 'roadmaps' || tab === 'ai usage') return;
    recruiterAPI.adminList(tab)
      .then((d) => setRows(d.recruiters))
      .catch((err) => {
        if (err?.response?.status === 403) setForbidden(true);
        else toast.error('Could not load recruiters.');
        setRows([]);
      });
  }, [tab]);

  const [pools, setPools] = useState({}); // recruiter id -> 'open' | 'campus'
  const review = async (id, approve) => {
    setBusyId(id);
    try {
      await recruiterAPI.adminReview(id, approve, approve ? (pools[id] || 'open') : undefined);
      setRows((r) => r.filter((x) => x.id !== id));
      toast.success(approve ? 'Recruiter approved.' : 'Recruiter rejected.');
    } catch (err) {
      toast.error('Could not update this recruiter.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main className="min-h-screen bg-bone text-ink px-4 py-12">
      <div className="max-w-[900px] mx-auto">
        <Link to="/recruiter" className="inline-flex items-center gap-1.5 text-[13px] text-ink-soft no-underline hover:text-oxblood mb-6">
          <ArrowLeft size={14} /> Recruiter portal
        </Link>
        <h1 className="font-display text-[clamp(2rem,5vw,2.6rem)] font-semibold text-oxblood m-0 mb-2">Recruiter approvals</h1>
        <p className="text-ink-soft text-[14px] leading-relaxed m-0 mb-6">
          Approve only recruiters you've verified, for example by a company email domain or a call. Approved recruiters can see every student who opted in.
        </p>

        {forbidden ? (
          <p className="text-ink-soft">Your account isn't an admin. Admins are set with ADMIN_EMAILS on the server.</p>
        ) : (
          <>
            <div className="flex gap-1 border-b border-rule mb-5" role="tablist">
              {TABS.map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tab === t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.12em] bg-transparent border-0 border-b-2 cursor-pointer ${tab === t ? 'text-oxblood border-oxblood' : 'text-ink-soft border-transparent'}`}
                >
                  {t}
                </button>
              ))}
            </div>

            {tab === 'ai usage' ? <AiUsageAdmin /> : tab === 'roadmaps' ? <RoadmapReview /> : rows === null ? (
              <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-ink-soft" /></div>
            ) : rows.length === 0 ? (
              <p className="text-ink-soft text-[14px]">No {tab} recruiters.</p>
            ) : (
              <div className="grid gap-3">
                {rows.map((r) => (
                  <article key={r.id} className="bg-paper border border-rule p-5 flex gap-4 items-start justify-between flex-wrap">
                    <div className="min-w-0">
                      <h2 className="m-0 text-[16px] font-semibold text-ink">{r.company}</h2>
                      <p className="m-0 text-[13px] text-ink-soft">{r.name}{r.designation && ` · ${r.designation}`}</p>
                      <p className="m-0 text-[13px] text-ink-soft mt-1">
                        {r.email || 'no email on token'}
                        {r.company_website && <> · <a href={r.company_website.startsWith('http') ? r.company_website : `https://${r.company_website}`} target="_blank" rel="noreferrer" className="text-oxblood underline">{r.company_website}</a></>}
                      </p>
                      <p className="m-0 font-mono text-[11px] text-ink-soft mt-1">Registered {r.created_at ? new Date(r.created_at + 'Z').toLocaleDateString() : ''}</p>
                    </div>
                    <div className="flex gap-2">
                      {tab !== 'approved' && (
                        <select aria-label="Recruiter pool" value={pools[r.id] || r.pool || 'open'}
                          onChange={(e) => setPools((p) => ({ ...p, [r.id]: e.target.value }))}
                          className="px-2 py-2 border border-rule bg-paper text-[12px] text-ink">
                          <option value="open">Off-campus (sees solo students)</option>
                          <option value="campus">Campus (sees linked colleges)</option>
                        </select>
                      )}
                      {tab === 'approved' && <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink-soft">{r.pool === 'campus' ? 'Campus' : 'Off-campus'}</span>}
                      {tab !== 'approved' && (
                        <button onClick={() => review(r.id, true)} disabled={busyId === r.id} className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-oxblood bg-oxblood text-bone font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer">
                          {busyId === r.id ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Approve
                        </button>
                      )}
                      {tab !== 'rejected' && (
                        <button onClick={() => review(r.id, false)} disabled={busyId === r.id} className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-ink text-ink bg-transparent font-mono text-[11px] uppercase tracking-[0.12em] cursor-pointer">
                          <X size={13} /> {tab === 'approved' ? 'Revoke' : 'Reject'}
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
