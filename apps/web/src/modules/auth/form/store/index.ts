import { create } from "zustand";

import { AuthProvider } from "@akashic-labs/auth";

export const useAuthFormStore = create<{
  provider: AuthProvider;
  setProvider: (provider: AuthProvider) => void;
  isSubmitting: boolean;
  setIsSubmitting: (isSubmitting: boolean) => void;
}>((set) => ({
  provider: AuthProvider.PASSWORD,
  setProvider: (provider) => set({ provider }),
  isSubmitting: false,
  setIsSubmitting: (isSubmitting) => set({ isSubmitting }),
}));
