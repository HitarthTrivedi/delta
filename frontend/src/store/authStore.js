import { create } from 'zustand';
import supabase from '../lib/supabaseClient';

export const useAuthStore = create((set) => ({
  userId: localStorage.getItem('delta_user_id') || sessionStorage.getItem('delta_user_id') || null,
  token: localStorage.getItem('delta_access_token') || sessionStorage.getItem('delta_access_token') || null,
  user: null,
  loading: true,

  setUserId: (id) => {
    const remember = localStorage.getItem('delta_remember_me') === 'true';
    const storage = remember ? localStorage : sessionStorage;
    if (id) {
      storage.setItem('delta_user_id', id);
    } else {
      localStorage.removeItem('delta_user_id');
      sessionStorage.removeItem('delta_user_id');
    }
    set({ userId: id });
  },

  setToken: (token) => {
    const remember = localStorage.getItem('delta_remember_me') === 'true';
    const storage = remember ? localStorage : sessionStorage;
    if (token) {
      storage.setItem('delta_access_token', token);
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
    const { data: { session }, error } = await supabase.auth.getSession();
    const remember = localStorage.getItem('delta_remember_me') === 'true';
    const storage = remember ? localStorage : sessionStorage;
    
    if (session) {
      set({ 
        userId: session.user.id,
        token: session.access_token,
        user: session.user,
        loading: false
      });
      storage.setItem('delta_user_id', session.user.id);
      storage.setItem('delta_access_token', session.access_token);
    } else {
      set({ userId: null, token: null, user: null, loading: false });
      localStorage.removeItem('delta_user_id');
      sessionStorage.removeItem('delta_user_id');
      localStorage.removeItem('delta_access_token');
      sessionStorage.removeItem('delta_access_token');
    }

    // Listen for auth state changes (login, logout, token refresh, etc)
    supabase.auth.onAuthStateChange((_event, session) => {
      const remember = localStorage.getItem('delta_remember_me') === 'true';
      const storage = remember ? localStorage : sessionStorage;
      if (session) {
        set({ 
          userId: session.user.id,
          token: session.access_token,
          user: session.user,
          loading: false
        });
        storage.setItem('delta_user_id', session.user.id);
        storage.setItem('delta_access_token', session.access_token);
      } else {
        set({ userId: null, token: null, user: null, loading: false });
        localStorage.removeItem('delta_user_id');
        sessionStorage.removeItem('delta_user_id');
        localStorage.removeItem('delta_access_token');
        sessionStorage.removeItem('delta_access_token');
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
      const remember = localStorage.getItem('delta_remember_me') === 'true';
      const storage = remember ? localStorage : sessionStorage;
      set({ 
        userId: data.session.user.id, 
        token: data.session.access_token,
        user: data.session.user,
        loading: false 
      });
      storage.setItem('delta_user_id', data.session.user.id);
      storage.setItem('delta_access_token', data.session.access_token);
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
        redirectTo: window.location.origin + '/intake',
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
    localStorage.removeItem('delta_user_id');
    sessionStorage.removeItem('delta_user_id');
    localStorage.removeItem('delta_access_token');
    sessionStorage.removeItem('delta_access_token');
    localStorage.removeItem('delta_remember_me');
  }
}));
export default useAuthStore;
