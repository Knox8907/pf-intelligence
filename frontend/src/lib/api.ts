import useSWR from "swr";

export function getToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("pf_token") : null;
}

const fetcher = (url: string) => {
  const token = getToken();
  return fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }).then((r) => {
    if (r.status === 401) {
      localStorage.removeItem("pf_token");
      window.location.reload();
    }
    if (!r.ok) throw new Error(`API error: ${r.status}`);
    return r.json();
  });
};

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  const data = await res.json();
  return data.access_token;
}

export function useDashboardSummary() {
  return useSWR("/api/dashboard/summary", fetcher, { refreshInterval: 60_000 });
}

export function useIssueFrequency() {
  return useSWR("/api/dashboard/issues", fetcher, { refreshInterval: 120_000 });
}

export function useProvinceScores() {
  return useSWR("/api/dashboard/provinces", fetcher, { refreshInterval: 120_000 });
}

export function usePosts(filters: {
  issue?: string;
  province?: string;
  platform?: string;
  sentiment?: string;
  source?: string;
  limit?: number;
} = {}) {
  const params = new URLSearchParams();
  if (filters.issue)     params.set("issue", filters.issue);
  if (filters.province)  params.set("province", filters.province);
  if (filters.platform)  params.set("platform", filters.platform);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.source)    params.set("source", filters.source);
  params.set("limit", String(filters.limit || 20));

  return useSWR(`/api/posts?${params}`, fetcher, { refreshInterval: 30_000 });
}

export function usePolls() {
  return useSWR("/api/polls", fetcher, { refreshInterval: 10_000 });
}

export async function submitPollResponse(payload: {
  poll_id: number;
  option_id: number;
  province?: string;
  age_group?: string;
}) {
  const res = await fetch("/api/polls/respond", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit response");
  }
  return res.json();
}

// ── Vote Protection ────────────────────────────────────────────

export function useVoterRegisterSummary() {
  return useSWR("/api/voter-register/summary", fetcher, { refreshInterval: 30_000 });
}

export function useDistricts(provinceNum: string | null) {
  return useSWR(
    provinceNum ? `/api/voter-register/districts?province_num=${provinceNum}` : null,
    fetcher
  );
}

export function useConstituencies(districtCode: string | null) {
  return useSWR(
    districtCode ? `/api/voter-register/constituencies?district_code=${districtCode}` : null,
    fetcher
  );
}

export function useWards(constituencyNum: string | null) {
  return useSWR(
    constituencyNum ? `/api/voter-register/wards?constituency_num=${constituencyNum}` : null,
    fetcher
  );
}

export function usePollingStations(wardCode: string | null) {
  return useSWR(
    wardCode ? `/api/voter-register/polling-stations?ward_code=${wardCode}` : null,
    fetcher,
    { refreshInterval: 15_000 }
  );
}

export function useTabulationOverview() {
  return useSWR("/api/tabulation/overview", fetcher, { refreshInterval: 15_000 });
}

export async function submitTabulation(payload: {
  polling_district_code: string;
  votes_cast: number;
  pf_votes?: number;
  upnd_votes?: number;
  other_votes?: number;
  rejected_ballots?: number;
  agent_name?: string;
  notes?: string;
}) {
  const token = getToken();
  const res = await fetch("/api/tabulation/submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit tabulation");
  }
  return res.json();
}
