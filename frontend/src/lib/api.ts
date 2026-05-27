import useSWR from "swr";

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`API error: ${r.status}`);
    return r.json();
  });

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
  limit?: number;
} = {}) {
  const params = new URLSearchParams();
  if (filters.issue)     params.set("issue", filters.issue);
  if (filters.province)  params.set("province", filters.province);
  if (filters.platform)  params.set("platform", filters.platform);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
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
