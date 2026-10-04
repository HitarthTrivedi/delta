import React from 'react';
import LegalDocument from '../components/LegalDocument';

// Source of truth: frontend/public/legal/privacy-policy.md
export default function PrivacyPolicy() {
  return <LegalDocument src="/legal/privacy-policy.md" />;
}
