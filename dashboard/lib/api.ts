// Server-side API client. The API key stays on the server; it's never sent to
// the browser. Called from React server components.

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${API_KEY}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export type MetricsSummary = {
  calls_total: number;
  calls_today: number;
  acceptance_rate: number;
  avg_rounds_when_accepted: number | null;
  avg_final_rate: string | null;
  outcomes: Record<string, number>;
  sentiment: Record<string, number>;
  calls_by_day: { date: string; count: number }[];
};

export type CallListItem = {
  id: number;
  mc_number: string | null;
  carrier_name: string | null;
  load_id: string | null;
  outcome: string | null;
  sentiment: string | null;
  final_rate: string | null;
  rounds_used: number | null;
  agreement_reached: boolean | null;
  created_at: string;
};

export type CallListResponse = {
  calls: CallListItem[];
  total: number;
};

export type OfferItem = {
  id: number;
  round_number: number;
  carrier_offer: string;
  agent_counter: string | null;
  decision: string;
  created_at: string;
};

export type CallDetail = {
  call: CallListItem;
  transcript: string | null;
  extracted_fields: Record<string, unknown> | null;
  offers: OfferItem[];
};

export function getMetricsSummary() {
  return apiGet<MetricsSummary>("/api/v1/metrics/summary");
}

export function getCalls(limit = 50, offset = 0) {
  return apiGet<CallListResponse>(`/api/v1/calls?limit=${limit}&offset=${offset}`);
}

export function getCallDetail(id: number) {
  return apiGet<CallDetail>(`/api/v1/calls/${id}`);
}

type LoadResponse = {
  statusCode: number;
  body: { load: { reference_number: string; posted_carrier_rate: string } };
};

/** Fetch posted_carrier_rate for each unique load_id. Returns a map: ref → rate. */
export async function getPostedRatesFor(loadIds: (string | null)[]): Promise<Record<string, string>> {
  const refs = Array.from(new Set(loadIds.filter((x): x is string => !!x)));
  const results = await Promise.all(
    refs.map(async (ref) => {
      try {
        const resp = await apiGet<LoadResponse>(`/api/v1/loads/${encodeURIComponent(ref)}`);
        return [ref, resp.body.load.posted_carrier_rate] as const;
      } catch {
        return [ref, null] as const;
      }
    })
  );
  return Object.fromEntries(results.filter(([, v]) => v !== null) as [string, string][]);
}
