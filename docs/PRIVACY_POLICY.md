# Privacy Policy — Delta ("Delta by Alpha.Kore")

**Last updated:** 2 July 2026
**Effective date:** 2 July 2026

---

> **About this document.** This Privacy Policy is drafted to comply with India's
> **Digital Personal Data Protection Act, 2023 ("DPDP Act")** and, to the extent
> currently applicable, the **Information Technology Act, 2000** and the
> **Information Technology (Reasonable Security Practices and Procedures and
> Sensitive Personal Data or Information) Rules, 2011 ("SPDI Rules")**. Where the
> DPDP Rules (the subordinate rules under the DPDP Act) come into force, we will
> update this Policy to align with them.
>
> **⚠️ Implementation notes for the operator (remove before publishing):**
> 1. **Children / verifiable consent.** You chose to allow users under 18 with
>    verifiable parental/guardian consent. Section 8 below reflects this, **but a
>    working consent-verification and parental-controls flow must actually be
>    built and operating** for this to be lawful under DPDP §9. Until it is live,
>    either restrict registration to 18+ or do not onboard minors.
> 2. **Fill the placeholders** marked `[…]` — correspondence address and any
>    registered-entity details if that changes.
> 3. **Keep in sync** with the live in-app page (`frontend/src/pages/PrivacyPolicy.jsx`).

---

## 1. Who we are (the Data Fiduciary)

Delta (branded **"Delta by Alpha.Kore"**, "Delta", "we", "us", "our") is an
AI-powered career-planning web application. Delta is currently operated as an
**early-stage, non-commercial project by an individual, Mr. Hitarth Trivedi**
("the Operator"), who is the **Data Fiduciary** responsible for your personal
data under the DPDP Act.

- **Data Fiduciary / Operator:** Hitarth Trivedi
- **Contact & Grievance Officer email:** hitartht318@gmail.com
- **Correspondence address:** [To be provided — available on written request to the email above]
- **Country of operation:** India

A **"Data Principal"** is you — the individual whose personal data we process.
A **"Data Processor"** is any third party that processes personal data on our
behalf (our sub-processors are listed in Section 6).

---

## 2. Scope of this Policy

This Policy applies to personal data we collect and process when you:

- create an account and sign in to Delta;
- complete onboarding / intake and build your career profile;
- chat with our AI agents (Agent 1 – onboarding, and Agent 2 – weekly planning);
- upload a résumé, add achievements, or set opportunity preferences;
- use the roadmap, weekly plan, resume, opportunities, calendar, dossier and
  other in-app features; and
- visit our public website.

It does **not** apply to third-party websites or services that Delta links to
(for example, LinkedIn job pages you open from the Opportunities board), which
have their own privacy policies.

---

## 3. What personal data we collect

We collect only the data needed to provide and improve the service. Because
Delta is a personalised career planner, some of this data is detailed by design.

### 3.1 Account & identity data
- Name and email address.
- A unique user identifier.
- Authentication is handled by **Supabase**; we do **not** store your raw
  password. If you sign in with Google, we receive basic profile information
  (name, email) from Google per your Google account settings.

### 3.2 Contact & profile links
- Phone number (if you provide it).
- LinkedIn, GitHub, and portfolio URLs (if you provide them).

### 3.3 Education & academic data
- Institution / university, major/field of study, year of study, GPA,
  education or life stage, and any target exams and exam dates you share.

### 3.4 Professional & career data
- Current role, target role(s), years of experience and experience level,
  past-experience descriptions, skills (and self-assessed depth), projects,
  certificates, achievements (your "Trophy Cabinet"), and target industries.

### 3.5 Résumé data
- Text and structured details **extracted** from résumé files (PDF/DOCX) you
  upload — including contact details, summary, skills, experience, projects and
  education. **We do not retain the original uploaded file** after extraction;
  we store only the extracted text and structured data.

### 3.6 Preferences & constraints
- Hours available per week, learning style, preferred content types, location
  and relocation openness, and opportunity preferences (location, role types,
  work mode, industries, free-text notes) and other personalisation settings.

### 3.7 Conversation data
- Messages you exchange with Agent 1 (onboarding) and Agent 2 (weekly planning),
  including your personal introduction/backstory and reasons for a career
  transition, and notes derived from those conversations. We store these to give
  continuity across sessions and to personalise your plan.

### 3.8 Activity & derived data
- Task completions, journey/progress events (which may include self-reported
  mood and AI planning decisions), your Delta Score history, weekly briefs,
  roadmaps, market snapshots generated for your role, and internal
  semantic-memory records derived from the above.

