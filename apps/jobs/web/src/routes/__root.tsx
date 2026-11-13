import type { QueryClient } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { Link, Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { Briefcase, Building2, MessageCircleQuestion, Users } from "lucide-react";
import { api, keys } from "@/lib/api";
import { relativeTime } from "@/lib/format";

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: Layout,
});

const NAV = [
  { to: "/", label: "Companies", icon: Building2 },
  { to: "/recruiters", label: "Recruiters", icon: Users },
  { to: "/questions", label: "Questions", icon: MessageCircleQuestion },
] as const;

function Count({ n }: { n: number }) {
  if (!n) return null;
  return (
    <span className="tabular ml-1.5 rounded-full bg-warning-soft px-1.5 py-px text-[10px] font-semibold text-warning">{n}</span>
  );
}

function Layout() {
  const { data } = useQuery({ queryKey: keys.overview, queryFn: api.overview });
  const open = data?.totals.open_questions ?? 0;
  return (
    <div className="min-h-dvh bg-background">
      <header className="sticky top-0 z-30 border-b bg-background">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-7 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Briefcase className="size-4" />
            </span>
            Jobs
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            {NAV.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                className="flex items-center rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                activeProps={{ className: "bg-accent text-foreground font-medium" }}
              >
                {label}
                {to === "/questions" && <Count n={open} />}
              </Link>
            ))}
          </nav>
          <div className="ml-auto text-xs text-muted-foreground">
            {data?.last_sync ? `Synced ${relativeTime(data.last_sync)}` : data && "No sync yet"}
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
              <span className="relative">
                <Icon className="size-5" />
                {to === "/questions" && open > 0 && (
                  <span className="tabular absolute -top-1.5 -right-3 rounded-full bg-warning px-1 text-[9px] font-semibold text-background">
                    {open}
                  </span>
                )}
              </span>
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
