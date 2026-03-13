import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabaseClient";
import { FullScreenLoader } from "@/components/FullScreenLoader";

type LoginParams = { email: string; password: string };
type SignupParams = { email: string; password: string };

export type AuthContextValue = {
  session: Session | null;
  user: User | null;
  isAuthLoading: boolean;
  authError: string | null;
  login: (params: LoginParams) => Promise<void>;
  signup: (params: SignupParams) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? "real";
const APP_ENVIRONMENT = import.meta.env.VITE_APP_ENVIRONMENT;
const TEST_USER_ID = import.meta.env.TEST_USER_ID as string | undefined;

const IS_DEMO_MODE =
  AUTH_MODE === "demo" && APP_ENVIRONMENT === "dev" && !!TEST_USER_ID;

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function init() {
      if (IS_DEMO_MODE && TEST_USER_ID) {
        const mockUser = {
          id: TEST_USER_ID,
        } as unknown as User;

        const mockSession = {
          access_token: "demo-access-token",
          token_type: "bearer",
          user: mockUser,
          expires_in: 60 * 60 * 24 * 365,
          expires_at: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 365,
          refresh_token: "demo-refresh-token",
          provider_token: null,
          provider_refresh_token: null,
        } as unknown as Session;

        if (!isMounted) return;

        setSession(mockSession);
        setUser(mockUser);
        setAuthError(null);
        setIsAuthLoading(false);

        return;
      }

      const {
        data: { session: initialSession },
        error,
      } = await supabase.auth.getSession();

      if (!isMounted) return;
      if (error) {
        // If session lookup fails, treat as signed out and record error.
        setSession(null);
        setUser(null);
        setAuthError("Failed to check authentication status.");
      } else {
        setSession(initialSession);
        setUser(initialSession?.user ?? null);
        setAuthError(null);
      }
      setIsAuthLoading(false);
    }

    init();

    if (IS_DEMO_MODE && TEST_USER_ID) {
      return () => {
        isMounted = false;
      };
    }

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, nextSession: Session | null) => {
        setSession(nextSession);
        setUser(nextSession?.user ?? null);
        setIsAuthLoading(false);
        setAuthError(null);
      },
    );

    return () => {
      isMounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  const login = useCallback(async ({ email, password }: LoginParams) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
  }, []);

  const signup = useCallback(async ({ email, password }: SignupParams) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  }, []);

  const logout = useCallback(async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;

    // Clear any cached data immediately on logout.
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user,
      isAuthLoading,
      authError,
      login,
      signup,
      logout,
    }),
    [session, user, isAuthLoading, authError, login, signup, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      <FullScreenLoader open={isAuthLoading} label="Loading..." />
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

