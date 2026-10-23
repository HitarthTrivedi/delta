import React from 'react';
import { Loader2 } from 'lucide-react';

// The one full-page loading state. Sign-in, consent, profile and page-code
// loading all show this same screen, so a chain of them reads as one short
// wait instead of several different flashing spinners.
export default function PageLoader() {
  return (
    <div className="min-h-screen bg-bone flex items-center justify-center" role="status" aria-label="Loading">
      <Loader2 className="w-6 h-6 animate-spin text-ink-soft" />
    </div>
  );
}
