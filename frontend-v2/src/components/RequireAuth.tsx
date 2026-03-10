import type { ReactNode } from "react";
import { Redirect, useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { session, isAuthLoading } = useAuth();
  const [location] = useLocation();

  if (isAuthLoading) {
    return <div>Checking user Status...</div>;
  }

  if (!session) {
    const next = encodeURIComponent(location);
    return <Redirect to={`/login?next=${next}`} />;
  }

  return <>{children}</>;
}

