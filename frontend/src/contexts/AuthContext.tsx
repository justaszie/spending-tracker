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
  loginDemo: () => Promise<void>;
  signup: (params: SignupParams) => Promise<void>;
  logout: () => Promise<void>;
  isDemo: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? "real";
const APP_ENVIRONMENT = import.meta.env.VITE_APP_ENVIRONMENT ?? "prod";
const TEST_USER_ID = import.meta.env.VITE_TEST_USER_ID as string | undefined;
const DEMO_EMAIL = import.meta.env.VITE_DEMO_EMAIL as string | undefined;
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD as string | undefined;

const IS_DEMO_MODE =
  AUTH_MODE === "demo" && APP_ENVIRONMENT === "dev" && !!TEST_USER_ID;

function isDemoRoute(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const url = new URL(window.location.href);
    return url.pathname === "/demo";
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const isDemo = useMemo(() => {
    // Local demo mode always counts as demo.
    if (IS_DEMO_MODE && TEST_USER_ID) {
      return true;
    }
    // In real Supabase auth, treat the configured demo account as demo.
    if (!user || !DEMO_EMAIL) return false;
    return user.email === DEMO_EMAIL;
  }, [user]);

  useEffect(() => {
    let isMounted = true;

    async function init() {
      // Local demo mode: mock session when Supabase isn't available (development only).
      if (IS_DEMO_MODE && TEST_USER_ID) {
        const mockUser = {
          id: TEST_USER_ID,
          email: "test@test",
        } as User;

        const mockSession = {
          access_token: "demo-access-token",
          token_type: "bearer",
          user: mockUser,
          expires_in: 60 * 60 * 24 * 365,
          expires_at: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 365,
          refresh_token: "demo-refresh-token",
          provider_token: null,
          provider_refresh_token: null,
        } as Session;

        if (!isMounted) return;

        setSession(mockSession);
        setUser(mockUser);
        setAuthError(null);
        setIsAuthLoading(false);

        return;
      }

      // Get the current user session first if it exists (managed by Supabase).
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
        setIsAuthLoading(false);
        return;
      }

      if (initialSession) {
        setSession(initialSession);
        setUser(initialSession?.user ?? null);
        setAuthError(null);
        setIsAuthLoading(false);
        return;
      }

      // No existing session yet. If we're on the /demo route and demo credentials
      // are configured, automatically sign in the demo user so visitors can
      // access the demo with a single URL.
      if (isDemoRoute() && DEMO_EMAIL && DEMO_PASSWORD) {
        try {
          const { data, error: demoError } = await supabase.auth.signInWithPassword({
            email: DEMO_EMAIL,
            password: DEMO_PASSWORD,
          });

          if (!isMounted) return;

          if (demoError || !data.session) {
            setSession(null);
            setUser(null);
            setAuthError("Failed to sign in demo user.");
            setIsAuthLoading(false);
            return;
          }

          setSession(data.session);
          setUser(data.session.user ?? null);
          setAuthError(null);
          setIsAuthLoading(false);
          return;
        } catch {
          if (!isMounted) return;
          setSession(null);
          setUser(null);
          setAuthError("Failed to sign in demo user.");
          setIsAuthLoading(false);
          return;
        }
      }

      // Regular unauthenticated state (no session yet).
      setSession(null);
      setUser(null);
      setAuthError(null);
      setIsAuthLoading(false);
    }

    init();

    // When in local demo, no auth state subscription needed. Cleanup just means unmounting
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

  const loginDemo = useCallback(async () => {
    if (!DEMO_EMAIL || !DEMO_PASSWORD) {
      throw new Error("Demo user is not configured.");
    }
    const { error } = await supabase.auth.signInWithPassword({
      email: DEMO_EMAIL,
      password: DEMO_PASSWORD,
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
      loginDemo,
      signup,
      logout,
      isDemo,
    }),
    [
      session,
      user,
      isAuthLoading,
      authError,
      login,
      loginDemo,
      signup,
      logout,
      isDemo,
    ],
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
