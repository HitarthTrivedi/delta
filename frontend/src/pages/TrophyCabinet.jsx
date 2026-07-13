import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Trophy, Award, BadgeCheck, GraduationCap, FolderGit2, Medal,
  Plus, X, Trash2, ExternalLink, Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { achievementsAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: 'var(--paper)',
  border: '1px solid var(--rule)',
  borderRadius: 0,
};

const serif = "'Cormorant Garamond', Georgia, serif";
const mono = "'IBM Plex Mono', ui-monospace, monospace";

const monoLabel = {
  fontFamily: mono,
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--ink-soft)',
};

// Type → icon + accent colour + label. Drives the ledger's left column.
const TYPES = {
  certificate: { label: 'Certificate', icon: BadgeCheck, color: 'var(--ink-soft)' },
  project: { label: 'Project', icon: FolderGit2, color: 'var(--oxblood)' },
  award: { label: 'Award', icon: Trophy, color: 'var(--oxblood)' },
  course: { label: 'Course', icon: GraduationCap, color: 'var(--ink-soft)' },
  other: { label: 'Other', icon: Medal, color: 'var(--ink-soft)' },
};

const TYPE_KEYS = Object.keys(TYPES);

const emptyForm = { type: 'certificate', title: '', organization: '', date_achieved: '', url: '', description: '' };

