import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2, Download, Eye, EyeOff, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { privacyAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const GRIEVANCE_EMAIL = 'hitartht318@gmail.com';

const PURPOSE_LABEL = {
  terms_privacy: 'Terms of Use & Privacy Policy',
  recruiter_visibility: 'Visible to recruiters',
  recruiter_terms: 'Recruiter terms',
  parental_consent: 'Parental consent (Delta for School)',
  account_deleted: 'Account deleted',
};

const SHARED = [
  'Your name',
  'Education: institution, field of study, year',
  'For working professionals: current job, industry and years of experience',
  'Target role',
  'Skills and their levels',
  'Practice results: technical test, coding and mock-interview scores, with a per-skill breakdown',
  'Your email, plus any LinkedIn / GitHub / portfolio links you added, so recruiters can contact you',
];
const NOT_SHARED = [
  'Your conversations with Delta\'s AI',
  'Your personal introduction and backstory',
  'Résumé text, weekly plans, progress notes, phone number, GPA',
];

const sectionClass = 'bg-paper border border-rule p-5 sm:p-6 mb-5';
const h2Class = 'font-display text-[22px] font-semibold text-ink m-0 mb-2';
const pClass = 'text-ink-soft text-[14px] leading-relaxed m-0';
const btnClass = 'inline-flex items-center gap-2 px-4 py-2.5 border font-mono text-[11px] uppercase tracking-[0.12em] transition-colors';

export default function PrivacySettings() {
  const userId = useAuthStore((state) => state.userId);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [consent, setConsent] = useState(null);
  const [views, setViews] = useState([]);
  const [optInChecked, setOptInChecked] = useState(false);
  const [busy, setBusy] = useState('');
  const [deleteText, setDeleteText] = useState('');

  useEffect(() => {
    if (!userId) return;
    privacyAPI.getConsent(userId).then(setConsent).catch(() => toast.error('Could not load your privacy settings.'));
    privacyAPI.getProfileViews(userId).then((d) => setViews(d.views || [])).catch(() => {});
  }, [userId]);

  const setVisibility = async (granted) => {
    setBusy('visibility');
    try {
      const next = await privacyAPI.setConsent(userId, { purpose: 'recruiter_visibility', granted });
      setConsent(next);
      queryClient.setQueryData(['consent', userId], next);
      setOptInChecked(false);
      toast.success(granted ? 'Recruiters can now find you.' : 'You are now hidden from recruiters.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update this setting.');
    } finally {
      setBusy('');
    }
  };

  const setReminders = async (granted) => {
    setBusy('reminders');
    try {
      const next = await privacyAPI.setConsent(userId, { purpose: 'learning_reminders', granted });
      setConsent(next);
      queryClient.invalidateQueries({ queryKey: ['engagement', userId] });
      toast.success(granted ? 'Study reminders on.' : 'Study reminders off.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not update this setting.');
    } finally {
      setBusy('');
    }
  };

  const downloadData = async () => {
    setBusy('export');
    try {
      const data = await privacyAPI.exportData(userId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `delta-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Could not export your data. Try again.');
    } finally {
      setBusy('');
    }
  };

  const deleteAccount = async () => {
    setBusy('delete');
    try {
      const res = await privacyAPI.deleteAccount(userId);
      if (!res.login_removed) {
        toast.message(`Your data is deleted. To also remove your login, email ${GRIEVANCE_EMAIL}.`);
      } else {
        toast.success('Your account and data have been deleted.');
      }
      queryClient.clear();
      await logout();
      navigate('/');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not delete your account. Try again.');
      setBusy('');
    }
  };

  if (!consent) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />
      </div>
    );
  }

  const visible = consent.recruiter_visible;

  return (
    <main className="min-h-screen bg-bone text-ink px-4 pt-24 pb-16">
      <div className="max-w-[760px] mx-auto">
        <header className="mb-8">
          <p className="kicker mb-3">Privacy settings</p>
          <h1 className="font-display text-[clamp(2rem,5vw,2.8rem)] font-semibold text-oxblood leading-tight m-0">Your data, your call.</h1>
          <p className={`${pClass} mt-3 text-[15px]`}>
            Choose who sees you, take a copy of everything we hold, or delete it all. Changes take effect immediately.
          </p>
        </header>

        {/* Recruiter visibility */}
        <section className={sectionClass}>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className={h2Class}>Visible to recruiters</h2>
              <p className={pClass}>
                {visible
                  ? 'You are visible. Approved recruiters can find you in search and open your profile.'
                  : 'You are hidden. No recruiter can see you.'}
              </p>
            </div>
            <span className={`font-mono text-[11px] uppercase tracking-[0.12em] px-2.5 py-1 border ${visible ? 'text-oxblood border-oxblood' : 'text-ink-soft border-rule'}`}>
              {visible ? 'On' : 'Off'}
            </span>
          </div>

          <div className="grid sm:grid-cols-2 gap-5 mt-5">
            <div>
              <p className="text-[13px] font-semibold text-ink m-0 mb-2">Recruiters see</p>
              <ul className="m-0 pl-5 text-[13.5px] text-ink-soft leading-relaxed">{SHARED.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
            <div>
              <p className="text-[13px] font-semibold text-ink m-0 mb-2">Recruiters never see</p>
              <ul className="m-0 pl-5 text-[13.5px] text-ink-soft leading-relaxed">{NOT_SHARED.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
          </div>

          <div className="mt-5 pt-5 border-t border-rule">
            {visible ? (
              <button
                onClick={() => setVisibility(false)}
                disabled={busy === 'visibility'}
                className={`${btnClass} border-ink text-ink bg-transparent cursor-pointer hover:border-oxblood hover:text-oxblood`}
              >
                {busy === 'visibility' ? <Loader2 size={14} className="animate-spin" /> : <EyeOff size={14} />} Hide me from recruiters
              </button>
            ) : (
              <>
                <label className="flex items-start gap-3 cursor-pointer text-[14px] leading-relaxed text-ink mb-4">
                  <input
                    type="checkbox"
                    checked={optInChecked}
                    onChange={() => setOptInChecked((v) => !v)}
                    className="mt-1 w-[17px] h-[17px] shrink-0 cursor-pointer accent-[var(--oxblood)]"
                  />
                  <span>
                    I consent to Delta sharing the details listed under "Recruiters see" with recruiters that Delta has verified,
                    so they can consider me for jobs. I can withdraw this any time.
                  </span>
                </label>
                <button
                  onClick={() => setVisibility(true)}
                  disabled={!optInChecked || busy === 'visibility'}
                  className={`${btnClass} ${optInChecked ? 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}
                >
                  {busy === 'visibility' ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />} Make me visible
                </button>
              </>
            )}
          </div>
        </section>

        {/* Study reminders (opt-in) */}
        <section className={sectionClass}>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h2 className={h2Class}>Study reminders</h2>
              <p className={pClass}>
                {consent.learning_reminders
                  ? 'On. At most one reminder a day, at your study time, only on days you have not studied yet.'
                  : 'Off. Delta will not send you study reminders.'}
              </p>
            </div>
            <button
              onClick={() => setReminders(!consent.learning_reminders)}
              disabled={busy === 'reminders'}
              className={`${btnClass} border-ink text-ink bg-transparent cursor-pointer hover:border-oxblood hover:text-oxblood`}
            >
              {busy === 'reminders' ? <Loader2 size={14} className="animate-spin" /> : null}
              {consent.learning_reminders ? 'Turn off' : 'Turn on'}
            </button>
          </div>
        </section>

        {/* Profile views */}
        <section className={sectionClass}>
          <h2 className={h2Class}>Who viewed your profile</h2>
          {views.length === 0 ? (
            <p className={pClass}>No recruiter has opened your profile yet.</p>
          ) : (
            <ul className="m-0 p-0 list-none grid gap-2">
              {views.map((v, i) => (
                <li key={i} className="flex justify-between gap-4 text-[14px] border-b border-rule last:border-0 pb-2">
                  <span className="text-ink">{v.company || 'A recruiter'}</span>
                  <span className="text-ink-soft font-mono text-[12px]">{v.viewed_at ? new Date(v.viewed_at + 'Z').toLocaleString() : ''}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Export */}
        <section className={sectionClass}>
          <h2 className={h2Class}>Download your data</h2>
          <p className={`${pClass} mb-4`}>A copy of everything Delta stores about you (profile, skills, plans, conversations, practice results, consent history), as a JSON file.</p>
          <button
            onClick={downloadData}
            disabled={busy === 'export'}
            className={`${btnClass} border-ink text-ink bg-transparent cursor-pointer hover:border-oxblood hover:text-oxblood`}
          >
            {busy === 'export' ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} Download my data
          </button>
          <p className={`${pClass} mt-4 text-[13px]`}>
            To correct your details, edit them on the <a href="/intake" className="text-oxblood underline">Intake</a> page, or email us.
          </p>
        </section>

        {/* Consent history */}
        <section className={sectionClass}>
          <h2 className={h2Class}>Consent history</h2>
          <ul className="m-0 p-0 list-none grid gap-2">
            {consent.history.map((h, i) => (
              <li key={i} className="flex justify-between gap-4 text-[13.5px] border-b border-rule last:border-0 pb-2">
                <span className="text-ink">{PURPOSE_LABEL[h.purpose] || h.purpose} · <span className="text-ink-soft">{h.action}</span></span>
                <span className="text-ink-soft font-mono text-[12px]">{h.at ? new Date(h.at + 'Z').toLocaleString() : ''}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Delete */}
        <section className={`${sectionClass} border-oxblood/40`}>
          <h2 className={h2Class}>Delete account &amp; withdraw consent</h2>
          <p className={`${pClass} mb-4`}>
            This permanently erases your profile, plans, conversations, skills and practice results, and stops all processing.
            It can't be undone. We keep only a minimal record (account ID, consent dates) as proof of consent, as the law requires.
          </p>
          <label className="block text-[13px] text-ink mb-2" htmlFor="delete-confirm">Type <strong>DELETE</strong> to confirm</label>
          <div className="flex gap-3 flex-wrap">
            <input
              id="delete-confirm"
              value={deleteText}
              onChange={(e) => setDeleteText(e.target.value)}
              className="flex-1 min-w-[160px] bg-bone border border-rule px-3 py-2.5 text-ink text-sm outline-none focus:border-oxblood"
              autoComplete="off"
            />
            <button
              onClick={deleteAccount}
              disabled={deleteText !== 'DELETE' || busy === 'delete'}
              className={`${btnClass} ${deleteText === 'DELETE' ? 'bg-oxblood text-bone border-oxblood cursor-pointer' : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'}`}
            >
              {busy === 'delete' ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />} Delete everything
            </button>
          </div>
        </section>

        <p className={`${pClass} text-[13px]`}>
          Questions or complaints? Contact our Grievance Officer at{' '}
          <a href={`mailto:${GRIEVANCE_EMAIL}`} className="text-oxblood underline">{GRIEVANCE_EMAIL}</a>. If you're not satisfied with our
          response, you can complain to the Data Protection Board of India. Read the full <a href="/privacy" className="text-oxblood underline">Privacy Policy</a>.
        </p>
      </div>
    </main>
  );
}
