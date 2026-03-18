import { Switch, Route, Redirect } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import TransactionsPage from "@/pages/transactions";
import ReviewPage from "@/pages/review";
import LoginPage from "@/pages/login";
import NotFound from "@/pages/not-found";
import SignupPage from "@/pages/signup";
import { RequireAuth } from "@/components/RequireAuth";
import { PublicOnly } from "@/components/PublicOnly";
import { AuthProvider } from "@/contexts/AuthContext";
import { AppLayout } from "@/components/layout/AppLayout";

function AuthedRouter() {
  return (
    <AppLayout>
      <Switch>
        <Route path="/demo">
          {() => <TransactionsPage />}
        </Route>
        <Route path="/transactions">
          {() => <TransactionsPage />}
        </Route>
        <Route path="/dashboard">
          {() => <Redirect to="/transactions" />}
        </Route>
        <Route path="/review">
          {() => <ReviewPage />}
        </Route>
        <Route path="/">
          {() => <Redirect to="/transactions" />}
        </Route>
        <Route component={NotFound} />
      </Switch>
    </AppLayout>
  );
}

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
      <Route>
        {() => (
          <RequireAuth>
            <AuthedRouter />
          </RequireAuth>
        )}
      </Route>
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