export default function TrophyCabinet() {
  const userId = useAuthStore((state) => state.userId);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const data = await achievementsAPI.list(userId);
      setItems(data?.achievements || []);
    } catch (err) {
      console.error(err);
      toast.error('Could not load your achievements.');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) loadItems();
  }, [userId, loadItems]);

  const counts = useMemo(() => {
    const c = { all: items.length };
    for (const key of TYPE_KEYS) c[key] = 0;
    for (const it of items) c[it.type] = (c[it.type] || 0) + 1;
    return c;
  }, [items]);

  const visible = filter === 'all' ? items : items.filter((it) => it.type === filter);

  const openAdd = () => { setForm(emptyForm); setModalOpen(true); };

  const saveAchievement = async () => {
    const title = form.title.trim();
    if (!title) { toast.error('Give your achievement a title.'); return; }
    setSaving(true);
    try {
      const res = await achievementsAPI.create(userId, { ...form, title });
      if (res?.achievement) setItems((prev) => [res.achievement, ...prev]);
      setModalOpen(false);
      setForm(emptyForm);
      toast.success('Added to your trophy cabinet.');
    } catch (err) {
      console.error(err);
      toast.error('Could not save this achievement.');
    } finally {
      setSaving(false);
    }
  };

  const removeAchievement = async (id) => {
    setConfirmDelete(null);
    setDeletingId(id);
    const prev = items;
    setItems((cur) => cur.filter((it) => it.id !== id)); // optimistic
    try {
      await achievementsAPI.remove(userId, id);
      toast.success('Removed.');
    } catch (err) {
      console.error(err);
      setItems(prev); // rollback
      toast.error('Could not remove this achievement.');
    } finally {
      setDeletingId(null);
    }
  };

  const setField = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bone)', color: 'var(--ink)', padding: '5.5rem 1.5rem 3.5rem' }}>
      <div style={{ maxWidth: 1040, margin: '0 auto' }}>

        {/* Header */}
        <header style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 18, alignItems: 'flex-end', marginBottom: 22 }}>
          <div>
            <h1 style={{ fontFamily: serif, fontWeight: 500, color: 'var(--oxblood)', fontSize: 'clamp(1.9rem, 3.5vw, 2.6rem)', lineHeight: 1.1, letterSpacing: 0, margin: 0, maxWidth: 640 }}>
              Everything you've earned, in one place.
            </h1>
            <p style={{ margin: '10px 0 0', color: 'var(--ink-soft)', fontSize: 14.5, lineHeight: 1.55, maxWidth: '58ch' }}>
              The certificates, projects, and awards you've collected on your journey. Add anything you're proud of.
            </p>
          </div>
          <button className="tc-btn tc-btn-primary" onClick={openAdd}>
            <Plus size={14} /> Add achievement
          </button>
        </header>

        {/* Filter tabs */}
        <div role="tablist" aria-label="Filter achievements" style={{ display: 'flex', gap: 24, borderBottom: '1px solid var(--rule)', marginBottom: 22, overflowX: 'auto' }}>
          {['all', ...TYPE_KEYS].map((key) => {
            const isActive = filter === key;
            const label = key === 'all' ? 'All' : TYPES[key].label + 's';
            return (
              <button
                key={key}
                role="tab"
                aria-selected={isActive}
                className={`tc-tab${isActive ? ' tc-tab-active' : ''}`}
                onClick={() => setFilter(key)}
              >
                {label}
                <span style={{ fontFamily: mono, fontSize: 11, fontWeight: 500, marginLeft: 7, opacity: 0.75 }}>{counts[key] || 0}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-soft)', padding: '40px 0', fontSize: 14 }}>
            <Loader2 size={17} className="tc-spin" style={{ animation: 'spin 1s linear infinite' }} /> Loading your cabinet...
          </div>
        ) : visible.length === 0 ? (
          <section style={{ ...panelStyle, padding: '30px 26px' }}>
            <h2 style={{ margin: '0 0 8px', fontFamily: serif, fontSize: 22, fontWeight: 600 }}>
              {items.length === 0 ? 'Your cabinet is empty.' : 'Nothing of this type yet.'}
            </h2>
            <p style={{ margin: '0 0 20px', color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.6, maxWidth: '58ch' }}>
              {items.length === 0
                ? 'Certificates, projects, awards, courses — anything you\'ve earned belongs here. Each entry strengthens the record behind your resume.'
                : 'Try another filter, or add one now.'}
            </p>
            <button className="tc-btn tc-btn-primary" onClick={openAdd}>
              <Plus size={14} /> {items.length === 0 ? 'Add your first achievement' : 'Add achievement'}
            </button>
          </section>
        ) : (
          <section style={{ ...panelStyle }}>
            {visible.map((it, i) => {
              const meta = TYPES[it.type] || TYPES.other;
              const Icon = meta.icon;
              const metaLine = [it.organization, it.date_achieved].filter(Boolean).join('  ·  ');
              return (
                <article
                  key={it.id}
                  className="tc-row"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '104px minmax(0, 1fr) auto',
                    gap: 18,
                    padding: '18px 22px',
                    borderTop: i ? '1px solid var(--rule)' : 'none',
                    alignItems: 'start',
                  }}
                >
                  <span className="tc-type" style={{ ...monoLabel, color: meta.color, display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                    <Icon size={12} /> {meta.label}
                  </span>

                  <div style={{ minWidth: 0 }}>
                    <h3 style={{ margin: 0, fontSize: 15.5, fontWeight: 700, lineHeight: 1.4 }}>{it.title}</h3>
                    {metaLine && (
                      <p style={{ margin: '4px 0 0', color: 'var(--ink-soft)', fontSize: 12.5, lineHeight: 1.5 }}>{metaLine}</p>
                    )}
                    {it.description && (
                      <p style={{ margin: '7px 0 0', color: 'var(--ink-soft)', fontSize: 13, lineHeight: 1.55, maxWidth: '65ch' }}>{it.description}</p>
                    )}
                    {it.url && (
                      <a className="tc-link" href={it.url} target="_blank" rel="noreferrer">
                        View credential <ExternalLink size={12} />
                      </a>
                    )}
                  </div>

                  <button
                    className="tc-del"
                    onClick={() => setConfirmDelete(it)}
                    disabled={deletingId === it.id}
                    aria-label={`Remove ${it.title}`}
                    title="Remove"
                  >
                    {deletingId === it.id
                      ? <Loader2 size={14} className="tc-spin" style={{ animation: 'spin 1s linear infinite' }} />
                      : <Trash2 size={14} />}
                  </button>
                </article>
              );
            })}
          </section>
        )}
      </div>

      {/* Delete confirmation */}
      {confirmDelete && (
        <>
          <div onClick={() => setConfirmDelete(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(26,25,24,0.45)', zIndex: 80 }} />
          <div role="dialog" aria-modal="true" aria-label="Remove achievement" style={{ position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 81, background: 'var(--paper)', border: '1px solid var(--rule)', padding: 28, width: 'min(90vw, 420px)' }}>
            <p style={{ ...monoLabel, margin: '0 0 8px' }}>Remove achievement</p>
            <p style={{ color: 'var(--ink)', fontSize: 15, fontWeight: 600, margin: '0 0 12px', lineHeight: 1.4 }}>{confirmDelete.title}</p>
            <p style={{ color: 'var(--ink-soft)', fontSize: 13, margin: '0 0 20px', lineHeight: 1.5 }}>This permanently removes it from your trophy cabinet. This can't be undone.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="tc-btn tc-btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setConfirmDelete(null)}>
                Cancel
              </button>
              <button className="tc-btn tc-btn-primary" style={{ flex: 1, justifyContent: 'center' }} onClick={() => removeAchievement(confirmDelete.id)}>
                Remove
              </button>
            </div>
          </div>
        </>
      )}

      {/* Add modal */}
      {modalOpen && (
        <>
          <div onClick={() => !saving && setModalOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(26,25,24,0.45)', zIndex: 80 }} />
          <div role="dialog" aria-modal="true" aria-label="Add achievement" style={{
            position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 81,
            background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 0,
            padding: 26, width: 'min(94vw, 480px)', maxHeight: '88vh', overflowY: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h2 style={{ margin: 0, fontFamily: serif, fontSize: 21, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <Award size={17} style={{ color: 'var(--oxblood)' }} /> Add achievement
              </h2>
              <button onClick={() => !saving && setModalOpen(false)} aria-label="Close" style={{ background: 'none', border: 'none', color: 'var(--ink-soft)', cursor: 'pointer', padding: 10, display: 'flex' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Type selector */}
              <div>
                <label style={labelStyle}>Type</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {TYPE_KEYS.map((key) => {
                    const meta = TYPES[key];
                    const Icon = meta.icon;
                    const active = form.type === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        className={`tc-chip${active ? ' tc-chip-active' : ''}`}
                        onClick={() => setForm((f) => ({ ...f, type: key }))}
                      >
                        <Icon size={13} /> {meta.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label style={labelStyle}>Title <span style={{ color: 'var(--oxblood)' }}>*</span></label>
                <input className="tc-input" value={form.title} onChange={setField('title')} placeholder="e.g. AWS Certified Cloud Practitioner" autoFocus />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Organization</label>
                  <input className="tc-input" value={form.organization} onChange={setField('organization')} placeholder="e.g. Amazon, Coursera" />
                </div>
                <div>
                  <label style={labelStyle}>Date</label>
                  <input className="tc-input" value={form.date_achieved} onChange={setField('date_achieved')} placeholder="e.g. Jun 2025" />
                </div>
              </div>

              <div>
                <label style={labelStyle}>Link (optional)</label>
                <input className="tc-input" value={form.url} onChange={setField('url')} placeholder="https://..." />
              </div>

              <div>
                <label style={labelStyle}>Description (optional)</label>
                <textarea className="tc-input" value={form.description} onChange={setField('description')} placeholder="What did you build or learn? Why does it matter?" rows={3} style={{ resize: 'vertical' }} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
              <button className="tc-btn tc-btn-ghost" onClick={() => setModalOpen(false)} disabled={saving}>
                Cancel
              </button>
              <button className="tc-btn tc-btn-primary" onClick={saveAchievement} disabled={saving}>
                {saving
                  ? <Loader2 size={13} className="tc-spin" style={{ animation: 'spin 1s linear infinite' }} />
                  : <Plus size={13} />}
                Add to cabinet
              </button>
            </div>
          </div>
        </>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .tc-btn {
          font-family: 'IBM Plex Mono', ui-monospace, monospace;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          border-radius: 0;
          padding: 11px 18px;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
          flex-shrink: 0;
        }
        .tc-btn:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .tc-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .tc-btn-primary { background: var(--oxblood); color: var(--bone); border: 1px solid var(--oxblood); }
        .tc-btn-primary:hover:not(:disabled) { background: var(--ink); border-color: var(--ink); }
        .tc-btn-ghost { background: transparent; color: var(--ink); border: 1px solid var(--ink); }
        .tc-btn-ghost:hover:not(:disabled) { background: var(--ink); color: var(--bone); }
        .tc-tab {
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          padding: 10px 2px 12px;
          margin-bottom: -1px;
          color: var(--ink-soft);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
          transition: color 0.15s ease, border-color 0.15s ease;
        }
        .tc-tab:hover { color: var(--ink); }
        .tc-tab:focus-visible { outline: 2px solid var(--oxblood); outline-offset: -2px; }
        .tc-tab-active { color: var(--ink); border-bottom-color: var(--oxblood); }
        .tc-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: var(--accent-surface);
          border: 1px solid var(--rule);
          color: var(--ink);
          border-radius: 0;
          padding: 8px 12px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: background-color 0.15s ease, color 0.15s ease;
        }
        .tc-chip:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .tc-chip-active { background: var(--ink); color: var(--bone); border-color: var(--ink); }
        .tc-input {
          width: 100%;
          background: var(--paper);
          border: 1px solid var(--rule);
          border-radius: 0;
          padding: 10px 12px;
          color: var(--ink);
          font-size: 14px;
          font-family: inherit;
          outline: none;
          box-sizing: border-box;
          transition: border-color 0.15s ease;
        }
        .tc-input::placeholder { color: var(--ink-soft); }
        .tc-input:focus { border-color: var(--oxblood); }
        .tc-link {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 9px;
          color: var(--ink);
          font-size: 13px;
          font-weight: 600;
          text-decoration: underline;
          text-underline-offset: 3px;
          transition: color 0.15s ease;
        }
        .tc-link:hover { color: var(--oxblood); }
        .tc-link:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        .tc-del {
          background: none;
          border: none;
          color: var(--ink-soft);
          cursor: pointer;
          padding: 8px;
          display: flex;
          transition: color 0.15s ease;
        }
        .tc-del:hover:not(:disabled) { color: var(--oxblood); }
        .tc-del:focus-visible { outline: 2px solid var(--oxblood); outline-offset: 2px; }
        @media (max-width: 560px) {
          .tc-row { grid-template-columns: minmax(0, 1fr) auto !important; }
          .tc-type { grid-column: 1 / -1; margin-top: 0 !important; }
        }
        @media (prefers-reduced-motion: reduce) {
          .tc-spin { animation: none !important; }
          .tc-btn, .tc-tab, .tc-chip, .tc-input, .tc-link, .tc-del { transition: none; }
        }
      `}</style>
    </main>
  );
}

const labelStyle = {
  display: 'block',
  fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
  fontSize: 10,
  fontWeight: 500,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--ink-soft)',
  marginBottom: 7,
};
