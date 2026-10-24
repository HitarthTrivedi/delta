import React from 'react';
import LegalDocument from '../components/LegalDocument';

// Source of truth: frontend/public/legal/terms-of-use.md
export default function TermsOfService() {
  return <LegalDocument src="/legal/terms-of-use.md" />;
}
