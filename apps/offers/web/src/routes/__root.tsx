import type { QueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { CreditCard, LayoutGrid, Sparkles, TicketPercent } from "lucide-react";
import { trackerApi } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: Layout,
});

const NAV = [
  { to: "/", label: "Tracker", icon: LayoutGrid },
  { to: "/review", label: "AI log", icon: Sparkles },
  { to: "/cards", label: "Cards", icon: CreditCard },
] as const;

function Layout() {
  const { data } = useQuery({ queryKey: trackerApi.key(6), queryFn: () => trackerApi.get(6) });
  const run = data?.last_run;

  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-30 border-b bg-background">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-7 place-items-center rounded-lg bg-primary text-primary-foreground">
              <TicketPercent className="size-4" />
            </span>
            Offers
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            {NAV.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="relative rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                activeProps={{ className: "bg-accent text-foreground font-medium" }}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto text-xs text-muted-foreground">
            {run ? (
              <span className="flex items-center gap-1.5">
                <span
                  className={cn("size-1.5 rounded-full", run.status === "ok" ? "bg-success" : "bg-destructive")}
                />
                Synced {relativeTime(run.finished_at ?? run.started_at)}
              </span>
            ) : (
              data && "No sync yet"
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pt-5 pb-28 sm:px-6 sm:pb-12">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t bg-background pb-[env(safe-area-inset-bottom)] sm:hidden">
        <div className="mx-auto grid max-w-md grid-cols-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: to === "/" }}
              className="relative flex h-16 flex-col items-center justify-center gap-1 text-[11px] text-muted-foreground"
              activeProps={{ className: "text-foreground font-medium" }}
            >
              <Icon className="size-5" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
