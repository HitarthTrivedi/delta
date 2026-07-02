import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const section = { marginBottom: 36 };
const h2 = { color: 'var(--oxblood)', fontFamily: "'Cormorant Garamond', Georgia, serif", fontSize: 22, fontWeight: 600, marginBottom: 10, marginTop: 0 };
const p = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, margin: '0 0 12px' };
const ul = { color: 'var(--ink-soft)', fontSize: 15, lineHeight: 1.8, paddingLeft: 22, margin: '0 0 12px' };
const strong = { color: 'var(--ink)' };
const link = { color: 'var(--oxblood)' };

export default function TermsOfService() {
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

        <h1 style={{ fontFamily: "'Cormorant Garamond', Georgia, serif", color: 'var(--oxblood)', fontSize: 'clamp(2rem, 4vw, 2.8rem)', fontWeight: 600, marginBottom: 8 }}>Terms of Use</h1>
        <p style={{ ...p, marginBottom: 40 }}>Last updated: July 2, 2026</p>

        <div style={section}>
          <h2 style={h2}>1. Who we are &amp; acceptance</h2>
          <p style={p}>
            Delta (branded &ldquo;Delta by Alpha.Kore&rdquo;, &ldquo;Delta&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) is an AI-powered
            career-planning web application, currently operated as an early-stage, non-commercial project by an
            individual, Mr. Hitarth Trivedi (&ldquo;the Operator&rdquo;). By creating an account or using Delta, you agree
            to these Terms and to our <a href="/privacy" style={link}>Privacy Policy</a>. If you do not agree, do not
            use Delta.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>2. What Delta is — and is not</h2>
          <p style={p}>
            Delta helps students and early-career individuals build structured, personalised career roadmaps, weekly
            plans, résumés, and opportunity suggestions based on information you provide and on live market signals.
          </p>
          <p style={p}>
            <strong style={strong}>Delta is not a professional career counsellor, recruiter, placement agency, or
            educational institution, and does not provide legal, financial, or professional advice.</strong> Outputs
            from Delta&apos;s AI agents are suggestions, not guarantees. Career outcomes depend on your own effort,
            market conditions, and factors outside our control. We do not guarantee any job, internship, admission,
            salary, or other outcome.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>3. Eligibility &amp; accounts</h2>
          <ul style={ul}>
            <li><strong style={strong}>Age.</strong> You must be at least 18 to use Delta on your own. If you are under 18, you may use Delta only with the verifiable consent and supervision of your parent or legal guardian, who accepts these Terms on your behalf and is responsible for your use.</li>
            <li><strong style={strong}>Accurate information.</strong> You agree to provide accurate, current, and complete information and keep it updated.</li>
            <li><strong style={strong}>Account security.</strong> You are responsible for keeping your credentials secure and for all activity under your account, and must notify us of any unauthorised use.</li>
            <li><strong style={strong}>One account per person.</strong> You may maintain only one account, and must not create an account for another person without their knowledge and consent.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>4. Acceptable use</h2>
          <p style={p}>You agree not to:</p>
          <ul style={ul}>
            <li>use Delta to generate, store or share content that is unlawful, harmful, abusive, defamatory, obscene, infringing, or that violates any third party&apos;s rights;</li>
            <li>upload a résumé or document belonging to someone else without permission, or that infringes any third party&apos;s intellectual-property or privacy rights;</li>
            <li>reverse-engineer, decompile, scrape, overload, disrupt, or gain unauthorised access to Delta, its APIs, or other users&apos; data;</li>
            <li>circumvent authentication, rate limits, or other security measures;</li>
            <li>use Delta to build or train a competing product or dataset; or</li>
            <li>use Delta in violation of any applicable law.</li>
          </ul>
        </div>

        <div style={section}>
          <h2 style={h2}>5. Your content &amp; licence</h2>
          <p style={p}>
            You retain ownership of the information you provide — your profile, goals, achievements, résumé content,
            and conversations (&ldquo;Your Content&rdquo;). By using Delta, you grant us a limited, non-exclusive,
            royalty-free licence to host, store, process, transmit, and display Your Content solely to operate and
            provide the service to you (including sending relevant portions to our AI and infrastructure providers as
            described in the Privacy Policy). You represent that you have the rights to provide Your Content and that
            it does not infringe any third party&apos;s rights.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>6. AI-generated content</h2>
          <p style={p}>
            Delta uses large language models (currently Google Gemini) to generate responses, roadmaps, résumé
            suggestions, and opportunity matches. AI-generated content can be inaccurate, outdated, biased, or
            incomplete. You are responsible for reviewing and independently verifying any information — especially
            deadlines, eligibility, application requirements, and compensation — before relying on it. Delta is not
            liable for decisions you make based on AI-generated content.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>7. Intellectual property</h2>
          <p style={p}>
            Delta — including its software, design, branding, text, and features — is owned by the Operator and
            protected by applicable law. Except for your right to use the service, no rights are transferred to you.
            You may not copy, modify, distribute, sell, or lease any part of Delta without our prior written
            permission.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>8. Third-party services &amp; links</h2>
          <p style={p}>
            Delta relies on and links to third-party services (for example, Supabase, Google Gemini, and job-search
            sites such as LinkedIn reached via deeplinks). We are not responsible for the availability, content,
            accuracy, or practices of those third parties, and your use of them is governed by their own terms and
            privacy policies.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>9. Fees</h2>
          <p style={p}>
            Delta is currently offered free of charge as an early-access, non-commercial project. We may introduce
            paid features in the future; if we do, we will make the pricing and terms available before you are charged.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>10. Service availability &amp; changes</h2>
          <p style={p}>
            We aim to keep Delta available but do not guarantee uninterrupted or error-free access. The service may be
            unavailable due to maintenance, infrastructure issues, third-party outages, or events outside our control.
            We may add, modify, suspend, or discontinue features (or the service) at any time, including during this
            early-access period.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>11. Disclaimer of warranties</h2>
          <p style={p}>
            To the maximum extent permitted by law, Delta is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;,
            without warranties of any kind, express or implied, including implied warranties of merchantability,
            fitness for a particular purpose, accuracy, and non-infringement. We do not warrant that Delta will meet
            your requirements, be secure, or be free of errors or interruptions.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>12. Limitation of liability</h2>
          <p style={p}>
            To the maximum extent permitted by law, and given that Delta is provided free of charge as an early-stage
            project, the Operator will not be liable for any indirect, incidental, special, consequential, or punitive
            damages, or for any loss of profits, opportunities, data, or goodwill, arising out of or relating to your
            use of (or inability to use) Delta or reliance on AI-generated content. To the extent any liability cannot
            be excluded, it is limited to the greater of the amount you paid us (if any) in the preceding twelve months
            or INR 1,000. Nothing here excludes liability that cannot be excluded under applicable law.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>13. Indemnity</h2>
          <p style={p}>
            You agree to indemnify and hold harmless the Operator from any claims, damages, liabilities, and reasonable
            expenses arising out of your misuse of Delta, your violation of these Terms, or your infringement of any
            third party&apos;s rights (including uploading content you do not have the rights to).
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>14. Suspension &amp; termination</h2>
          <p style={p}>
            You may stop using Delta and delete your account at any time. We may suspend or terminate your access if
            you violate these Terms, if required by law, or to protect the service or other users. On termination, your
            right to use Delta ends; provisions that by their nature should survive will survive.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>15. Privacy</h2>
          <p style={p}>
            Your use of Delta is also governed by our <a href="/privacy" style={link}>Privacy Policy</a>, which
            explains how we collect, use, share, and protect your personal data in accordance with India&apos;s Digital
            Personal Data Protection Act, 2023.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>16. Governing law, jurisdiction &amp; grievances</h2>
          <p style={p}>
            These Terms are governed by the laws of India. Subject to any mandatory consumer-protection rights you may
            have, the courts at Ahmedabad, Gujarat, India shall have exclusive jurisdiction over any dispute relating
            to these Terms or your use of Delta. For any grievance relating to the service or content, contact our
            Grievance Officer, Mr. Hitarth Trivedi, at{' '}
            <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a>.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>17. Changes to these Terms</h2>
          <p style={p}>
            We may update these Terms from time to time. If we make material changes, we will update the
            &ldquo;Last updated&rdquo; date and, where appropriate, notify you by email. Continued use of Delta after
            changes take effect constitutes your acceptance of the updated Terms.
          </p>
        </div>

        <div style={section}>
          <h2 style={h2}>18. Contact</h2>
          <p style={p}>
            Questions about these Terms? Email us at{' '}
            <a href="mailto:hitartht318@gmail.com" style={link}>hitartht318@gmail.com</a>.
          </p>
        </div>

      </div>
    </div>
  );
}
