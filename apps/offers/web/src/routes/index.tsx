import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Check, ChevronRight, Coins, Hand, KeyRound, ReceiptText, RotateCcw, SkipForward, Smartphone, TriangleAlert } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { CellCaption, LOOK_LABEL, Mark, look, type Look } from "@/components/cell";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  trackerApi,
  type CardRewards,
  type Cell,
  type Tracker,
  type TrackerCard,
  type TrackerRow,
} from "@/lib/api";
import {
  MONTH_NAMES,
  feeYearCaptured,
  holderLabel,
  issuerAccent,
  longDate,
  money,
  monthBefore,
  monthYear,
  shortCard,
  shortDate,
} from "@/lib/format";
import { useCellMark } from "@/lib/mutations";
import { cn } from "@/lib/utils";

const MONTHS = 6;

export const Route = createFileRoute("/")({
  loader: ({ context }) =>
    context.queryClient.ensureQueryData({ queryKey: trackerApi.key(MONTHS), queryFn: () => trackerApi.get(MONTHS) }),
  pendingComponent: TrackerSkeleton,
  component: TrackerPage,
});

function TrackerPage() {
  const { data } = useQuery({ queryKey: trackerApi.key(MONTHS), queryFn: () => trackerApi.get(MONTHS) });
  if (!data) return <TrackerSkeleton />;
  return (
    <div className="space-y-6">
      <Hero data={data} />
      <Resets cards={data.cards} />
      <Legend />
      {data.cards.map((card) => (
        <CardGrid key={`${card.card_id}:${card.account.id}`} card={card} months={data.months} />
      ))}
      {data.unmatched_accounts.length > 0 && (
        <p className="px-1 text-xs text-muted-foreground">
          Accounts in Actual Budget without a card in the catalog: {data.unmatched_accounts.join(", ")}. Add a card to{" "}
          <code>apps/offers/catalog.yaml</code> to track one.
        </p>
      )}
    </div>
  );
}

function monthLabel(key: string, style: "short" | "long" = "short") {
  return new Date(`${key}-01T00:00:00`).toLocaleDateString("en-US", {
    month: style,
    ...(style === "long" ? { year: "numeric" } : {}),
  });
}

