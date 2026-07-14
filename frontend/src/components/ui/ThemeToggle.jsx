import React, { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from 'next-themes';

export default function ThemeToggle({ className = '' }) {
  const { resolvedTheme, setTheme } = useTheme();
  // Theme is unknown until next-themes reads localStorage/media query on mount;
  // render a stable icon first to avoid a wrong-icon flash.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const isDark = mounted && resolvedTheme === 'dark';
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';

  return (
    <button
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      title={label}
      aria-label={label}
      className={`flex items-center justify-center bg-transparent border border-rule text-ink-soft hover:text-oxblood hover:border-oxblood transition-all cursor-pointer ${className}`}
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );
}
