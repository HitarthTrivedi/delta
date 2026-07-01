import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Trophy, Award, BadgeCheck, GraduationCap, FolderGit2, Medal,
  Plus, X, Trash2, ExternalLink, Loader2, Calendar as CalendarIcon, Building2,
} from 'lucide-react';
import { toast } from 'sonner';
import { achievementsAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const panelStyle = {
  background: '#050505',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 8,
};

// Type → icon + accent colour + label. Drives the badge and card styling.
const TYPES = {
  certificate: { label: 'Certificate', icon: BadgeCheck, color: '#fbbf24' },
  project: { label: 'Project', icon: FolderGit2, color: '#60a5fa' },
  award: { label: 'Award', icon: Trophy, color: '#f472b6' },
  course: { label: 'Course', icon: GraduationCap, color: '#4ade80' },
  other: { label: 'Other', icon: Medal, color: 'rgba(255,255,255,0.6)' },
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
    <main style={{ minHeight: '100vh', background: '#000', color: '#fff', padding: '5.5rem 1.5rem 3rem' }}>
      <div style={{ maxWidth: 1000, margin: '0 auto' }}>

        {/* Header */}
        <header style={{ display: 'flex', justifyContent: 'space-between', gap: 18, alignItems: 'flex-start', marginBottom: 28 }}>
          <div>
            <p style={{ color: 'rgba(255,255,255,0.46)', fontSize: 13, fontWeight: 650, margin: '0 0 10px', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Trophy size={15} style={{ color: '#fbbf24' }} /> Trophy Cabinet
            </p>
            <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.2rem)', lineHeight: 1.08, letterSpacing: 0, margin: 0, maxWidth: 720 }}>
              Everything you've earned, in one place.
            </h1>
            <p style={{ margin: '14px 0 0', color: 'rgba(255,255,255,0.5)', fontSize: 15, lineHeight: 1.55, maxWidth: 620 }}>
              Track the certificates, projects, and awards you've collected on your journey. Add anything you're proud of.
            </p>
          </div>
          <button
            onClick={openAdd}
            style={{
              background: '#fff', color: '#000', border: 'none', borderRadius: 999,
              padding: '11px 18px', fontWeight: 700, flexShrink: 0,
              display: 'inline-flex', alignItems: 'center', gap: 8, cursor: 'pointer',
            }}
          >
            <Plus size={16} /> Add achievement
          </button>
        </header>

        {/* Filter chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 22 }}>
          {['all', ...TYPE_KEYS].map((key) => {
            const isActive = filter === key;
            const label = key === 'all' ? 'All' : TYPES[key].label + 's';
            const count = counts[key] || 0;
            return (
              <button
                key={key}
                onClick={() => setFilter(key)}
                style={{
                  background: isActive ? '#fff' : 'rgba(255,255,255,0.05)',
                  color: isActive ? '#000' : 'rgba(255,255,255,0.7)',
                  border: '1px solid rgba(255,255,255,0.12)', borderRadius: 999,
                  padding: '7px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: 7,
                }}
              >
                {label}
                <span style={{ opacity: 0.6, fontSize: 12 }}>{count}</span>
              </button>
            );
          })}
        </div>

        {/* Content */}
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,0.5)', padding: '40px 0' }}>
            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> Loading your cabinet...
          </div>
        ) : visible.length === 0 ? (
          <section style={{ ...panelStyle, padding: '48px 24px', textAlign: 'center' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%', margin: '0 auto 16px',
              background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Trophy size={26} style={{ color: '#fbbf24' }} />
            </div>
            <h2 style={{ margin: '0 0 8px', fontSize: 20 }}>
              {items.length === 0 ? 'Your cabinet is empty' : 'Nothing here yet'}
            </h2>
            <p style={{ margin: '0 0 20px', color: 'rgba(255,255,255,0.5)', fontSize: 14, lineHeight: 1.55 }}>
              {items.length === 0
                ? 'Add your first certificate, project, or award to start building your trophy cabinet.'
                : 'No achievements of this type yet. Try another filter or add one.'}
            </p>
            <button
              onClick={openAdd}
              style={{
                background: '#fff', color: '#000', border: 'none', borderRadius: 8,
                padding: '11px 18px', fontWeight: 700, cursor: 'pointer',
                display: 'inline-flex', alignItems: 'center', gap: 8,
              }}
            >
              <Plus size={16} /> Add achievement
            </button>
          </section>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
            {visible.map((it) => {
              const meta = TYPES[it.type] || TYPES.other;
              const Icon = meta.icon;
              return (
                <div key={it.id} style={{ ...panelStyle, padding: 18, display: 'flex', flexDirection: 'column', gap: 10, position: 'relative' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      background: 'rgba(255,255,255,0.05)', border: `1px solid ${meta.color}44`,
                      color: meta.color, borderRadius: 999, padding: '4px 10px', fontSize: 11, fontWeight: 700,
                      textTransform: 'uppercase', letterSpacing: 0.5,
                    }}>
                      <Icon size={12} /> {meta.label}
                    </span>
                    <button
                      onClick={() => removeAchievement(it.id)}
                      disabled={deletingId === it.id}
                      title="Remove"
                      style={{
                        background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)',
                        cursor: 'pointer', padding: 4, display: 'flex',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = '#f87171'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.3)'; }}
                    >
                      {deletingId === it.id
                        ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                        : <Trash2 size={14} />}
                    </button>
                  </div>

                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, lineHeight: 1.35 }}>{it.title}</h3>

                  {(it.organization || it.date_achieved) && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>
                      {it.organization && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                          <Building2 size={12} /> {it.organization}
                        </span>
                      )}
                      {it.date_achieved && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                          <CalendarIcon size={12} /> {it.date_achieved}
                        </span>
                      )}
                    </div>
                  )}

                  {it.description && (
                    <p style={{ margin: 0, color: 'rgba(255,255,255,0.6)', fontSize: 13, lineHeight: 1.55 }}>{it.description}</p>
                  )}

                  {it.url && (
                    <a
                      href={it.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#fff', fontSize: 13, textDecoration: 'underline', marginTop: 'auto' }}
                    >
                      <ExternalLink size={13} /> View credential
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add modal */}
      {modalOpen && (
        <>
          <div onClick={() => !saving && setModalOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 80 }} />
          <div style={{
            position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', zIndex: 81,
            background: '#0b0b0b', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 14,
            padding: 26, width: 'min(94vw, 480px)', maxHeight: '88vh', overflowY: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h2 style={{ margin: 0, fontSize: 19, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <Award size={18} style={{ color: '#fbbf24' }} /> Add achievement
              </h2>
              <button onClick={() => !saving && setModalOpen(false)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', padding: 4, display: 'flex' }}>
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
                        onClick={() => setForm((f) => ({ ...f, type: key }))}
                        style={{
                          display: 'inline-flex', alignItems: 'center', gap: 6,
                          background: active ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${active ? meta.color + '88' : 'rgba(255,255,255,0.12)'}`,
                          color: active ? '#fff' : 'rgba(255,255,255,0.6)',
                          borderRadius: 8, padding: '8px 12px', fontSize: 13, cursor: 'pointer', fontWeight: 600,
                        }}
                      >
                        <Icon size={13} style={{ color: meta.color }} /> {meta.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label style={labelStyle}>Title <span style={{ color: '#f87171' }}>*</span></label>
                <input value={form.title} onChange={setField('title')} placeholder="e.g. AWS Certified Cloud Practitioner" style={inputStyle} autoFocus />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Organization</label>
                  <input value={form.organization} onChange={setField('organization')} placeholder="e.g. Amazon, Coursera" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Date</label>
                  <input value={form.date_achieved} onChange={setField('date_achieved')} placeholder="e.g. Jun 2025" style={inputStyle} />
                </div>
              </div>

              <div>
                <label style={labelStyle}>Link (optional)</label>
                <input value={form.url} onChange={setField('url')} placeholder="https://..." style={inputStyle} />
              </div>

              <div>
                <label style={labelStyle}>Description (optional)</label>
                <textarea value={form.description} onChange={setField('description')} placeholder="What did you build or learn? Why does it matter?" rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 20 }}>
              <button onClick={() => setModalOpen(false)} disabled={saving} style={{ background: 'none', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 8, padding: '9px 16px', color: 'rgba(255,255,255,0.6)', fontSize: 13, cursor: 'pointer' }}>
                Cancel
              </button>
              <button onClick={saveAchievement} disabled={saving} style={{ background: '#fff', color: '#000', border: 'none', borderRadius: 8, padding: '9px 18px', fontWeight: 700, fontSize: 13, cursor: saving ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                {saving ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={14} />}
                Add to cabinet
              </button>
            </div>
          </div>
        </>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </main>
  );
}

const labelStyle = {
  display: 'block',
  fontSize: 12,
  color: 'rgba(255,255,255,0.5)',
  marginBottom: 6,
  fontWeight: 600,
};

const inputStyle = {
  width: '100%',
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.14)',
  borderRadius: 8,
  padding: '10px 12px',
  color: '#fff',
  fontSize: 14,
  outline: 'none',
  boxSizing: 'border-box',
};
