import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { BellRing, CalendarClock, ChevronLeft, ChevronRight, CircleCheckBig, PartyPopper, Wallet } from "lucide-react";
import { OfferRow } from "@/components/offer-row";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { api, keys, type Card as CardData, type OfferStatus } from "@/lib/api";
import { bucket, holderLabel, issuerAccent, lastDay, money, shortCard } from "@/lib/format";
import { cn } from "@/lib/utils";

type Tab = "todo" | "pending" | "done";
type Sort = "deadline" | "card";
type Search = { tab?: Tab; holder?: string; sort?: Sort; month?: string };

export const Route = createFileRoute("/")({
  validateSearch: (search: Record<string, unknown>): Search => ({
    tab: search.tab === "pending" || search.tab === "done" ? search.tab : undefined,
    holder: typeof search.holder === "string" ? search.holder : undefined,
    sort: search.sort === "card" ? "card" : undefined,
    month: typeof search.month === "string" && /^\d{4}-\d{2}$/.test(search.month) ? search.month : undefined,
  }),
  loaderDeps: ({ search }) => ({ month: search.month }),
  loader: ({ context, deps }) =>
    context.queryClient.ensureQueryData({
      queryKey: keys.dashboard(deps.month),
      queryFn: () => api.dashboard(deps.month),
    }),
  pendingComponent: HomeSkeleton,
  component: Home,
});

type Row = { offer: OfferStatus; card: CardData };

