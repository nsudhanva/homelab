import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, keys, type OverrideBody } from "./api";

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
