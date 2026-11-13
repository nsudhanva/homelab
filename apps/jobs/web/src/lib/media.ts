import { useSyncExternalStore } from "react";

const query = window.matchMedia("(min-width: 768px)");

export function useWide(): boolean {
  return useSyncExternalStore(
    (notify) => {
      query.addEventListener("change", notify);
      return () => query.removeEventListener("change", notify);
    },
    () => query.matches,
  );
}
