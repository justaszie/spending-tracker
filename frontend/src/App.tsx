import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Dashboard from "@/pages/dashboard";
import LoginPage from "@/pages/login";
import NotFound from "@/pages/not-found";
import SignupPage from "@/pages/signup";
import { RequireAuth } from "@/components/RequireAuth";
import { PublicOnly } from "@/components/PublicOnly";
import { AuthProvider } from "@/contexts/AuthContext";

function Router() {
  return (
    <Switch>
      <Route path="/login">
        {() => (
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        )}
      </Route>
      <Route path="/signup">
        {() => (
          <PublicOnly>
            <SignupPage />
          </PublicOnly>
        )}
      </Route>
      <Route path="/demo">
        {() => (
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        )}
      </Route>
      <Route path="/">
        {() => (
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        )}
      </Route>
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