### 3.9 Technical & usage data
- A session token stored in your browser's local storage, functional cookies/
  local storage used to keep you logged in, and standard server/CDN logs (such
  as IP address and request metadata) generated by our hosting providers
  (Vercel, Render) and database provider (Supabase).

### 3.10 Data we do **not** intentionally collect
- We do not intentionally collect financial account data, health data, biometric
  data, or other specially sensitive categories. **Please do not enter such
  information into free-text fields or chats.** If you do, it will be processed
  as ordinary profile text; contact us to have it removed.

---

## 4. Why we process your data, and our legal basis

Under the DPDP Act we process personal data on the basis of your **consent**,
which you give by clicking to accept this Policy and by voluntarily providing
information as you use Delta. We process your data for the following purposes:

| Purpose | Examples |
|---------|----------|
| **Provide the core service** | Build and refine your personalised career roadmap and weekly plan; run the onboarding intake. |
| **Power the AI agents** | Answer your questions, adapt your plan, generate briefs, match opportunities, and analyse/improve your résumé. |
| **Track progress** | Maintain your journey history, Delta Score, and completed tasks. |
| **Communicate with you** | Send daily task-reminder emails (if enabled) and important account or service notices. |
| **Security & integrity** | Authenticate you, prevent unauthorised access to other users' data, rate-limit abuse, and debug issues. |
| **Improve Delta** | Understand feature usage and improve the product — **in aggregated and de-identified form** wherever feasible. |

We follow **purpose limitation** and **data minimisation**: we ask for and use
only what is reasonably necessary for these purposes.

**We do not sell your personal data. We do not use your personal data to train
third-party AI models, and we do not permit our AI provider to train its models
on your data through paid/API processing** (see Section 6).

---

## 5. How the AI processing works

Delta uses large language models (currently **Google Gemini**) to generate
roadmaps, chat replies, résumé analysis, and opportunity suggestions. To do
this, relevant parts of your profile, your chat messages, and (for résumé
features) your résumé text are sent to Google's Gemini API to generate a
response. This transfer is described in Section 6 and Section 7.

**AI outputs can be wrong.** AI-generated content may be inaccurate, outdated, or
incomplete. Always verify important information — deadlines, eligibility,
application requirements, and salary data — from authoritative sources. See our
[Terms of Use](./TERMS_OF_SERVICE.md).

---

## 6. Who we share data with (Data Processors / sub-processors)

We share personal data only with the service providers needed to operate Delta.
Each acts as our Data Processor under contract/terms and is permitted to use the
data only to provide their service to us:

| Sub-processor | Purpose | Data shared |
|---------------|---------|-------------|
| **Supabase** | Authentication and database (PostgreSQL) hosting | Your account and stored profile/app data |
| **Google (Gemini API)** | AI text generation | Profile context, chat messages, résumé text, and prompts sent for generation |
| **Google (Gmail SMTP)** | Sending daily reminder emails | Your email address and pending-task titles |
| **Tavily / Serper** | Web search for market signals and enrichment | Search queries (role/skill/market terms, which may be derived from your profile) |
| **Vercel** | Frontend/website hosting | Standard web/CDN request logs |
| **Render** | Backend API hosting | Standard server/request logs |
| **Redis provider** *(if configured)* | Caching of market/search/embedding results | Cache artifacts; not personalised generative content |

**Market/opportunity data sources** (GitHub, StackExchange, job boards, coding/
hackathon platforms) are queried for public, role-level market information and do
**not** receive your personal data. Job-search **deeplinks** (e.g., to LinkedIn)
are URLs you click; we do not transmit your personal data to those sites.

We may also disclose personal data if **required by law**, court order, or a
lawful request by a public authority, or to protect the rights, safety, and
security of Delta and its users.

---

## 7. International / cross-border transfer

Some of our sub-processors (including Google, Supabase, Vercel, and Render)
**store or process data on servers located outside India**. By using Delta and
consenting to this Policy, you acknowledge that your personal data may be
transferred to and processed in such countries.

Under Section 16 of the DPDP Act, cross-border transfer is permitted except to
countries or territories specifically restricted by the Central Government. We
will not transfer personal data to any country that has been so restricted, and
we take reasonable steps to ensure our processors provide an adequate level of
protection.

---

## 8. Children's data

Delta is intended for students and early-career individuals. Under the DPDP Act,
a **"child" is anyone under 18 years of age**.

- If you are **under 18**, you may use Delta **only** with the **verifiable
  consent of your parent or legal guardian**, and your parent/guardian must
  provide and manage that consent.
