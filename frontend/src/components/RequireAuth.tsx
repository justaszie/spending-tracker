import type { ReactNode } from "react";
import { Redirect, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import ErrorPage from "@/pages/error";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, isAuthLoading, authError } = useAuth();
  const [location] = useLocation();

  if (isAuthLoading) {
    return <div>Checking user Status...</div>;
  }

  if (authError) {
    return (
      <ErrorPage
        title="Authentication error"
        message="We could not authenticate you. Please refresh the page or log in again."
      />
    );
  }

  if (!session) {
    const next = encodeURIComponent(location);
    return <Redirect to={`/login?next=${next}`} />;
  }

  return <>{children}</>;
}

