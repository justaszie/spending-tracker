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
  currentToken: string | null;
  login: (params: LoginParams) => Promise<void>;
  signup: (params: SignupParams) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [currentToken, setCurrentToken] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function init() {
      const {
        data: { session: initialSession },
        error,
      } = await supabase.auth.getSession();

      if (!isMounted) return;
      if (error) {
        // If session lookup fails, treat as signed out and record error.
        setSession(null);
        setUser(null);
        setCurrentToken(null);
        setAuthError("Failed to check authentication status.");
      } else {
        setSession(initialSession);
        setUser(initialSession?.user ?? null);
        setCurrentToken(initialSession?.access_token ?? null);
        setAuthError(null);
      }
      setIsAuthLoading(false);
    }

    init();

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, nextSession: Session | null) => {
        setSession(nextSession);
        setUser(nextSession?.user ?? null);
        setCurrentToken(nextSession?.access_token ?? null);
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
      currentToken,
      login,
      signup,
      logout,
    }),
    [session, user, isAuthLoading, authError, currentToken, login, signup, logout],
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