function Hero({ data }: { data: Tracker }) {
  const c = data.current;
  const percent = c.available ? (c.captured / c.available) * 100 : 0;
  const stale =
    data.latest_txn && (new Date(data.today).getTime() - new Date(data.latest_txn).getTime()) / 86_400_000 > 4;
  return (
    <section className="space-y-4">
      {stale && data.latest_txn && (
        <div className="flex items-start gap-3 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3 text-sm">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
          <p>
            <span className="font-medium">
              Actual Budget has no transactions after{" "}
              {new Date(`${data.latest_txn}T00:00:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" })}.
            </span>{" "}
            <span className="text-muted-foreground">
              Run the bank sync in Actual Budget. Until then, later months show as open or missed.
            </span>
          </p>
        </div>
      )}
      <div className="rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
        <div className="text-sm text-muted-foreground">{monthLabel(c.month, "long")}</div>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="tabular text-4xl font-semibold tracking-tight text-success sm:text-5xl">
            {money(c.captured)}
          </span>
          <span className="text-lg text-muted-foreground">
            used of <span className="tabular text-foreground">{money(c.available)}</span> in credits
          </span>
        </div>
        <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full rounded-full bg-success transition-all" style={{ width: `${Math.min(100, percent)}%` }} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <Pill look="used" text={`${c.used_count} used`} />
          <Pill look="open" text={`${c.open_count} open · ${money(c.open)} left`} />
          {c.ending_soon > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-soft px-3 py-1 text-warning">
              <AlertTriangle className="size-3.5" /> {c.ending_soon} end within 7 days
            </span>
          )}
          {c.missed > 0 && <Pill look="missed" text={`${money(c.missed)} missed last month`} />}
          {data.captured_total > 0 && (
            <span className="inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1">
              <Coins className="size-3.5 text-success" /> {money(data.captured_total)} captured so far, all cards
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

function Resets({ cards }: { cards: TrackerCard[] }) {
  const withFee = cards.filter((c) => c.annual_fee > 0);
  return (
    <details className="group rounded-xl border bg-card px-4 py-3 text-sm sm:px-5">
      <summary className="flex cursor-pointer list-none items-center justify-between font-medium">
        When do credits reset?
        <ChevronRight className="size-4 text-muted-foreground transition-transform group-open:rotate-90" />
      </summary>
      <div className="mt-3 space-y-3 text-muted-foreground">
        <p>
          Most credits follow the <span className="text-foreground">calendar</span>: a monthly credit resets on the
          1st, a half-year credit on January 1 and July 1, and a yearly credit on January 1. The date that you pay the
          annual fee does not change them.
        </p>
        <p>
          A few credits follow the <span className="text-info">card-member year</span>. It starts on the account
          anniversary, which is when the annual fee posts, and runs for 12 months. These rows say{" "}
          <span className="text-info">Card year</span>.
        </p>
        <ul className="space-y-1.5">
          {withFee.map((c) => {
            const cardYear = c.rows.filter((r) => r.period === "cardmember_year").map((r) => r.name);
            const f = c.fee;
            return (
              <li key={`${c.card_id}:${c.account.id}`}>
                <span className="font-medium text-foreground">{shortCard(c.name)}</span>
                {" · "}
                {f.source === "fee" && f.fee_date
                  ? `$${c.annual_fee} fee posted ${longDate(f.fee_date)}, so the fee year runs ${monthYear(f.year_start!)} – ${monthBefore(f.year_end!)}.`
                  : f.anniversary_month
                    ? `The fee is not in your data. The card year most likely starts in ${MONTH_NAMES[f.anniversary_month - 1]}.`
                    : "The fee date is not in your data."}{" "}
                {cardYear.length
                  ? `${cardYear.join(", ")} ${cardYear.length === 1 ? "follows" : "follow"} the card year. Everything else follows the calendar.`
                  : "All its credits follow the calendar."}
              </li>
            );
          })}
        </ul>
        <p>
          The <span className="text-foreground">fee year</span> on each card counts the credits that you captured
          between two annual fees, because that is what the fee pays for.
        </p>
      </div>
    </details>
  );
}

function Pill({ look: l, text }: { look: Look; text: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1">
      <Mark look={l} size="sm" fraction={0.5} />
      {text}
    </span>
  );
}

function Legend() {
  const items: Look[] = ["used", "partial", "open", "missed", "unknown", "pending", "skipped"];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-1 text-xs text-muted-foreground">
      {items.map((l) => (
        <span key={l} className="inline-flex items-center gap-1.5">
          <Mark look={l} size="sm" fraction={0.5} />
          {LOOK_LABEL[l]}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5">
        <Smartphone className="size-3.5" /> In-app credit
      </span>
      <span className="inline-flex items-center gap-1.5">
        <ReceiptText className="size-3.5" /> Statement credit
      </span>
    </div>
  );
}

const PER: Record<string, string> = {
  monthly: "mo",
  quarterly: "quarter",
  semiannual: "half-year",
  annual: "year",
  cardmember_year: "card year",
  once: "one time",
};

function CardGrid({ card, months }: { card: TrackerCard; months: string[] }) {
  const fee = card.annual_fee;
  const last = months[months.length - 1];
  const scroller = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [months.length]);
  const hasOffers = card.rows.length > 0;
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <header className={cn("flex flex-wrap items-center gap-3 px-4 py-3.5 sm:px-5", hasOffers && "border-b")}>
        <span className={cn("h-8 w-12 shrink-0 rounded-md bg-gradient-to-br shadow-sm", issuerAccent(card.issuer))} />
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{shortCard(card.name)}</div>
          <div className="text-xs text-muted-foreground">
            {holderLabel(card.account)}
            {hasOffers && card.total && card.total.since && (
              <>
                {" · "}
                <span className="tabular font-medium text-success">{money(card.total.captured)}</span> captured since{" "}
                {monthYear(card.total.since)} ({card.total.months} month{card.total.months === 1 ? "" : "s"})
              </>
            )}
          </div>
          {card.rewards && <Rates rewards={card.rewards} />}
        </div>
        {fee > 0 && <FeeYear card={card} />}
      </header>
      {hasOffers && (
      <div ref={scroller} className="overflow-x-auto overscroll-x-contain">
        <table className="w-full border-separate border-spacing-0 text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 min-w-36 bg-card px-4 py-2 text-left text-xs font-medium text-muted-foreground sm:min-w-56 sm:px-5">
                Offer
              </th>
              {months.map((m) => (
                <th
                  key={m}
                  className={cn(
                    "min-w-[3.75rem] px-1 py-2 text-center text-xs font-medium text-muted-foreground sm:min-w-16",
                    m === last && "bg-accent/60 text-foreground",
                  )}
                >
                  {monthLabel(m)}
                  {m === last && <div className="text-[10px] font-normal text-muted-foreground">now</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {card.rows.map((row) => (
              <OfferLine key={row.offer_id} row={row} card={card} last={last} />
            ))}
          </tbody>
        </table>
      </div>
      )}
    </Card>
  );
}

function rateText(r: CardRewards, rate: number): string {
  return r.currency === "cash" ? `${rate}%` : `${rate}x`;
}

function Rates({ rewards: r }: { rewards: CardRewards }) {
  const items = [...r.rules.map((b) => `${rateText(r, b.rate)} ${b.name.toLowerCase()}`), `${rateText(r, r.base)} everything else`];
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5" title={r.note ?? undefined}>
      {items.map((t) => (
        <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
          {t}
        </span>
      ))}
    </div>
  );
}

function FeeYear({ card }: { card: TrackerCard }) {
  const f = card.fee;
  const captured = feeYearCaptured(card);
  return (
    <div className="w-full text-left sm:w-60 sm:text-right">
      <div className="text-xs text-muted-foreground">
        {f.year_start && f.year_end
          ? `Fee year ${monthYear(f.year_start)} – ${monthBefore(f.year_end)}`
          : "This calendar year"}
      </div>
      <div className="text-sm">
        <span className="tabular font-semibold text-success">{money(captured)}</span>
        <span className="text-muted-foreground">
          {" "}
          of <span className="tabular">{money(card.annual_fee)}</span> fee earned back
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-success"
          style={{ width: `${Math.min(100, (captured / card.annual_fee) * 100)}%` }}
        />
      </div>
      <div className="mt-1 text-[11px] text-muted-foreground">
        {f.source === "fee" && f.fee_date
          ? `Annual fee posted ${longDate(f.fee_date)}`
          : f.source === "catalog" && f.anniversary_month
            ? `Card year starts in ${MONTH_NAMES[f.anniversary_month - 1]} (estimated)`
            : "Annual fee date not found"}
      </div>
    </div>
  );
}

function OfferLine({ row, card, last }: { row: TrackerRow; card: TrackerCard; last: string }) {
  const Kind = row.kind === "activation" ? KeyRound : row.in_app ? Smartphone : ReceiptText;
  return (
    <tr className="group">
      <td className="sticky left-0 z-10 border-t bg-card px-4 py-3 align-middle sm:px-5">
        <Link to="/offers/$offerId/$accountId" params={{ offerId: row.offer_id, accountId: card.account.id }} className="block">
          <div className="flex items-center gap-1.5 font-medium leading-tight" title={row.cycle}>
            <Kind className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="hover:underline">{row.name}</span>
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            {row.kind === "activation"
              ? "Activation reminder"
              : `${money(row.value)} / ${PER[row.period] ?? row.period}${row.uses > 1 ? ` · ${row.uses} uses` : ""}`}
          </div>
          {row.next_reset && row.period !== "once" && (
            <div className={cn("mt-0.5 text-[11px]", row.period === "cardmember_year" ? "text-info" : "text-muted-foreground")}>
              {row.period === "cardmember_year" ? "Card year · " : ""}resets {shortDate(row.next_reset)}
              {row.period !== "monthly" && `, ${new Date(`${row.next_reset}T00:00:00`).getFullYear()}`}
            </div>
          )}
        </Link>
      </td>
      {row.cells.map((cell) => (
        <CellView key={cell.month} cell={cell} row={row} card={card} highlight={cell.month === last || cell.current} />
      ))}
    </tr>
  );
}

function CellView({ cell, row, card, highlight }: { cell: Cell; row: TrackerRow; card: TrackerCard; highlight: boolean }) {
  const [open, setOpen] = useState(false);
  const mark = useCellMark();
  const l = look(cell);
  const fraction = cell.uses > 1 ? cell.used / cell.uses : cell.value ? cell.captured / cell.value : 0;
  const warn = cell.elsewhere > 0 && (l === "open" || l === "missed");
  const activation = row.kind === "activation";
  const canMark = !cell.override && cell.state !== null && ["unused", "partial", "pending", "to_activate"].includes(cell.state);
  const offerId = cell.offer_id ?? row.offer_id;
  const send = (status: "used" | "ignored" | null) => {
    if (!cell.period_start) return;
    mark.mutate({
      offer_id: offerId,
      account_id: card.account.id,
      period_start: cell.period_start,
      status,
      kind: row.kind,
      name: row.name,
      label: cell.period_label ?? "",
    });
    setOpen(false);
  };
  const content = (
    <div
      className={cn(
        "relative mx-auto flex flex-col items-center gap-1 rounded-lg px-1 py-1.5",
        cell.span > 1 && "flex-row justify-center gap-2 border bg-background/60 px-3",
      )}
    >
      <Mark look={l} fraction={fraction} />
      <div className={cn("flex flex-col items-center", cell.span > 1 && "items-start")}>
        <CellCaption cell={cell} l={l} />
        {cell.span > 1 && cell.period_label && (
          <span className="mt-0.5 text-[10px] text-muted-foreground">{cell.period_label}</span>
        )}
      </div>
      {warn && <span className="absolute top-0.5 right-0.5 size-2 rounded-full bg-warning ring-2 ring-card" />}
      {cell.override && <Hand className="absolute right-0.5 bottom-0.5 size-3 text-muted-foreground" />}
    </div>
  );
  return (
    <td colSpan={cell.span} className={cn("border-t px-1 py-2 text-center align-middle", highlight && "bg-accent/40")}>
      {cell.state ? (
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              aria-label={`${row.name}, ${cell.period_label}: ${LOOK_LABEL[l]}`}
              className="block w-full rounded-lg transition hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              {content}
            </button>
          </PopoverTrigger>
          <PopoverContent side="top" className="w-72 space-y-3 text-left">
            <div>
              <div className="font-medium">{row.name}</div>
              <div className="text-xs text-muted-foreground">{cell.period_label}</div>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Mark look={l} size="sm" fraction={fraction} />
              <span>
                {LOOK_LABEL[l]}
                {cell.captured > 0 && ` · ${money(cell.captured)} captured`}
                {cell.remaining > 0 && ` · ${money(cell.remaining)} ${l === "missed" ? "missed" : "left"}`}
              </span>
            </div>
            <p className="rounded-md bg-muted px-2.5 py-1.5 text-xs text-muted-foreground">{row.cycle}</p>
            {cell.override && <p className="text-xs text-muted-foreground">You marked this period yourself.</p>}
            {cell.data_from && (
              <p className="text-xs text-muted-foreground">
                Your Actual Budget data starts {cell.data_from}. Use before that date is not visible.
              </p>
            )}
            {warn && (
              <p className="text-xs text-warning">
                {cell.elsewhere} matching order{cell.elsewhere === 1 ? " was" : "s were"} paid with another card. Pay
                with this card to use the credit.
              </p>
            )}
            {canMark && (
              <div className="grid grid-cols-2 gap-2">
                <Button size="sm" disabled={mark.isPending} onClick={() => send("used")}>
                  <Check className="size-4" /> {activation ? "I activated it" : "I used it"}
                </Button>
                <Button size="sm" variant="outline" disabled={mark.isPending} onClick={() => send("ignored")}>
                  <SkipForward className="size-4" /> Not interested
                </Button>
              </div>
            )}
            {cell.override && (
              <Button size="sm" variant="outline" className="w-full" disabled={mark.isPending} onClick={() => send(null)}>
                <RotateCcw className="size-4" /> Undo my mark
              </Button>
            )}
            <Link
              to="/offers/$offerId/$accountId"
              params={{ offerId, accountId: card.account.id }}
              className="flex items-center justify-between rounded-md px-1 py-1 text-xs text-muted-foreground hover:text-foreground"
            >
              History and transactions <ChevronRight className="size-3.5" />
            </Link>
          </PopoverContent>
        </Popover>
      ) : (
        <div className="mx-auto grid h-12 place-items-center">
          <Mark look="none" />
        </div>
      )}
    </td>
  );
}

function TrackerSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-44 rounded-2xl" />
      <Skeleton className="h-5 w-96" />
      {Array.from({ length: 2 }, (_, i) => (
        <Skeleton key={i} className="h-72 rounded-xl" />
      ))}
    </div>
  );
}
