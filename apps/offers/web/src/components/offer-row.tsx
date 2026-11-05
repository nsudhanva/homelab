import { Link } from "@tanstack/react-router";
import { History, MoreHorizontal, RotateCcw, SkipForward, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { OfferStatus } from "@/lib/api";
import { bucket, deadlineText, holderLabel, lastDay, money, shortCard, urgency } from "@/lib/format";
import { useOverride } from "@/lib/mutations";
import { cn } from "@/lib/utils";
import { StateChip, StateIcon, UsePips } from "./state";

export function OfferRow({
  offer,
  cardName,
  showCard = true,
  past = false,
}: {
  offer: OfferStatus;
  cardName: string;
  showCard?: boolean;
  past?: boolean;
}) {
  const setOverride = useOverride();
  const group = bucket(offer.state);
  const done = group === "done";
  const level = urgency(offer.period.days_left);
  const activation = offer.kind === "activation";
  const usedCount =
    offer.uses > 1 && offer.value > 0 ? Math.round((offer.captured / offer.value) * offer.uses) : 0;

  return (
    <li
      className={cn(
        "group flex items-start gap-3 px-4 py-3.5 transition-colors sm:px-5",
        done ? "opacity-75" : "hover:bg-accent/40",
      )}
    >
      <StateIcon state={offer.state} className="mt-0.5" />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Link
            to="/offers/$offerId/$accountId"
            params={{ offerId: offer.offer_id, accountId: offer.account.id }}
            className={cn(
              "font-medium leading-tight hover:underline underline-offset-4",
              offer.state === "ignored" && "line-through decoration-muted-foreground/60",
            )}
          >
            {offer.name}
          </Link>
          <StateChip state={offer.state} />
          {offer.enrollment && !done && !past && (
            <span className="rounded-full border px-2 py-0.5 text-[11px] text-muted-foreground">
              Enrollment required
            </span>
          )}
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
          {showCard && (
            <span>
              {shortCard(cardName)} · {holderLabel(offer.account)}
            </span>
          )}
          {showCard && <span aria-hidden>·</span>}
          {done || past ? (
            <span>{offer.period.label}</span>
          ) : (
            <span
              className={cn(
                "tabular",
                level === "soon" && "font-medium text-warning",
                level === "urgent" && "font-semibold text-destructive",
              )}
            >
              {deadlineText(offer.period.days_left)} · ends {lastDay(offer.period.end)}
            </span>
          )}
          {offer.uses > 1 && (
            <span className="inline-flex items-center gap-1.5">
              <span aria-hidden>·</span>
              <UsePips uses={offer.uses} used={usedCount} />
              <span className="tabular">
                {usedCount}/{offer.uses}
              </span>
            </span>
          )}
        </div>

        {!done && !past && offer.how_to_use && (
          <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground/90">{offer.how_to_use}</p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {!activation && (
          <div className="mr-1 text-right">
            <div className={cn("tabular text-sm font-semibold", done ? "text-success" : "text-foreground")}>
              {done ? money(offer.captured) : money(offer.remaining || offer.value)}
            </div>
            <div className="text-[11px] text-muted-foreground">
              {done ? (offer.state === "ignored" ? "skipped" : "captured") : offer.state === "pending" ? "expected" : "left"}
            </div>
          </div>
        )}

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-9" aria-label={`Actions for ${offer.name}`}>
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            {!done && (
              <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
                Tracked automatically. Correct it only if it is wrong.
              </DropdownMenuLabel>
            )}
            {!done && (
              <DropdownMenuItem onSelect={() => setOverride(offer, "used")}>
                <Check className="size-4" />
                {activation ? "I activated it" : "I used it"}
              </DropdownMenuItem>
            )}
            {!done && (
              <DropdownMenuItem onSelect={() => setOverride(offer, "ignored")}>
                <SkipForward className="size-4" />
                Not interested this period
              </DropdownMenuItem>
            )}
            {offer.override && (
              <DropdownMenuItem onSelect={() => setOverride(offer, null)}>
                <RotateCcw className="size-4" />
                Undo {offer.override === "ignored" ? "skip" : "mark"}
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/offers/$offerId/$accountId" params={{ offerId: offer.offer_id, accountId: offer.account.id }}>
                <History className="size-4" />
                History and evidence
              </Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  );
}
