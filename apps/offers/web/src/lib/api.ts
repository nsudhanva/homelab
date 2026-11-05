export type Account = { id: string; name: string; holder: string | null; last4: string | null };

export type State =
  | "credited"
  | "partial"
  | "pending"
  | "used"
  | "unused"
  | "ignored"
  | "to_activate"
  | "activated";

export type OfferStatus = {
  offer_id: string;
  card_id: string;
  name: string;
  kind: "credit" | "activation";
  value: number;
  uses: number;
  how_to_use: string | null;
  account: Account;
  period: { start: string; end: string; label: string; days_left: number };
  state: State;
  captured: number;
  remaining: number;
  override: "used" | "ignored" | null;
};

export type Txn = {
  id: string;
  date: string;
  amount: number;
  payee: string;
  description: string;
  account: Account | null;
};

export type Evidence = {
  kind: "credit" | "usage";
  source: "rule" | "ai" | "manual";
  amount: number;
  confidence: number;
  reason: string;
  txn: Txn | null;
};

export type OfferDetail = {
  offer_id: string;
  name: string;
  cycle: string;
  card_name: string;
  account: Account;
  value: number;
  period: string;
  history: { status: OfferStatus; evidence: Evidence[] }[];
};

export type ReviewItem = {
  txn: Txn;
  offer_id: string;
  offer_name: string;
  card_name: string;
  kind: "credit" | "usage";
  ai_match: boolean;
  confidence: number;
  reason: string;
};

export type OverrideBody = {
  offer_id: string;
  account_id: string;
  period_start: string;
  status: "used" | "ignored" | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  offer: (offerId: string, accountId: string) =>
    request<OfferDetail>(`/api/offers/${encodeURIComponent(offerId)}/${encodeURIComponent(accountId)}`),
  review: () => request<ReviewItem[]>("/api/review"),
  decide: (body: { txn_id: string; offer_id: string; match: boolean }) =>
    request<void>("/api/review", { method: "POST", body: JSON.stringify(body) }),
  override: (body: OverrideBody) =>
    request<void>("/api/override", { method: "POST", body: JSON.stringify(body) }),
};

export const keys = {
  dashboards: ["dashboard"] as const,
  review: ["review"] as const,
  offer: (offerId: string, accountId: string) => ["offer", offerId, accountId] as const,
};

export type Cell = {
  month: string;
  offer_id: string | null;
  data_from: string | null;
  span: number;
  state: State | null;
  value: number;
  captured: number;
  remaining: number;
  uses: number;
  used: number;
  period_start: string | null;
  period_label: string | null;
  days_left: number | null;
  current: boolean;
  elsewhere: number;
  override: "used" | "ignored" | null;
};

export type TrackerRow = {
  offer_id: string;
  name: string;
  cycle: string;
  next_reset: string | null;
  kind: "credit" | "activation";
  in_app: boolean;
  value: number;
  period: string;
  uses: number;
  how_to_use: string | null;
  cells: Cell[];
};

export type TrackerCard = {
  card_id: string;
  name: string;
  issuer: string;
  annual_fee: number;
  account: Account;
  year_captured: number;
  fee: {
    fee_date: string | null;
    anniversary_month: number | null;
    source: "fee" | "catalog" | null;
    year_start: string | null;
    year_end: string | null;
    year_captured: number;
  };
  rows: TrackerRow[];
  rewards: CardRewards | null;
  total: { captured: number; since: string | null; months: number } | null;
};

export type CardRewards = {
  currency: "cash" | "points";
  program: string | null;
  base: number;
  rules: { name: string; rate: number; detail: string }[];
  note: string | null;
};

export type Tracker = {
  today: string;
  latest_txn: string | null;
  months: string[];
  current: {
    month: string;
    available: number;
    captured: number;
    open: number;
    missed: number;
    used_count: number;
    open_count: number;
    ending_soon: number;
  };
  last_run: { started_at: string; finished_at: string | null; status: string; message: string } | null;
  cards: TrackerCard[];
  captured_total: number;
  unmatched_accounts: string[];
  unlinked: Txn[];
};

export const trackerApi = {
  get: (months: number) => request<Tracker>(`/api/tracker?months=${months}`),
  key: (months: number) => ["dashboard", "tracker", months] as const,
};
