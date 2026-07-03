import { create } from 'zustand';
import supabase from '../lib/supabaseClient';

// Mirror keys must respect the same "remember me" flag as Supabase's own
// session storage (see customStorage in lib/supabaseClient.js), otherwise the
// two can disagree: e.g. remember=false lets the real session expire with the
// tab, but a stale mirror in localStorage still says "logged in", so the next
// API call 401s and force-logs-out the user — looking exactly like "remember
// me never works" regardless of the checkbox.
function rememberEnabled() {
  return localStorage.getItem('delta_remember_me') === 'true';
}

function persistSession(session) {
  const store = rememberEnabled() ? localStorage : sessionStorage;
  const other = store === localStorage ? sessionStorage : localStorage;
  store.setItem('delta_user_id', session.user.id);
  store.setItem('delta_access_token', session.access_token);
  other.removeItem('delta_user_id');
  other.removeItem('delta_access_token');
}

function clearPersistedSession() {
  localStorage.removeItem('delta_user_id');
  sessionStorage.removeItem('delta_user_id');
  localStorage.removeItem('delta_access_token');
  sessionStorage.removeItem('delta_access_token');
}

export const useAuthStore = create((set) => ({
  userId: localStorage.getItem('delta_user_id') || sessionStorage.getItem('delta_user_id') || null,
  token: localStorage.getItem('delta_access_token') || sessionStorage.getItem('delta_access_token') || null,
  user: null,
  loading: true,

  setUserId: (id) => {
    if (id) {
      const store = rememberEnabled() ? localStorage : sessionStorage;
      store.setItem('delta_user_id', id);
    } else {
      localStorage.removeItem('delta_user_id');
      sessionStorage.removeItem('delta_user_id');
    }
    set({ userId: id });
  },

  setToken: (token) => {
    if (token) {
      const store = rememberEnabled() ? localStorage : sessionStorage;
      store.setItem('delta_access_token', token);
    } else {
      localStorage.removeItem('delta_access_token');
      sessionStorage.removeItem('delta_access_token');
    }
    set({ token });
  },

  // Initialize session state from Supabase
  initializeAuth: async () => {
    set({ loading: true });

    // Get initial session
    const { data: { session } } = await supabase.auth.getSession();

    if (session) {
      set({
        userId: session.user.id,
        token: session.access_token,
        user: session.user,
        loading: false
      });
      persistSession(session);
    } else {
      set({ userId: null, token: null, user: null, loading: false });
      clearPersistedSession();
    }

    // Listen for auth state changes (login, logout, token refresh, etc)
    supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        set({
          userId: session.user.id,
          token: session.access_token,
          user: session.user,
          loading: false
        });
        persistSession(session);
      } else {
        set({ userId: null, token: null, user: null, loading: false });
        clearPersistedSession();
      }
    });
  },

  // Email & Password Sign In
  login: async (email, password) => {
    set({ loading: true });
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      set({ loading: false });
      throw error;
    }
    if (data?.session) {
      set({
        userId: data.session.user.id,
        token: data.session.access_token,
        user: data.session.user,
        loading: false
      });
      persistSession(data.session);
    }
    return data;
  },

  // Email & Password Sign Up
  signUp: async (email, password, name) => {
    set({ loading: true });
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: name,
        }
      }
    });
    if (error) {
      set({ loading: false });
      throw error;
    }
    set({ loading: false });
    return data;
  },

  // Google OAuth Login
  loginWithGoogle: async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        // /roadmap gates on profile completion and falls back to onboarding.
        redirectTo: window.location.origin + '/roadmap',
      }
    });
    if (error) throw error;
    return data;
  },

  // Sign Out
  logout: async () => {
    set({ loading: true });
    await supabase.auth.signOut();
    set({ userId: null, token: null, user: null, loading: false });
    clearPersistedSession();
    localStorage.removeItem('delta_remember_me');
  }
}));
export default useAuthStore;
