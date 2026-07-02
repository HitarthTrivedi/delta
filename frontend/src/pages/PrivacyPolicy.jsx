import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const section = { marginBottom: 36 };
const h2 = { color: 'var(--oxblood)', fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 22, fontWeight: 600, marginBottom: 10, marginTop: 0 };
const h3 = { color: 'var(--ink)', fontSize: 15, fontWeight: 600, marginBottom: 6, marginTop: 18 };
const p = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, margin: '0 0 12px' };
const ul = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, paddingLeft: 22, margin: '0 0 12px' };
const strong = { color: 'var(--ink)' };
const link = { color: 'var(--oxblood)' };

export default function PrivacyPolicy() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bone)', fontFamily: "'Manrope', sans-serif", color: 'var(--ink)' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '6rem 1.5rem 4rem' }}>

        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none',
            border: 'none', color: 'var(--ink-soft)', cursor: 'pointer',
            fontSize: 14, marginBottom: 40, padding: 0,
          }}
        >
          <ArrowLeft size={15} /> Back
        </button>

        <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", color: 'var(--oxblood)', fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 600, marginBottom: 8 }}>Privacy Policy</h1>
        <p style={{ ...p, marginBottom: 8 }}>Last updated: July 2, 2026</p>
        <p style={{ ...p, marginBottom: 40 }}>
          This Privacy Policy is drafted to comply with India&apos;s Digital Personal Data Protection Act, 2023
          (the &ldquo;DPDP Act&rdquo;) and, to the extent applicable, the Information Technology Act, 2000 and the
          SPDI Rules, 2011.
        </p>

        <div style={section}>
          <h2 style={h2}>1. Who we are (the Data Fiduciary)</h2>
          <p style={p}>
            Delta (branded &ldquo;Delta by Alpha.Kore&rdquo;, &ldquo;Delta&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) is an AI-powered
            career-planning web application, currently operated as an early-stage, non-commercial project by an
            individual, Mr. Hitarth Trivedi (&ldquo;the Operator&rdquo;), who is the Data Fiduciary responsible for your
            personal data under the DPDP Act.
          </p>
          <ul style={ul}>
            <li><strong style={strong}>Data Fiduciary / Operator</strong> — Hitarth Trivedi</li>
            <li><strong style={strong}>Contact &amp; Grievance Officer</strong> — <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a></li>
            <li><strong style={strong}>Country of operation</strong> — India</li>
          </ul>
          <p style={p}>
            A &ldquo;Data Principal&rdquo; is you — the individual whose personal data we process. A &ldquo;Data Processor&rdquo;
            is a third party that processes personal data on our behalf (listed in Section 6).
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>2. Scope</h2>
          <p style={p}>
            This Policy applies when you create an account, complete onboarding, chat with our AI agents (Agent 1 —
            onboarding, and Agent 2 — weekly planning), upload a résumé, add achievements, set opportunity
            preferences, use the roadmap, weekly plan, résumé, opportunities, calendar and other features, or visit
            our website. It does not apply to third-party sites we link to (for example, LinkedIn job pages you open
            from the Opportunities board), which have their own policies.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>3. What personal data we collect</h2>
          <p style={p}>We collect only the data needed to provide and personalise the service:</p>

          <h3 style={h3}>Account &amp; identity</h3>
          <p style={p}>
            Name, email address, and a unique user ID. Authentication is handled by Supabase; we do not store your raw
            password. If you sign in with Google, we receive basic profile information (name, email).
          </p>

          <h3 style={h3}>Contact &amp; profile links</h3>
          <p style={p}>Phone number, and LinkedIn / GitHub / portfolio URLs, where you provide them.</p>

          <h3 style={h3}>Education &amp; academic</h3>
          <p style={p}>
            Institution/university, major, year of study, GPA, education or life stage, and any target exams and exam
            dates you share.
          </p>

          <h3 style={h3}>Professional &amp; career</h3>
          <p style={p}>
            Current and target role(s), years of experience and experience level, past-experience descriptions, skills
            and their depth, projects, certificates, achievements (your &ldquo;Trophy Cabinet&rdquo;), and target industries.
          </p>

          <h3 style={h3}>Résumé data</h3>
          <p style={p}>
            Text and structured details extracted from résumé files (PDF/DOCX) you upload. We do not retain the
            original uploaded file after extraction — only the extracted text and structured data.
          </p>

          <h3 style={h3}>Preferences &amp; constraints</h3>
          <p style={p}>
            Hours available per week, learning style, preferred content types, location and relocation openness, and
            opportunity preferences (location, role types, work mode, industries, notes).
          </p>

          <h3 style={h3}>Conversations</h3>
          <p style={p}>
            Messages you exchange with Agent 1 and Agent 2, your personal introduction/backstory and transition
            reasons, and notes derived from those conversations, stored to give continuity and personalise your plan.
          </p>

          <h3 style={h3}>Activity &amp; derived data</h3>
          <p style={p}>
            Task completions, journey/progress events (which may include self-reported mood and AI planning
            decisions), Delta Score history, weekly briefs, roadmaps, market snapshots, and internal memory records
            derived from the above.
          </p>

          <h3 style={h3}>Technical &amp; usage data</h3>
          <p style={p}>
            A session token in your browser&apos;s local storage, functional cookies/local storage to keep you signed
            in, and standard server/CDN logs (such as IP address and request metadata) via our hosting and database
            providers.
          </p>

          <h3 style={h3}>Data we do not intentionally collect</h3>
          <p style={p}>
            We do not intentionally collect financial, health, biometric, or other specially sensitive data. Please do
            not enter such information into free-text fields or chats; if you do, contact us to have it removed.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>4. Why we process your data &amp; legal basis</h2>
          <p style={p}>
            We process your personal data on the basis of your consent, which you give by accepting this Policy and by
            voluntarily providing information as you use Delta. We use your data to:
          </p>
          <ul style={ul}>
            <li>build and refine your personalised career roadmap and weekly plan;</li>
            <li>power the AI agents that answer questions, adapt your plan, generate briefs, match opportunities, and analyse your résumé;</li>
            <li>track your progress, journey history and Delta Score;</li>
            <li>send daily task-reminder emails (if enabled) and important account notices;</li>
            <li>authenticate you, prevent unauthorised access to other users&apos; data, and secure the service; and</li>
            <li>improve Delta — in aggregated and de-identified form wherever feasible.</li>
          </ul>
          <p style={p}>
            We follow purpose limitation and data minimisation. <strong style={strong}>We do not sell your personal
            data, and we do not use it — or allow our AI provider to use it — to train third-party AI models.</strong>
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>5. How the AI processing works</h2>
          <p style={p}>
            Delta uses large language models (currently Google Gemini) to generate roadmaps, chat replies, résumé
            analysis and opportunity suggestions. To do this, relevant parts of your profile, your chat messages, and
            (for résumé features) your résumé text are sent to Google&apos;s Gemini API to generate a response.
            AI-generated content can be inaccurate, outdated or incomplete — always verify important information such
            as deadlines, eligibility and salary data from authoritative sources.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>6. Who we share data with (sub-processors)</h2>
          <p style={p}>
            We share personal data only with the service providers needed to run Delta. Each acts as our Data
            Processor and may use the data only to provide their service to us:
          </p>
          <ul style={ul}>
            <li><strong style={strong}>Supabase</strong> — authentication and database (PostgreSQL) hosting; stores your account and profile/app data.</li>
            <li><strong style={strong}>Google (Gemini API)</strong> — AI generation; receives profile context, chat messages, résumé text and prompts.</li>
            <li><strong style={strong}>Google (Gmail SMTP)</strong> — sends daily reminder emails; receives your email and pending-task titles.</li>
            <li><strong style={strong}>Tavily / Serper</strong> — web search for market signals; receives search queries (which may be derived from your profile).</li>
            <li><strong style={strong}>Vercel &amp; Render</strong> — frontend and backend hosting; standard request/CDN logs.</li>
            <li><strong style={strong}>Redis provider</strong> (if configured) — caches market/search results; no personalised generative content.</li>
          </ul>
          <p style={p}>
            Market/opportunity data sources (GitHub, StackExchange, job boards, coding/hackathon platforms) are queried
            for public, role-level information and do not receive your personal data. Job-search deeplinks (e.g. to
            LinkedIn) are URLs you click; we do not transmit your data to those sites. We may disclose data if required
            by law or to protect the rights and safety of Delta and its users. We do not sell your personal data.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>7. International transfer</h2>
          <p style={p}>
            Some sub-processors (including Google, Supabase, Vercel and Render) store or process data on servers
            outside India. By using Delta you acknowledge this transfer. Under Section 16 of the DPDP Act,
            cross-border transfer is permitted except to countries restricted by the Central Government; we will not
            transfer personal data to any such restricted country.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>8. Children&apos;s data</h2>
          <p style={p}>
            Under the DPDP Act, a &ldquo;child&rdquo; is anyone under 18 years of age.
          </p>
          <ul style={ul}>
            <li>If you are under 18, you may use Delta only with the verifiable consent of your parent or legal guardian, who must provide and manage that consent.</li>
            <li>We do not undertake tracking, behavioural monitoring, or targeted advertising directed at children, and will not knowingly process a child&apos;s data in a way likely to harm their well-being.</li>
            <li>If we learn we collected a child&apos;s data without the required verifiable parental/guardian consent, we will delete it promptly.</li>
            <li>A parent or guardian may contact us to review, correct, delete, or withdraw consent for their child&apos;s data.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>9. Data retention</h2>
          <p style={p}>
            We retain your personal data for as long as your account is active and as needed for the purposes above.
            When you delete your account, withdraw consent, or the data is no longer necessary, we erase it — unless
            retention is required to comply with a legal obligation or to defend legal claims. Backups and logs may
            persist for a limited period and are overwritten on normal cycles. De-identified data may be retained for
            analytics.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>10. How we protect your data</h2>
          <ul style={ul}>
            <li>Authentication via Supabase-issued JWTs, verified server-side.</li>
            <li>Ownership checks on every user-scoped request so one user cannot access another&apos;s data.</li>
            <li>Encryption in transit (HTTPS/TLS) between your browser, our backend, and our providers.</li>
            <li>Rate limiting on sensitive endpoints and input validation on writes.</li>
            <li>Access to production data limited to the Operator.</li>
          </ul>
          <p style={p}>
            No method of transmission or storage is 100% secure, and we cannot guarantee absolute security. You are
            responsible for keeping your login credentials confidential.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>11. Personal data breach</h2>
          <p style={p}>
            If a personal data breach occurs, we will take reasonable steps to contain and assess it and, in
            accordance with the DPDP Act, notify the Data Protection Board of India and each affected Data Principal
            within the timelines prescribed by law.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>12. Your rights as a Data Principal</h2>
          <ul style={ul}>
            <li><strong style={strong}>Access</strong> — a summary of the data we hold about you and who it has been shared with.</li>
            <li><strong style={strong}>Correction &amp; completion</strong> — correct, complete or update your data (much of it is editable via the Intake/Profile pages).</li>
            <li><strong style={strong}>Erasure</strong> — request deletion of your data and account, subject to legal-retention exceptions.</li>
            <li><strong style={strong}>Withdraw consent</strong> — at any time, as easily as you gave it (this may limit or end the service).</li>
            <li><strong style={strong}>Grievance redressal</strong> — raise a grievance and receive a response.</li>
            <li><strong style={strong}>Nominate</strong> — nominate someone to exercise your rights in the event of death or incapacity.</li>
            <li><strong style={strong}>Export</strong> — request a copy of your profile data.</li>
          </ul>
          <p style={p}>
            To exercise any right, email <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a> from
            your registered email. We respond within the timelines required by law after verifying your identity.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>13. Grievance redressal</h2>
          <p style={p}>
            For any concern about how we handle your personal data, contact our Grievance Officer, Mr. Hitarth Trivedi,
            at <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a>. If you are not satisfied
            with our response, you have the right to lodge a complaint with the Data Protection Board of India.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>14. Your duties</h2>
          <p style={p}>
            Under Section 15 of the DPDP Act, you agree to provide authentic information, not impersonate another
            person, not suppress material information where legally required, and not raise false or frivolous
            grievances.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>15. Cookies &amp; local storage</h2>
          <p style={p}>
            Delta uses only functional cookies/local storage needed to keep you signed in and remember your session and
            in-app preferences. We do not use advertising or third-party tracking cookies.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>16. Changes to this Policy</h2>
          <p style={p}>
            We may update this Policy from time to time. If we make material changes, we will update the
            &ldquo;Last updated&rdquo; date and, where appropriate, notify you by email or an in-app notice. Continued use
            of Delta after changes take effect constitutes acceptance.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>17. Contact</h2>
          <p style={p}>
            For any privacy question, rights request, or grievance, email us at{' '}
            <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a>.
          </p>
        </div>

      </div>
    </div>
  );
}