- We will **not undertake tracking, behavioural monitoring, or targeted
  advertising directed at children**, and we will not knowingly process a
  child's data in a way likely to cause a detrimental effect on their
  well-being.
- If we learn that we have collected a child's personal data without the
  required verifiable parental/guardian consent, we will delete it promptly.
- A parent or guardian may contact us at hitartht318@gmail.com to review,
  correct, or delete their child's data, or to withdraw consent.

> *Operator note:* to lawfully onboard minors, the verifiable-parental-consent
> mechanism referenced above must be implemented and operating.

---

## 9. Data retention

- We retain your personal data **for as long as your account is active** and for
  as long as needed to fulfil the purposes in Section 4.
- When you **delete your account**, **withdraw consent**, or when the data is no
  longer necessary for the purpose it was collected for, we will **erase** your
  personal data, unless retention is required to comply with a legal obligation
  or to establish, exercise, or defend legal claims.
- **Backups and logs** may persist for a limited period after deletion and are
  overwritten on our providers' normal cycles.
- Aggregated or de-identified data that can no longer identify you may be
  retained for analytics and product improvement.

---

## 10. How we protect your data (security safeguards)

We implement reasonable technical and organisational security measures
appropriate to the nature of the data, including:

- **Authentication** via Supabase-issued JWTs, verified server-side (symmetric
  and asymmetric/JWKS verification).
- **Authorisation / ownership checks** on every user-scoped API request so that
  one user cannot access another user's data (protection against broken
  object-level authorisation).
- **Encryption in transit** (HTTPS/TLS) between your browser, our backend, and
  our providers.
- **Rate limiting** on sensitive/expensive endpoints and input validation on
  write operations.
- **Access minimisation** — access to production data is limited to the Operator.

No method of transmission or storage is 100% secure, and we cannot guarantee
absolute security. You are responsible for keeping your login credentials
confidential.

---

## 11. Personal data breach

If a personal data breach occurs, we will take reasonable steps to contain and
assess it and, in accordance with the DPDP Act and applicable rules, **notify the
Data Protection Board of India and each affected Data Principal** of the breach,
including its nature and the measures we are taking, within the timelines
prescribed by law.

---

## 12. Your rights as a Data Principal

Subject to the DPDP Act, you have the right to:

1. **Access** — obtain a summary of the personal data we process about you and
   the processing activities, and the identities of sub-processors with whom it
   has been shared.
2. **Correction & completion** — have inaccurate or incomplete data corrected,
   completed, or updated (you can edit much of this yourself via the Intake/
   Profile pages).
3. **Erasure** — request deletion of your personal data and account, subject to
   legal-retention exceptions.
4. **Withdraw consent** — withdraw your consent at any time; withdrawing is as
   easy as giving it. Withdrawal does not affect processing done before
   withdrawal, and may mean we can no longer provide some or all of the service.
5. **Grievance redressal** — raise a grievance with our Grievance Officer
   (Section 13) and receive a response.
6. **Nominate** — nominate another individual to exercise your rights in the
   event of your death or incapacity.
7. **Data portability / export** — request a copy of your profile data in a
   commonly used format.

To exercise any of these rights, email **hitartht318@gmail.com** from your
registered email address. We will respond within the timelines required by
applicable law after reasonable verification of your identity.

---

## 13. Grievance redressal

If you have any concern or complaint about how we handle your personal data, you
may contact our **Grievance Officer**:

- **Grievance Officer:** Hitarth Trivedi
- **Email:** hitartht318@gmail.com

We will acknowledge and make reasonable efforts to resolve grievances within the
period prescribed under applicable law. If you are not satisfied with our
response, you have the right to lodge a complaint with the **Data Protection
Board of India**.

---

## 14. Your duties as a Data Principal

Under Section 15 of the DPDP Act, you agree to:

- provide **authentic and accurate** information and not impersonate another
  person when providing your personal data;
- not suppress material information where legally required; and
- not raise false or frivolous grievances or complaints.

---

## 15. Cookies & local storage

Delta uses only **functional** cookies/local storage necessary to keep you
signed in and to remember your session and in-app preferences. **We do not use
advertising or third-party tracking cookies.**

---

## 16. Changes to this Policy

We may update this Policy from time to time. If we make material changes, we will
update the "Last updated" date and, where appropriate, notify you via the email
on your account or an in-app notice. Your continued use of Delta after changes
take effect constitutes acceptance of the updated Policy.

---

## 17. Contact

For any privacy question, rights request, or grievance, contact us at
**hitartht318@gmail.com**.
