import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  userId: '00000000-0000-0000-0000-000000000000',
  setUserId: (id) => set({ userId: id }),
}));
