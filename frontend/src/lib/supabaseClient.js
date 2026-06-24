import { createClient } from '@supabase/supabase-js';

const rawUrl = process.env.REACT_APP_SUPABASE_URL || '';
// Clean the URL if it accidentally has the REST path suffix
const supabaseUrl = rawUrl.endsWith('/rest/v1/') 
  ? rawUrl.replace('/rest/v1/', '') 
  : rawUrl;

const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || '';

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn("Supabase credentials missing! Please check your frontend .env file.");
}

// Custom storage engine that dynamically respects the "Remember Me" checkbox
const customStorage = {
  getItem: (key) => {
    return localStorage.getItem(key) || sessionStorage.getItem(key);
  },
  setItem: (key, value) => {
    const remember = localStorage.getItem('delta_remember_me') === 'true';
    if (remember) {
      localStorage.setItem(key, value);
    } else {
      sessionStorage.setItem(key, value);
    }
  },
  removeItem: (key) => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  }
};

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: customStorage,
    persistSession: true,
    detectSessionInUrl: true
  }
});
export default supabase;
