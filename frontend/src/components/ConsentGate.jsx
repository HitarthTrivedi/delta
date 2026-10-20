import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { privacyAPI } from '../lib/api';
import { useAuthStore } from '../store/authStore';

const GRIEVANCE_EMAIL = 'hitartht318@gmail.com';

/**
 * Blocks the student app until the signed-in user has given explicit,
 * recorded consent (DPDP Act §6) to the CURRENT Terms + Privacy Policy and
 * confirmed they are 18+. Re-appears whenever the policy version changes.
 * Recruiter accounts are sent to the recruiter portal instead.
 */
export default function ConsentGate({ children }) {
  const userId = useAuthStore((state) => state.userId);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['consent', userId],
    queryFn: () => privacyAPI.getConsent(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bone flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-bone flex flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-ink-soft text-sm">We couldn't check your privacy settings. Please try again.</p>
        <button onClick={() => refetch()} className="px-5 py-2.5 border border-ink text-ink font-mono text-xs uppercase tracking-[0.12em] bg-transparent cursor-pointer">
          Retry
        </button>
      </div>
    );
  }

  if (data.is_recruiter) return <Navigate to="/recruiter" replace />;
  if (!data.terms_accepted) return <ConsentScreen consent={data} />;
  return children;
}

function ConsentScreen({ consent }) {
  const userId = useAuthStore((state) => state.userId);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [checks, setChecks] = useState({ age: false, terms: false, privacy: false });
  const [saving, setSaving] = useState(false);

  const isUpdate = !!consent.terms_accepted_version;
  const allChecked = checks.age && checks.terms && checks.privacy;

  const accept = async () => {
    setSaving(true);
    try {
      const next = await privacyAPI.setConsent(userId, {
        purpose: 'terms_privacy',
        granted: true,
        policy_version: consent.current_policy_version,
        age_confirmed: checks.age,
      });
      queryClient.setQueryData(['consent', userId], next);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Could not save your consent. Try again.');
    } finally {
      setSaving(false);
    }
  };

  const signOut = async () => {
    await logout();
    navigate('/login');
  };

  const toggle = (key) => setChecks((c) => ({ ...c, [key]: !c[key] }));

  return (
    <main className="min-h-screen bg-bone text-ink px-4 py-16 sm:py-20">
      <div className="max-w-[640px] mx-auto">
        <p className="kicker mb-3">{isUpdate ? 'Our terms have changed' : 'Before you start'}</p>
        <h1 className="font-display text-[clamp(2rem,5vw,2.6rem)] font-semibold text-oxblood leading-tight m-0">
          {isUpdate ? 'Please review the updated terms' : 'Your data, in plain words'}
        </h1>
        <p className="text-ink-soft text-[15px] leading-relaxed mt-3 mb-8">
          Delta needs your permission before it can build your plan. Here's the short version. The full{' '}
          <a href="/terms" target="_blank" rel="noreferrer" className="text-oxblood underline">Terms of Use</a> and{' '}
          <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a> have every detail.
        </p>

        <section className="bg-paper border border-rule p-5 sm:p-6 mb-6">
          <dl className="m-0 grid gap-4 text-[14px] leading-relaxed">
            <div>
              <dt className="font-semibold text-ink">What we collect</dt>
              <dd className="m-0 text-ink-soft">Your name and email, education, goals and skills, what you tell Delta's AI, résumé text you upload, your tasks, and your practice-test results.</dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">Why</dt>
              <dd className="m-0 text-ink-soft">To build and adapt your roadmap, run the AI features, track your progress, and send reminders you've turned on. We don't sell your data or use it for ads.</dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">Who processes it</dt>
              <dd className="m-0 text-ink-soft">Our service providers (hosting, database, and AI models from Google and Groq), some of them outside India. They may only use it to run Delta for us.</dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">Recruiters</dt>
              <dd className="m-0 text-ink-soft">Recruiters can't see you. That only changes if you separately switch on visibility in Privacy settings, and you can switch it off any time.</dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">Your rights</dt>
              <dd className="m-0 text-ink-soft">
                Download, correct or delete your data, and withdraw consent, from Privacy settings at any time. Complaints go to our Grievance Officer at{' '}
                <a href={`mailto:${GRIEVANCE_EMAIL}`} className="text-oxblood underline">{GRIEVANCE_EMAIL}</a>
                , and if you're not satisfied, to the Data Protection Board of India.
              </dd>
            </div>
          </dl>
        </section>

        <fieldset className="border-0 p-0 m-0 grid gap-3 mb-7">
          <legend className="sr-only">Consent</legend>
          <Check checked={checks.age} onChange={() => toggle('age')}>
            I am 18 years of age or older.
          </Check>
          <Check checked={checks.terms} onChange={() => toggle('terms')}>
            I have read and agree to the{' '}
            <a href="/terms" target="_blank" rel="noreferrer" className="text-oxblood underline">Terms of Use</a>.
          </Check>
          <Check checked={checks.privacy} onChange={() => toggle('privacy')}>
            I have read the <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a> and
            consent to Delta processing my personal data for the purposes described in it.
          </Check>
        </fieldset>

        <button
          onClick={accept}
          disabled={!allChecked || saving}
          className={`w-full py-[13px] border font-mono text-xs uppercase tracking-[0.14em] flex items-center justify-center gap-2 transition-colors ${
            allChecked && !saving
              ? 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink'
              : 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'
          }`}
        >
          {saving && <Loader2 size={16} className="animate-spin" />}
          Agree and continue
        </button>

        <p className="text-[13px] text-ink-soft leading-relaxed mt-5 text-center">
          Under 18? You can't have your own account, but a parent can set up Delta for School for you from their account.{' '}
          <button onClick={signOut} className="text-oxblood underline bg-transparent border-0 p-0 cursor-pointer text-[13px]">Sign out</button>
        </p>
      </div>
    </main>
  );
}

function Check({ checked, onChange, children }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer text-[14px] leading-relaxed text-ink">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="mt-1 w-[17px] h-[17px] shrink-0 cursor-pointer accent-[var(--oxblood)]"
      />
      <span>{children}</span>
    </label>
  );
}
