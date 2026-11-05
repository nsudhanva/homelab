import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, keys, type Dashboard, type OfferStatus, type OverrideBody, type State } from "./api";

function applyOverride(offer: OfferStatus, status: OverrideBody["status"]): OfferStatus {
  if (status === "used") {
    const state: State = offer.kind === "activation" ? "activated" : "used";
    return { ...offer, state, override: "used", captured: offer.value, remaining: 0 };
  }
  if (status === "ignored") return { ...offer, state: "ignored", override: "ignored", remaining: 0 };
  return offer;
}

export function overrideBody(offer: OfferStatus, status: OverrideBody["status"]): OverrideBody {
  return { offer_id: offer.offer_id, account_id: offer.account.id, period_start: offer.period.start, status };
}

export function useOverride() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.override,
    onMutate: async (body) => {
      await client.cancelQueries({ queryKey: keys.dashboards });
      const previous = client.getQueriesData<Dashboard>({ queryKey: keys.dashboards });
      if (body.status) {
        client.setQueriesData<Dashboard>({ queryKey: keys.dashboards }, (board) =>
          board && {
            ...board,
            cards: board.cards.map((card) => ({
              ...card,
              offers: card.offers.map((o) =>
                o.offer_id === body.offer_id && o.account.id === body.account_id && o.period.start === body.period_start
                  ? applyOverride(o, body.status)
                  : o,
              ),
            })),
          },
        );
      }
      return { previous };
    },
    onError: (_error, _body, context) => {
      for (const [key, value] of context?.previous ?? []) client.setQueryData(key, value);
      toast.error("Could not save. Try again.");
    },
    onSettled: (_data, _error, body) => {
      void client.invalidateQueries({ queryKey: keys.dashboards });
      void client.invalidateQueries({ queryKey: keys.offer(body.offer_id, body.account_id) });
    },
  });

  return (offer: OfferStatus, status: OverrideBody["status"]) => {
    mutation.mutate(overrideBody(offer, status), {
      onSuccess: () => {
        if (!status) {
          toast("Mark removed", { description: offer.name });
          return;
        }
        const verb = status === "ignored" ? "Skipped" : offer.kind === "activation" ? "Activated" : "Marked used";
        toast.success(`${verb}: ${offer.name}`, {
          description: offer.period.label,
          action: { label: "Undo", onClick: () => mutation.mutate(overrideBody(offer, null)) },
        });
      },
    });
  };
}

export function useDecide() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.decide,
    onMutate: async (body) => {
      await client.cancelQueries({ queryKey: keys.review });
      const previous = client.getQueryData(keys.review);
      client.setQueryData(keys.review, (items: { txn: { id: string }; offer_id: string }[] | undefined) =>
        items?.filter((i) => !(i.txn.id === body.txn_id && i.offer_id === body.offer_id)),
      );
      return { previous };
    },
    onError: (_error, _body, context) => {
      client.setQueryData(keys.review, context?.previous);
      toast.error("Could not save the answer. Try again.");
    },
    onSuccess: (_data, body) => {
      toast.success(body.match ? "Corrected: it counts" : "Corrected: it does not count");
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.review });
      void client.invalidateQueries({ queryKey: keys.dashboards });
    },
  });
}
