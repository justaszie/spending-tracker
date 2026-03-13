import { FormEvent, useState } from "react";
import { Link, useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const [location, navigate] = useLocation();
  const params = new URLSearchParams(location.split("?")[1] ?? "");
  const next = params.get("next");

  const { login, isAuthLoading } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login({ email, password });
      navigate(next ? decodeURIComponent(next) : "/");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to sign in. Please try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const disabled = submitting || isAuthLoading;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md rounded-xl border bg-card shadow-sm p-8">
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
              <span className="text-xs font-bold">S</span>
            </div>
            <span className="font-semibold tracking-tight">SpendPulse</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Sign in to view and manage your spending.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="•••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <p className="text-sm text-destructive mt-1" role="alert">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full mt-2"
            disabled={disabled}
          >
            {disabled ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <div className="mt-6 flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-primary underline-offset-4 hover:underline">
              Sign up
            </Link>
          </span>
        </div>
      </div>
    </div>
  );
}

