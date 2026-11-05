import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, keys, type OverrideBody, type Tracker } from "./api";

export function useOverride() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.override,
    onError: () => {
      toast.error("Could not save. Try again.");
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.dashboards });
      void client.invalidateQueries({ queryKey: ["offer"] });
    },
  });

  return {
    pending: mutation.isPending,
    set: (body: OverrideBody, name: string, label: string) =>
      mutation.mutate(body, {
        onSuccess: () => {
          if (!body.status) {
            toast("Correction removed", { description: `${name} · ${label}` });
            return;
          }
          toast.success(body.status === "used" ? `Marked used: ${name}` : `Not interested: ${name}`, {
            description: label,
            action: { label: "Undo", onClick: () => mutation.mutate({ ...body, status: null }) },
          });
        },
      }),
  };
}

export function useDecide() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: api.decide,
    onError: () => {
      toast.error("Could not save the correction. Try again.");
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

type CellMark = OverrideBody & { kind: "credit" | "activation"; name: string; label: string };

function markCell(data: Tracker, body: CellMark): Tracker {
  return {
    ...data,
    cards: data.cards.map((card) =>
      card.account.id !== body.account_id
        ? card
        : {
            ...card,
            rows: card.rows.map((row) => ({
              ...row,
              cells: row.cells.map((cell) => {
                if (cell.offer_id !== body.offer_id || cell.period_start !== body.period_start) return cell;
                if (body.status === "used")
                  return {
                    ...cell,
                    state: body.kind === "activation" ? "activated" : "used",
                    captured: cell.value,
                    remaining: 0,
                    override: "used",
                  };
                if (body.status === "ignored") return { ...cell, state: "ignored", remaining: 0, override: "ignored" };
                return cell;
              }),
            })),
          },
    ),
  };
}

/** Marks a tracker cell in place. The cell changes at once; the server confirms in the background. */
export function useCellMark() {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (body: CellMark) =>
      api.override({
        offer_id: body.offer_id,
        account_id: body.account_id,
        period_start: body.period_start,
        status: body.status,
      }),
    onMutate: async (body) => {
      await client.cancelQueries({ queryKey: ["dashboard", "tracker"] });
      const previous = client.getQueriesData<Tracker>({ queryKey: ["dashboard", "tracker"] });
      if (body.status) client.setQueriesData<Tracker>({ queryKey: ["dashboard", "tracker"] }, (d) => d && markCell(d, body));
      return { previous };
    },
    onError: (_error, _body, context) => {
      for (const [key, value] of context?.previous ?? []) client.setQueryData(key, value);
      toast.error("Could not save. Try again.");
    },
    onSuccess: (_data, body) => {
      if (!body.status) {
        toast("Mark removed", { description: `${body.name} · ${body.label}` });
        return;
      }
      const verb = body.status === "ignored" ? "Not interested" : body.kind === "activation" ? "Activated" : "Marked used";
      toast.success(`${verb}: ${body.name}`, {
        description: body.label,
        action: { label: "Undo", onClick: () => mutation.mutate({ ...body, status: null }) },
      });
    },
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.dashboards });
      void client.invalidateQueries({ queryKey: ["offer"] });
    },
  });
  return mutation;
}
