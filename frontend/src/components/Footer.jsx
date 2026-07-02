import React from 'react';

const FooterLink = ({ href, children }) => (
  <a
    href={href}
    className="block text-ink-soft hover:text-oxblood no-underline text-[13px] leading-[2.1] transition-colors"
  >
    {children}
  </a>
);

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-bone text-ink-soft border-t border-rule px-6 pt-14 pb-8">
      <div
        className="max-w-[1120px] mx-auto grid gap-10 mb-10"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}
      >
        {/* Brand column */}
        <div className="min-w-[180px]">
          <div className="flex items-baseline gap-2 mb-3.5">
            <span className="font-display text-ink font-semibold text-xl">Delta</span>
            <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-soft">by Alpha.Kore</span>
          </div>
          <p className="text-ink-soft text-[13px] leading-relaxed m-0 max-w-[220px]">
            AI-powered career operating system for students.
          </p>
        </div>

        {/* Product */}
        <div>
          <p className="kicker mb-2.5">Product</p>
          <FooterLink href="#features">Features</FooterLink>
          <FooterLink href="#how-it-works">How It Works</FooterLink>
          <FooterLink href="/intake">Get Started</FooterLink>
          <FooterLink href="/#feedback">Feedback</FooterLink>
        </div>

        {/* Company */}
        <div>
          <p className="kicker mb-2.5">Company</p>
          <FooterLink href="/about">About</FooterLink>
          <FooterLink href="/careers">Careers</FooterLink>
          <FooterLink href="/contact">Contact</FooterLink>
          <FooterLink href="/partners">Partners</FooterLink>
          <FooterLink href="/investors">Investors</FooterLink>
        </div>

        {/* Legal */}
        <div>
          <p className="kicker mb-2.5">Legal</p>
          <FooterLink href="/privacy">Privacy Policy</FooterLink>
          <FooterLink href="/terms">Terms of Service</FooterLink>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="max-w-[1120px] mx-auto border-t border-rule pt-5 flex justify-between items-center flex-wrap gap-3">
        <p className="m-0 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft">
          &copy; {currentYear} Delta &middot; Alpha.Kore
        </p>
        <p className="m-0 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-soft/70">
          Made with purpose for students everywhere.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
