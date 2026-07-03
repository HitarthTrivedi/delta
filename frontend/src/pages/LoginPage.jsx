import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Loader2, Eye, EyeOff, Mail, Lock, User } from 'lucide-react';
import { toast } from 'sonner';
import supabase from '../lib/supabaseClient';

export default function LoginPage() {
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const { login, signUp, loginWithGoogle } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || (isSignUp && !name)) {
      toast.error('Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      localStorage.setItem('delta_remember_me', rememberMe ? 'true' : 'false');
      if (isSignUp) {
        await signUp(email, password, name);
        toast.success('Account created! Please sign in.');
        setIsSignUp(false);
        setEmail('');
        setPassword('');
        setName('');
      } else {
        await login(email, password);
        toast.success('Welcome back!');
        // Send returning users to their roadmap. The /roadmap route's
        // ProtectedRoute redirects to /onboarding automatically if the profile
        // isn't complete, so incomplete users still land in intake.
        navigate('/roadmap');
      }
    } catch (err) {
      toast.error(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      // Must be set before the OAuth redirect: when Supabase writes the session
      // on return, customStorage reads this flag to pick localStorage vs
      // sessionStorage. Without it Google users were never remembered.
      localStorage.setItem('delta_remember_me', rememberMe ? 'true' : 'false');
      await loginWithGoogle();
    } catch (err) {
      toast.error(err.message || 'Google Sign-In failed');
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-bone font-sans">

      {/* ── Left Panel: Form ── */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 sm:px-10 py-12 bg-bone relative z-[1]">

        <div className="w-full max-w-[400px] relative">

          {/* Logo */}
          <div className="flex flex-col items-center mb-9">
            <div className="w-[52px] h-[52px] bg-paper border border-rule flex items-center justify-center mb-4 overflow-hidden">
              <img
                src="/delta-bg.jpeg"
                alt="Delta logo"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="font-display text-[26px] font-semibold text-ink tracking-tight">Delta</span>
            <span className="kicker mt-1">Career Intelligence</span>
          </div>

          {/* Heading */}
          <h2 className="font-display text-[28px] font-semibold text-oxblood mb-1.5 text-center">
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="text-sm text-ink-soft text-center mb-8">
            {isSignUp ? (
              <>Already have an account?{' '}
                <button type="button" onClick={() => setIsSignUp(false)} className={linkClass}>Sign in</button>
              </>
            ) : (
              <>Don't have an account?{' '}
                <button type="button" onClick={() => setIsSignUp(true)} className={linkClass}>Sign up</button>
              </>
            )}
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">

            {/* Name field (sign-up only) */}
            {isSignUp && (
              <div className="relative flex items-center">
                <User className={iconClass} size={16} />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Full name"
                  disabled={loading}
                  className={inputClass}
                />
              </div>
            )}

            {/* Email */}
            <div className="relative flex items-center">
              <Mail className={iconClass} size={16} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                disabled={loading}
                className={inputClass}
              />
            </div>

            {/* Password */}
            <div className="relative flex items-center">
              <Lock className={iconClass} size={16} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                disabled={loading}
                className={`${inputClass} pr-11`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 w-9 h-9 bg-transparent border-none cursor-pointer text-ink-soft flex items-center justify-center"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Remember Me + Forgot Password */}
            <div className="flex items-center justify-between mt-0.5">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                {/* Custom checkbox */}
                <div
                  role="checkbox"
                  aria-checked={rememberMe}
                  tabIndex={0}
                  onClick={() => setRememberMe(!rememberMe)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setRememberMe(!rememberMe); } }}
                  className={`w-[17px] h-[17px] border flex items-center justify-center transition-all cursor-pointer shrink-0 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-oxblood ${
                    rememberMe ? 'border-ink bg-ink' : 'border-rule bg-transparent'
                  }`}
                >
                  {rememberMe && (
                    <svg viewBox="0 0 12 10" fill="none" className="w-[9px] h-[9px]">
                      <path d="M1 5l3.5 3.5L11 1" stroke="var(--bone)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
                <span className="text-[13px] text-ink-soft font-medium">
                  Remember me
                </span>
              </label>

              {!isSignUp && (
                <button
                  type="button"
                  onClick={async () => {
                    if (!email) { toast.error('Enter your email above first.'); return; }
                    try {
                      const { error } = await supabase.auth.resetPasswordForEmail(email, {
                        redirectTo: window.location.origin + '/login',
                      });
                      if (error) throw error;
                      toast.success('Password reset email sent — check your inbox.');
                    } catch (err) {
                      toast.error(err.message || 'Could not send reset email.');
                    }
                  }}
                  className={`${linkClass} text-[13px]`}
                >
                  Forgot password?
                </button>
              )}
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className={`mt-2 w-full py-[13px] border font-mono text-xs uppercase tracking-[0.14em] flex items-center justify-center gap-2 transition-colors ${
                loading
                  ? 'bg-accent-surface text-ink-soft border-rule cursor-not-allowed'
                  : 'bg-oxblood text-bone border-oxblood cursor-pointer hover:bg-ink hover:border-ink'
              }`}
            >
              {loading
                ? <Loader2 size={18} className="animate-spin" />
                : <span>{isSignUp ? 'Create account' : 'Sign in'}</span>
              }
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3.5 my-6">
            <div className="flex-1 h-px bg-rule" />
            <span className="font-mono text-[11px] text-ink-soft tracking-[0.1em] uppercase">or</span>
            <div className="flex-1 h-px bg-rule" />
          </div>

          {/* Google Sign-In */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full py-3 border border-rule bg-paper text-ink font-medium text-sm cursor-pointer flex items-center justify-center gap-2.5 hover:border-ink-soft transition-colors"
          >
            {/* Google icon */}
            <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          {/* Footer */}
          <p className="mt-8 text-center text-[11px] text-ink-soft leading-relaxed">
            By continuing, you agree to Delta's{' '}
            <a href="/terms" target="_blank" rel="noreferrer" className="text-oxblood underline">Terms</a>
            {' '}and{' '}
            <a href="/privacy" target="_blank" rel="noreferrer" className="text-oxblood underline">Privacy Policy</a>
          </p>

        </div>
      </div>

      {/* ── Right Panel: Image ── */}
      <div className="login-right-panel hidden lg:block w-[48%] min-w-[420px] relative overflow-hidden border-l border-rule">
        {/* Background image */}
        <img
          src="/login-bg.jpg"
          alt="Delta pattern"
          className="absolute inset-0 w-full h-full object-cover object-center"
        />

        {/* Warm overlay for the editorial look */}
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, rgba(26,25,24,0.55) 0%, rgba(26,25,24,0.35) 100%)' }} />

        {/* Overlay content */}
        <div className="relative z-[2] h-full flex flex-col justify-end p-12">
          <div className="bg-bone/95 border border-rule px-8 py-7">
            <p className="font-display text-ink text-[1.35rem] font-semibold leading-normal mb-3.5">
              Your personal career strategist — builds a roadmap from your story, not just your resume.
            </p>
            <p className="text-[13px] text-ink-soft leading-relaxed">
              Delta learns your goals, skills, and constraints, then gives you a weekly plan that actually fits your life.
            </p>
          </div>
        </div>
      </div>

      {/* Autofill styling for light inputs */}
      <style>{`
        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus {
          -webkit-text-fill-color: var(--ink) !important;
          -webkit-box-shadow: 0 0 0 1000px var(--paper) inset !important;
          background-clip: content-box !important;
        }
      `}</style>
    </div>
  );
}

/* ── Shared class strings ── */
const iconClass = 'absolute left-3.5 text-ink-soft pointer-events-none shrink-0';

const inputClass =
  'w-full bg-paper border border-rule py-[13px] pl-[42px] pr-3.5 text-ink placeholder:text-ink-soft text-sm outline-none transition-colors focus:border-oxblood box-border';

const linkClass =
  'text-oxblood font-medium bg-transparent border-none cursor-pointer text-sm no-underline p-0 hover:underline';