function Home() {
  const raw = Route.useSearch();
  const search = { tab: raw.tab ?? "todo", holder: raw.holder, sort: raw.sort ?? "deadline", month: raw.month } as const;
  const navigate = useNavigate({ from: "/" });
  const { data } = useQuery({
    queryKey: keys.dashboard(search.month),
    queryFn: () => api.dashboard(search.month),
    placeholderData: keepPreviousData,
  });
  if (!data) return <HomeSkeleton />;
  const past = data.as_of < data.today;
  const monthIndex = data.months.indexOf(data.month);

  const holders = [...new Set(data.cards.map((c) => c.account.holder).filter((h): h is string => !!h))];
  const all: Row[] = data.cards.flatMap((card) => card.offers.map((offer) => ({ offer, card })));
  const mine = all.filter((r) => !search.holder || r.card.account.holder === search.holder);
  const reminders = mine.filter((r) => r.offer.state === "to_activate");
  const visible = mine.filter((r) => r.offer.kind !== "activation");
  const counts = { todo: 0, pending: 0, done: 0 };
  for (const r of visible) counts[bucket(r.offer.state)] += 1;
  const inTab = visible.filter((r) => bucket(r.offer.state) === search.tab);

  const openRows = visible.filter((r) => bucket(r.offer.state) === "todo");
  const openValue = openRows.reduce((sum, r) => sum + r.offer.remaining, 0);
  const endingSoon = openRows.filter((r) => r.offer.period.days_left <= 7);
  const capturedNow = visible.reduce((sum, r) => sum + r.offer.captured, 0);
  const cards = data.cards.filter((c) => !search.holder || c.account.holder === search.holder);
  const yearCaptured = cards.reduce((s, c) => s + c.year_captured, 0);
  const fees = cards.reduce((s, c) => s + c.annual_fee, 0);

  const set = (patch: Partial<Search>) => navigate({ search: (prev) => ({ ...prev, ...patch }), replace: true });

  const goMonth = (offset: number) => {
    const next = data.months[monthIndex + offset];
    if (next) set({ month: monthIndex + offset === data.months.length - 1 ? undefined : next });
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">{monthName(data.month)}</h1>
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" className="size-9" disabled={monthIndex <= 0} onClick={() => goMonth(-1)} aria-label="Previous month">
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="outline" size="icon" className="size-9" disabled={monthIndex >= data.months.length - 1} onClick={() => goMonth(1)} aria-label="Next month">
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Kpi
          className="col-span-2 lg:col-span-1"
          icon={<Wallet className="size-4" />}
          label={past ? "Left unclaimed" : "Left to claim now"}
          value={money(openValue)}
          tone="text-warning"
          detail={
            past
              ? `${openRows.length} unused`
              : endingSoon.length
              ? `${endingSoon.length} ending within 7 days`
              : `${openRows.length} open offer${openRows.length === 1 ? "" : "s"}`
          }
        />
        <Kpi
          icon={<CircleCheckBig className="size-4" />}
          label={past ? "Captured" : "Captured this period"}
          value={money(capturedNow)}
          tone="text-success"
          detail={`${counts.done} used or credited`}
        />
        <Card className="gap-0 py-0">
          <CardContent className="space-y-2 p-4">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarClock className="size-4" />
              {new Date(`${data.today}T00:00:00`).getFullYear()} value vs fees
            </div>
            <div className="tabular text-2xl font-semibold tracking-tight">
              {money(yearCaptured)}
              <span className="text-sm font-normal text-muted-foreground"> / {money(fees)}</span>
            </div>
            <Progress value={fees ? Math.min(100, (yearCaptured / fees) * 100) : 0} className="h-1.5" />
          </CardContent>
        </Card>
      </section>

      <section className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={search.tab} onValueChange={(tab) => set({ tab: tab as Tab })}>
          <TabsList className="h-10">
            <TabsTrigger value="todo" className="px-3">
              Unused <Count n={counts.todo} />
            </TabsTrigger>
            <TabsTrigger value="pending" className="px-3">
              Awaiting credit <Count n={counts.pending} />
            </TabsTrigger>
            <TabsTrigger value="done" className="px-3">
              Used <Count n={counts.done} />
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="flex items-center gap-2 overflow-x-auto">
          {holders.length > 1 && (
            <ToggleGroup
              type="single"
              size="sm"
              variant="outline"
              value={search.holder ?? "all"}
              onValueChange={(v) => set({ holder: v && v !== "all" ? v : undefined })}
            >
              <ToggleGroupItem value="all" className="px-3">
                Everyone
              </ToggleGroupItem>
              {holders.map((h) => (
                <ToggleGroupItem key={h} value={h} className="px-3">
                  {h}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
          <ToggleGroup
            type="single"
            size="sm"
            variant="outline"
            value={search.sort}
            onValueChange={(v) => v && set({ sort: v as Sort })}
          >
            <ToggleGroupItem value="deadline" className="px-3">
              By deadline
            </ToggleGroupItem>
            <ToggleGroupItem value="card" className="px-3">
              By card
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </section>

      {!past && reminders.length > 0 && <Reminders rows={reminders} />}

      {inTab.length === 0 ? (
        <Empty tab={search.tab} filtered={!!search.holder} onReset={() => set({ holder: undefined })} />
      ) : search.sort === "card" ? (
        <ByCard rows={inTab} past={past} />
      ) : (
        <ByDeadline rows={inTab} past={past} />
      )}
    </div>
  );
}

function Reminders({ rows }: { rows: Row[] }) {
  return (
    <section className="flex items-start gap-3 rounded-xl border border-dashed px-4 py-3 text-sm">
      <BellRing className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <ul className="space-y-1">
        {rows.map(({ offer, card }) => (
          <li key={`${offer.offer_id}:${offer.account.id}`}>
            <span className="font-medium">{shortCard(card.name)}</span>
            <span className="text-muted-foreground">
              {" "}
              · {holderLabel(offer.account)} · {offer.how_to_use ?? offer.name} By {lastDay(offer.period.end)}.
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function monthName(month: string): string {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function Count({ n }: { n: number }) {
  return <span className="tabular ml-1.5 text-xs text-muted-foreground">{n}</span>;
}

function Kpi({
  icon,
  label,
  value,
  detail,
  tone,
  className,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  tone: string;
  className?: string;
}) {
  return (
    <Card className={cn("gap-0 py-0", className)}>
      <CardContent className="space-y-1 p-4">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {icon}
          {label}
        </div>
        <div className={cn("tabular text-3xl font-semibold tracking-tight", tone)}>{value}</div>
        <div className="text-xs text-muted-foreground">{detail}</div>
      </CardContent>
    </Card>
  );
}

function sortRows(rows: Row[]): Row[] {
  return [...rows].sort(
    (a, b) =>
      a.offer.period.days_left - b.offer.period.days_left ||
      b.offer.remaining - a.offer.remaining ||
      a.offer.name.localeCompare(b.offer.name),
  );
}

function ByDeadline({ rows, past }: { rows: Row[]; past: boolean }) {
  const groups: [string, Row[]][] = past ? [["Offers in this month", rows]] : [
    ["Ending this week", rows.filter((r) => r.offer.period.days_left <= 7)],
    ["Ending this month", rows.filter((r) => r.offer.period.days_left > 7 && r.offer.period.days_left <= 31)],
    ["Later", rows.filter((r) => r.offer.period.days_left > 31)],
  ];
  return (
    <div className="space-y-5">
      {groups
        .filter(([, items]) => items.length)
        .map(([title, items]) => (
          <section key={title} className="space-y-2">
            <h2 className="px-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</h2>
            <Card className="gap-0 overflow-hidden py-0">
              <ul className="divide-y">
                {sortRows(items).map(({ offer, card }) => (
                  <OfferRow key={`${offer.offer_id}:${offer.account.id}`} offer={offer} cardName={card.name} past={past} />
                ))}
              </ul>
            </Card>
          </section>
        ))}
    </div>
  );
}

function ByCard({ rows, past }: { rows: Row[]; past: boolean }) {
  const byCard = new Map<string, Row[]>();
  for (const r of rows) {
    const key = `${r.card.card_id}:${r.card.account.id}`;
    byCard.set(key, [...(byCard.get(key) ?? []), r]);
  }
  return (
    <div className="space-y-4">
      {[...byCard.values()].map((items) => {
        const card = items[0].card;
        return (
          <Card key={`${card.card_id}:${card.account.id}`} className="gap-0 overflow-hidden py-0">
            <div className="flex items-center gap-3 border-b px-4 py-3 sm:px-5">
              <span className={cn("h-7 w-11 rounded-md bg-gradient-to-br shadow-sm", issuerAccent(card.issuer))} />
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{shortCard(card.name)}</div>
                <div className="text-xs text-muted-foreground">{card.account.holder ?? card.issuer}</div>
              </div>
            </div>
            <ul className="divide-y">
              {sortRows(items).map(({ offer }) => (
                <OfferRow key={offer.offer_id} offer={offer} cardName={card.name} showCard={false} past={past} />
              ))}
            </ul>
          </Card>
        );
      })}
    </div>
  );
}

function Empty({ tab, filtered, onReset }: { tab: Tab; filtered: boolean; onReset: () => void }) {
  const text = {
    todo: ["Nothing unused", "Every offer this period is used, credited, or skipped."],
    pending: ["Nothing awaiting a credit", "Purchases that wait for an issuer credit show here."],
    done: ["Nothing used yet this period", "Offers show here with a check mark as soon as a transaction uses them."],
  }[tab];
  return (
    <Card className="items-center gap-2 py-12 text-center">
      <PartyPopper className="size-8 text-success" />
      <div className="font-medium">{text[0]}</div>
      <p className="max-w-sm text-sm text-muted-foreground">{text[1]}</p>
      {filtered && (
        <button onClick={onReset} className="text-sm text-primary underline underline-offset-4">
          Show everyone
        </button>
      )}
    </Card>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Skeleton className="col-span-2 h-28 rounded-xl lg:col-span-1" />
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
      <Skeleton className="h-10 w-80 rounded-lg" />
      <div className="space-y-2">
        {Array.from({ length: 5 }, (_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
