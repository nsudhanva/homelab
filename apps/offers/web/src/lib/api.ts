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
  enrollment: boolean;
  how_to_use: string | null;
  valid_to: string | null;
  account: Account;
  period: { start: string; end: string; label: string; days_left: number };
  state: State;
  captured: number;
  remaining: number;
  override: "used" | "ignored" | null;
  evidence_count: number;
};

export type Card = {
  card_id: string;
  name: string;
  issuer: string;
  account: Account;
  annual_fee: number;
  year_captured: number;
  year_missed: number;
  offers: OfferStatus[];
};

export type Txn = {
  id: string;
  date: string;
  amount: number;
  payee: string;
  description: string;
  account: Account | null;
};

export type Dashboard = {
  today: string;
  as_of: string;
  month: string;
  months: string[];
  last_run: { started_at: string; finished_at: string | null; status: string; message: string } | null;
  totals: {
    open_now: number;
    captured_now: number;
    to_review: number;
    captured_year: number;
    missed_year: number;
    annual_fees: number;
  };
  cards: Card[];
  unlinked: Txn[];
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
  dashboard: (month?: string) => request<Dashboard>(`/api/dashboard${month ? `?month=${month}` : ""}`),
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
  dashboard: (month?: string) => ["dashboard", month ?? "current"] as const,
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
  kind: "credit" | "activation";
  in_app: boolean;
  value: number;
  period: string;
  uses: number;
  how_to_use: string | null;
  enrollment: boolean;
  cells: Cell[];
};

export type TrackerCard = {
  card_id: string;
  name: string;
  issuer: string;
  annual_fee: number;
  account: Account;
  year_captured: number;
  rows: TrackerRow[];
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
  last_run: Dashboard["last_run"];
  cards: TrackerCard[];
};

export const trackerApi = {
  get: (months: number) => request<Tracker>(`/api/tracker?months=${months}`),
  key: (months: number) => ["dashboard", "tracker", months] as const,
};
