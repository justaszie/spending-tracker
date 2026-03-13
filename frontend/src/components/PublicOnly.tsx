import type { ReactNode } from "react";
import { Redirect } from "wouter";
import { useAuth } from "@/contexts/AuthContext";

export function PublicOnly({ children }: { children: ReactNode }) {
  const { session, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return <div>Checking user status...</div>;
  }

  if (session) {
    return <Redirect to="/" />;
  }

  return <>{children}</>;
}

