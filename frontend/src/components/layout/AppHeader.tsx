import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { Link, useLocation } from "wouter";

type NavItem = {
  label: string;
  href: string;
};

const navItems: NavItem[] = [
  { label: "Transactions", href: "/transactions" },
  { label: "Review", href: "/review" },
];

export function AppHeader() {
  const { logout, user, isDemo } = useAuth();
  const [location] = useLocation();

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-6">
        <div className="mr-4 flex items-center gap-2 font-semibold">
          <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
            <span className="text-xs font-bold">S</span>
          </div>
          <span>SpendPulse</span>
        </div>

        <nav className="flex items-center space-x-6 text-sm font-medium">
          {navItems.map((item) => {
            const isActive = location === item.href;

            return (
              <Link key={item.href} href={item.href}>
                <a
                  className={
                    "transition-colors hover:text-foreground/80 " +
                    (isActive ? "text-foreground" : "text-foreground/60")
                  }
                >
                  {item.label}
                </a>
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center space-x-4">
          {isDemo && (
            <span className="px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
              Demo mode
            </span>
          )}
          <div className="flex items-center gap-1">
            <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center">
              <p>{user && user.email?.slice(0, 1).toUpperCase()}</p>
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="text-xs text-muted-foreground"
              onClick={() => logout()}
            >
              Logout
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

