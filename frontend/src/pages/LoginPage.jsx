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
        navigate('/intake');
      }
    } catch (err) {
      toast.error(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      await loginWithGoogle();
    } catch (err) {
      toast.error(err.message || 'Google Sign-In failed');
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      display: 'flex',
      background: '#0a0a0a',
      fontFamily: "'Inter', 'SF Pro Display', -apple-system, sans-serif",
    }}>

      {/* ── Left Panel: Form ── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 40px',
        background: '#0d0d0d',
        position: 'relative',
        zIndex: 1,
      }}>

        <div style={{ width: '100%', maxWidth: '400px', position: 'relative' }}>

          {/* Logo */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            marginBottom: '36px',
          }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '12px',
              background: '#111',
              border: '1px solid rgba(255,255,255,0.16)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}>
              <img
                src="/delta-bg.jpeg"
                alt="Delta logo"
                style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit' }}
              />
            </div>
            <span style={{
              fontSize: '22px',
              fontWeight: '700',
              color: '#ffffff',
              letterSpacing: '-0.5px',
            }}>Delta</span>
            <span style={{
              fontSize: '12px',
              color: 'rgba(255,255,255,0.35)',
              marginTop: '4px',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}>Career Intelligence</span>
          </div>

          {/* Heading */}
          <h2 style={{
            fontSize: '26px',
            fontWeight: '700',
            color: '#ffffff',
            marginBottom: '6px',
            textAlign: 'center',
            letterSpacing: '-0.4px',
          }}>
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </h2>
          <p style={{
            fontSize: '14px',
            color: 'rgba(255,255,255,0.4)',
            textAlign: 'center',
            marginBottom: '32px',
          }}>
            {isSignUp ? (
              <>Already have an account?{' '}
                <button type="button" onClick={() => setIsSignUp(false)}
                  style={linkStyle}>Sign in</button>
              </>
            ) : (
              <>Don't have an account?{' '}
                <button type="button" onClick={() => setIsSignUp(true)}
                  style={linkStyle}>Sign up</button>
              </>
            )}
          </p>

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

            {/* Name field (sign-up only) */}
            {isSignUp && (
              <div style={fieldWrapStyle}>
                <User style={iconStyle} size={16} />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Full name"
                  disabled={loading}
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.34)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
            )}

            {/* Email */}
            <div style={fieldWrapStyle}>
              <Mail style={iconStyle} size={16} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                disabled={loading}
                style={inputStyle}
                onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.34)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
            </div>

            {/* Password */}
            <div style={fieldWrapStyle}>
              <Lock style={iconStyle} size={16} />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                disabled={loading}
                style={{ ...inputStyle, paddingRight: '44px' }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,255,255,0.34)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '14px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'rgba(255,255,255,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '2px',
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Remember Me + Forgot Password */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2px' }}>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                userSelect: 'none',
              }}>
                {/* Custom checkbox */}
                <div
                  onClick={() => setRememberMe(!rememberMe)}
                  style={{
                    width: '17px',
                    height: '17px',
                    borderRadius: '5px',
                    border: rememberMe ? '1.5px solid rgba(255,255,255,0.85)' : '1.5px solid rgba(255,255,255,0.2)',
                    background: rememberMe ? '#fff' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.15s ease',
                    cursor: 'pointer',
                    flexShrink: 0,
                  }}
                >
                  {rememberMe && (
                    <svg viewBox="0 0 12 10" fill="none" style={{ width: '9px', height: '9px' }}>
                      <path d="M1 5l3.5 3.5L11 1" stroke="#000" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
                <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.45)', fontWeight: '500' }}>
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
                  style={{ ...linkStyle, fontSize: '13px' }}
                >
                  Forgot password?
                </button>
              )}
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: '8px',
                width: '100%',
                padding: '13px',
                borderRadius: '12px',
                border: 'none',
                background: loading
                  ? 'rgba(255,255,255,0.22)'
                  : '#f4f4f4',
                color: '#050505',
                fontWeight: '600',
                fontSize: '15px',
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all 0.2s ease',
                boxShadow: 'none',
                letterSpacing: '0.01em',
              }}
              onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#fff'; }}
              onMouseLeave={e => { if (!loading) e.currentTarget.style.background = '#f4f4f4'; }}
            >
              {loading
                ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                : <span>{isSignUp ? 'Create account' : 'Sign in'}</span>
              }
            </button>
          </form>

          {/* Divider */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            margin: '24px 0',
          }}>
            <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.08)' }} />
            <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>or</span>
            <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.08)' }} />
          </div>

          {/* Google Sign-In */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.04)',
              color: 'rgba(255,255,255,0.75)',
              fontWeight: '500',
              fontSize: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              transition: 'all 0.18s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.18)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
          >
            {/* Google icon */}
            <svg viewBox="0 0 24 24" style={{ width: '18px', height: '18px' }}>
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          {/* Footer */}
          <p style={{
            marginTop: '32px',
            textAlign: 'center',
            fontSize: '11px',
            color: 'rgba(255,255,255,0.18)',
            lineHeight: '1.6',
          }}>
            By continuing, you agree to Delta's{' '}
            <span
              onClick={() => window.open('/terms', '_blank')}
              style={{ color: 'rgba(255,255,255,0.65)', cursor: 'pointer', textDecoration: 'underline' }}
            >Terms</span>
            {' '}and{' '}
            <span
              onClick={() => window.open('/privacy', '_blank')}
              style={{ color: 'rgba(255,255,255,0.65)', cursor: 'pointer', textDecoration: 'underline' }}
            >Privacy Policy</span>
          </p>

        </div>
      </div>

      {/* ── Right Panel: Image ── */}
      <div style={{
        width: '48%',
        minWidth: '420px',
        position: 'relative',
        overflow: 'hidden',
        display: 'none',
      }}
        className="login-right-panel"
      >
        {/* Background image */}
        <img
          src="/login-bg.jpg"
          alt="Delta pattern"
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
          }}
        />

        {/* Dark overlay so it looks polished */}
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(135deg, rgba(0,0,0,0.68) 0%, rgba(20,20,20,0.52) 100%)',
        }} />

        {/* Overlay content */}
        <div style={{
          position: 'relative',
          zIndex: 2,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
          padding: '48px',
        }}>
          <div style={{
            background: 'rgba(0,0,0,0.45)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '16px',
            padding: '28px 32px',
          }}>
            <p style={{
              fontSize: '18px',
              fontWeight: '600',
              color: '#ffffff',
              lineHeight: '1.5',
              marginBottom: '14px',
              letterSpacing: '-0.2px',
            }}>
              Your personal career strategist — builds a roadmap from your story, not just your resume.
            </p>
            <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.42)', lineHeight: 1.6 }}>
              Delta learns your goals, skills, and constraints, then gives you a weekly plan that actually fits your life.
            </p>
          </div>
        </div>
      </div>

      {/* Responsive styles via style tag */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @media (min-width: 768px) {
          .login-right-panel {
            display: block !important;
          }
        }

        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus {
          -webkit-text-fill-color: rgba(255,255,255,0.85) !important;
          -webkit-box-shadow: 0 0 0 1000px #1a1a1a inset !important;
          background-clip: content-box !important;
        }
      `}</style>
    </div>
  );
}

/* ── Shared style objects ── */
const fieldWrapStyle = {
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
};

const iconStyle = {
  position: 'absolute',
  left: '14px',
  color: 'rgba(255,255,255,0.28)',
  pointerEvents: 'none',
  flexShrink: 0,
};

const inputStyle = {
  width: '100%',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  padding: '13px 14px 13px 42px',
  color: 'rgba(255,255,255,0.85)',
  fontSize: '14px',
  outline: 'none',
  transition: 'border-color 0.18s ease',
  boxSizing: 'border-box',
};

const linkStyle = {
  color: 'rgba(255,255,255,0.72)',
  fontWeight: '500',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontSize: '14px',
  textDecoration: 'none',
  padding: 0,
};
