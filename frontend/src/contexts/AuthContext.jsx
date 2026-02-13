import { createContext, useContext, useState, useEffect } from "react";
import { createClient } from "@supabase/supabase-js";

const AuthContext = createContext(null);

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Checking if authenticated on initial load
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    // Set up a listener that will get auth state updates
    // and update client session accordingly
    const { data } = supabase.auth.onAuthStateChange(
      (_event, authenticated_session) => {
        setSession(authenticated_session);
      },
    );

    // Remove the auth state listener when auth context is cleared
    return () => {
      data.subscription.unsubscribe();
    };
  }, []);

  const login = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email,
      password: password,
    });

    if (error) {
      return { success: false, error: error.message };
    } else {
      setSession(data.session);
      return { success: true };
    }
  };

  const signup = async (email, password) => {
    const { data, error } = await supabase.auth.signUp({
      email: email,
      password: password,
    });
    if (error) {
      return { success: false, error: error.message };
    }

    setSession(data.session);
    return { success: true };
  };

  const logout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ session, login, signup, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
