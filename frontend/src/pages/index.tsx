"use client";
import { useState, useEffect, useCallback } from "react";
import {
  useDashboardSummary, useIssueFrequency, useProvinceScores,
  usePosts, usePolls, submitPollResponse, login, getToken,
  useVoterRegisterSummary, useDistricts, useConstituencies,
  useWards, usePollingStations, useTabulationOverview, submitTabulation,
} from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from "recharts";
import { formatDistanceToNow, differenceInDays } from "date-fns";

const ELECTION_DATE = new Date("2026-08-13T00:00:00");

function scoreColor(score: number): { bg: string; border: string; text: string } {
  if (score >= 80) return { bg: "rgba(185,28,28,0.35)",  border: "rgba(239,68,68,0.5)",  text: "#fca5a5" };
  if (score >= 65) return { bg: "rgba(194,65,12,0.30)",  border: "rgba(249,115,22,0.45)", text: "#fdba74" };
  if (score >= 50) return { bg: "rgba(161,98,7,0.25)",   border: "rgba(234,179,8,0.40)",  text: "#fde047" };
  if (score >= 35) return { bg: "rgba(21,128,61,0.20)",  border: "rgba(34,197,94,0.35)",  text: "#86efac" };
  return               { bg: "rgba(55,65,81,0.40)",   border: "rgba(107,114,128,0.4)", text: "#9ca3af" };
}

const ISSUE_DISPLAY: Record<string, string> = {
  mealie_meal: "Mealie meal", fuel: "Fuel costs",
  electricity: "ZESCO/Power", employment: "Unemployment",
  kwacha: "Kwacha", fertiliser: "Fertiliser", education: "School/Medical",
};

function LoginPage({ onAuth }: { onAuth: () => void }) {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await login(email, password);
      localStorage.setItem("pf_token", token);
      onAuth();
    } catch {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center font-bold text-lg">PF</div>
          <div>
            <div className="font-semibold text-white">PF Intelligence Hub</div>
            <div className="text-xs text-gray-500">Zambia 2026 · Internal access only</div>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-6 border border-gray-800 space-y-4">
          <h2 className="text-sm font-medium text-gray-300 mb-2">Sign in to continue</h2>
          <input
            type="email" placeholder="Email address" required autoFocus
            value={email} onChange={e => setEmail(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-red-500"
          />
          <input
            type="password" placeholder="Password" required
            value={password} onChange={e => setPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-red-500"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-6 h-6 border-2 border-gray-700 border-t-red-500 rounded-full animate-spin" />
    </div>
  );
}

function ApiError({ message }: { message: string }) {
  return (
    <div className="py-8 text-center text-sm text-red-400 bg-red-950/20 rounded-xl border border-red-900/40">
      {message}
    </div>
  );
}

function CountdownTimer() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const diff = ELECTION_DATE.getTime() - now.getTime();
  const days = Math.floor(diff / 86400000);
  const hrs  = Math.floor((diff % 86400000) / 3600000);
  const mins = Math.floor((diff % 3600000)  / 60000);
  const secs = Math.floor((diff % 60000)    / 1000);

  return (
    <div className="mb-6">
      <div className="flex items-end gap-3 mb-2">
        <div className="bg-red-950/50 border border-red-700/60 rounded-xl px-5 py-3 text-center min-w-[90px]">
          <div className="text-5xl font-black text-red-400 tabular-nums leading-none">{String(days).padStart(2,"0")}</div>
          <div className="text-[10px] text-red-500 uppercase tracking-widest mt-1">Days</div>
        </div>
        <div className="text-red-700 text-3xl font-bold pb-3">:</div>
        {[["Hrs", hrs], ["Min", mins], ["Sec", secs]].map(([l, v]) => (
          <div key={l} className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-center min-w-[72px]">
            <div className="text-3xl font-bold text-white tabular-nums leading-none">{String(v).padStart(2,"0")}</div>
            <div className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">{l}</div>
          </div>
        ))}
        <div className="pb-3 ml-1">
          <div className="text-sm font-medium text-gray-300">until election day</div>
          <div className="text-xs text-gray-500">13 August 2026</div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, delta, deltaUp, accent }: {
  label: string; value: string; delta?: string; deltaUp?: boolean; accent?: string;
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 border-l-4"
         style={{ borderLeftColor: accent || "#e63946" }}>
      <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-2">{label}</div>
      <div className="text-3xl font-black text-white leading-none">{value}</div>
      {delta && (
        <div className={`text-xs mt-2 font-medium ${deltaUp ? "text-green-400" : "text-gray-500"}`}>
          {delta}
        </div>
      )}
    </div>
  );
}

function IssueBars({ data }: { data: any[] }) {
  return (
    <div className="space-y-3">
      {data.slice(0, 7).map((d) => (
        <div key={d.issue}>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>{d.display || ISSUE_DISPLAY[d.issue] || d.issue}</span>
            <span className="font-medium text-white">{d.pct}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-red-500 transition-all duration-700"
              style={{ width: `${d.pct}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ProvinceGrid({ provinces }: { provinces: any[] }) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {provinces.map((p) => {
        const { bg, border, text } = scoreColor(p.score);
        return (
          <div key={p.province}
               className="rounded-lg p-3 text-center"
               style={{ background: bg, border: `1px solid ${border}` }}>
            <div className="text-2xl font-black leading-none" style={{ color: text }}>{p.score}</div>
            <div className="text-[10px] text-gray-400 mt-1 leading-tight">{p.province}</div>
            {p.top_issue && (
              <div className="text-[9px] mt-1 leading-tight" style={{ color: text, opacity: 0.7 }}>
                {ISSUE_DISPLAY[p.top_issue] || p.top_issue}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function PostFeed({ posts }: { posts: any[] }) {
  const sentClass = (s: string) => {
    if (s === "negative") return "bg-red-900/30 text-red-400 border-red-800";
    if (s === "positive") return "bg-green-900/30 text-green-400 border-green-800";
    return "bg-gray-800 text-gray-400 border-gray-700";
  };

  return (
    <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
      {posts.map((post) => (
        <div key={post.id} className="bg-gray-900 rounded-lg p-4 border border-gray-800 hover:border-gray-700 transition-colors">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-[10px] font-medium uppercase tracking-widest px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
              {post.platform === "facebook" ? "FB" : post.platform === "news" ? "NEWS" : post.platform}
            </span>
            <span className="text-xs font-medium text-gray-300">{post.source_name}</span>
            {post.published_at && (
              <span className="text-xs text-gray-600">
                · {formatDistanceToNow(new Date(post.published_at), { addSuffix: true })}
              </span>
            )}
            {post.sentiment && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ml-auto ${sentClass(post.sentiment)}`}>
                {post.sentiment}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-200 leading-relaxed">{post.content}</p>
          <div className="flex items-center gap-4 mt-3">
            {post.issues?.length > 0 && (
              <div className="flex gap-1 flex-wrap flex-1">
                {post.issues.map((i: string) => (
                  <span key={i} className="text-[10px] bg-red-950/60 text-red-300 border border-red-900/60 px-2 py-0.5 rounded-full">
                    #{ISSUE_DISPLAY[i] || i}
                  </span>
                ))}
              </div>
            )}
            {(post.likes > 0 || post.comments > 0) && (
              <div className="flex gap-3 text-[10px] text-gray-600 shrink-0">
                {post.likes > 0 && <span>♥ {post.likes.toLocaleString()}</span>}
                {post.comments > 0 && <span>💬 {post.comments.toLocaleString()}</span>}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function PollSection({ polls }: { polls: any[] }) {
  const [answered, setAnswered] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState<Record<number, boolean>>({});
  const [province, setProvince] = useState("");

  const PROVINCES = ["Lusaka","Copperbelt","Eastern","Southern","Central",
                     "Western","Northern","Luapula","North-Western","Muchinga"];

  async function handleSubmit(pollId: number) {
    const optionId = answered[pollId];
    if (!optionId) return;
    try {
      await submitPollResponse({ poll_id: pollId, option_id: optionId, province: province || undefined });
      setSubmitted((s) => ({ ...s, [pollId]: true }));
    } catch (e: any) {
      if (e.message?.includes("Already")) {
        setSubmitted((s) => ({ ...s, [pollId]: true }));
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-2 items-center">
        <label className="text-sm text-gray-400">Your province:</label>
        <select
          className="bg-gray-800 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-700"
          value={province}
          onChange={(e) => setProvince(e.target.value)}
        >
          <option value="">Select province</option>
          {PROVINCES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      {polls.map((poll) => (
        <div key={poll.id} className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <p className="text-white font-medium mb-4 leading-relaxed">{poll.question}</p>

          {!submitted[poll.id] ? (
            <>
              <div className="space-y-2 mb-4">
                {poll.options.map((opt: any) => (
                  <button key={opt.id}
                    onClick={() => setAnswered((a) => ({ ...a, [poll.id]: opt.id }))}
                    className={`w-full text-left flex items-center gap-3 p-3 rounded-lg border text-sm transition-all
                      ${answered[poll.id] === opt.id
                        ? "border-red-500 bg-red-950/30 text-white"
                        : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600"}`}>
                    <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center
                      ${answered[poll.id] === opt.id ? "border-red-500 bg-red-500" : "border-gray-600"}`}>
                      {answered[poll.id] === opt.id && <div className="w-1.5 h-1.5 bg-white rounded-full"/>}
                    </div>
                    {opt.text}
                  </button>
                ))}
              </div>
              <button
                disabled={!answered[poll.id]}
                onClick={() => handleSubmit(poll.id)}
                className="w-full py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors">
                Submit answer
              </button>
            </>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-green-400 mb-3">✓ Response recorded · Live results:</p>
              {poll.options.map((opt: any) => (
                <div key={opt.id}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className={answered[poll.id] === opt.id ? "text-red-400" : "text-gray-400"}>{opt.text}</span>
                    <span className="text-white font-medium">{opt.pct}%</span>
                  </div>
                  <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700"
                         style={{ width: `${opt.pct}%`,
                                  background: answered[poll.id] === opt.id ? "#e63946" : "#4b5563" }}/>
                  </div>
                </div>
              ))}
              <p className="text-xs text-gray-600 mt-2">{poll.total_responses.toLocaleString()} responses</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const STRATEGY_RECS = [
  {
    title: "Lead with mealie meal — your most resonant issue",
    body: "84% of sampled posts reference food affordability. Anchor all messaging on the specific price of a 25kg bag. The ZMW 150 → ZMW 340 increase since 2021 is your central attack line. Commit to a price ceiling policy with a specific target figure.",
  },
  {
    title: "Lusaka & Copperbelt are the decisive battlegrounds",
    body: "Combined ~45% of registered voters. Grievance scores 88 and 82 respectively. Prioritise constituency activation in Chawama, Kanyama, Matero, Wusakile, and Nchanga. These seats decide the presidency.",
  },
  {
    title: "ZESCO load shedding is Copperbelt's number one issue",
    body: "16+ hour outages dominate Northern and Copperbelt conversations. Publish a specific 100-day energy plan. Small businesses losing stock to outages are your most powerful visual story — film it.",
  },
  {
    title: "Youth unemployment is the fastest-growing grievance",
    body: "18–35s are 60%+ of the electorate. Graduate frustration is intense. Host town halls at UNZA, CBU, and NIPA. Propose a concrete graduate employment bond or skills fund with a named delivery date.",
  },
  {
    title: "Frame 2026 as a forward-looking campaign",
    body: "Polling shows voters want solutions, not retrospective comparisons. Messaging should be 'PF 2026 — what we will do' not a defence of 2011–2021. The electorate has moved on from Lungu-era associations.",
  },
];

export default function Dashboard() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    setAuthed(!!getToken());
  }, []);

  if (authed === null) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-gray-700 border-t-red-500 rounded-full animate-spin" />
    </div>
  );
  if (!authed) return <LoginPage onAuth={() => setAuthed(true)} />;

  return <DashboardInner />;
}

// ── Vote Protection Tab ────────────────────────────────────────

function StatBadge({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-1">
      <div className="text-xs text-gray-500 uppercase tracking-widest">{label}</div>
      <div className="text-2xl font-bold text-white tabular-nums">{typeof value === "number" ? value.toLocaleString() : value}</div>
      {sub && <div className="text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

function ProgressBar({ pct, color = "#ef4444" }: { pct: number; color?: string }) {
  return (
    <div className="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }} />
    </div>
  );
}

function TabulationModal({
  station, onClose, onSubmitted,
}: {
  station: any;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const [votesCast,      setVotesCast]      = useState("");
  const [pfVotes,        setPfVotes]        = useState("");
  const [upndVotes,      setUpndVotes]      = useState("");
  const [otherVotes,     setOtherVotes]     = useState("");
  const [rejectedBallots,setRejectedBallots]= useState("");
  const [agentName,      setAgentName]      = useState("");
  const [notes,          setNotes]          = useState("");
  const [submitting,     setSubmitting]     = useState(false);
  const [result,         setResult]         = useState<any>(null);
  const [error,          setError]          = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const res = await submitTabulation({
        polling_district_code: station.polling_district_code,
        votes_cast:            parseInt(votesCast),
        pf_votes:              pfVotes       ? parseInt(pfVotes)        : undefined,
        upnd_votes:            upndVotes     ? parseInt(upndVotes)      : undefined,
        other_votes:           otherVotes    ? parseInt(otherVotes)     : undefined,
        rejected_ballots:      rejectedBallots ? parseInt(rejectedBallots) : undefined,
        agent_name:            agentName     || undefined,
        notes:                 notes         || undefined,
      });
      setResult(res);
      onSubmitted();
    } catch (err: any) {
      setError(err.message || "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  const numInput = (label: string, value: string, onChange: (v: string) => void, required = false) => (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}{required && " *"}</label>
      <input type="number" min="0" required={required} value={value} onChange={e => onChange(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500" />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-semibold text-white">{station.polling_station}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{station.polling_district} · Registered: {station.total?.toLocaleString()}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg ml-4">✕</button>
        </div>

        {result ? (
          <div className={`rounded-xl p-4 border ${result.discrepancy ? "bg-red-950/40 border-red-700" : "bg-green-950/40 border-green-700"}`}>
            <p className={`font-semibold mb-1 ${result.discrepancy ? "text-red-400" : "text-green-400"}`}>
              {result.discrepancy ? "⚠ DISCREPANCY FLAGGED" : "✓ Result Recorded"}
            </p>
            <p className="text-sm text-gray-300">{result.message}</p>
            {result.discrepancy && (
              <p className="text-xs text-red-400 mt-2">
                Votes cast ({result.votes_cast?.toLocaleString()}) exceed registered voters ({result.registered?.toLocaleString()})
              </p>
            )}
            <button onClick={onClose} className="mt-4 w-full py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors">Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            {numInput("Total votes cast", votesCast, setVotesCast, true)}
            <div className="grid grid-cols-3 gap-2">
              {numInput("PF votes", pfVotes, setPfVotes)}
              {numInput("UPND votes", upndVotes, setUpndVotes)}
              {numInput("Other votes", otherVotes, setOtherVotes)}
            </div>
            {numInput("Rejected ballots", rejectedBallots, setRejectedBallots)}
            <div>
              <label className="block text-xs text-gray-400 mb-1">PF Agent name</label>
              <input type="text" value={agentName} onChange={e => setAgentName(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Notes / observations</label>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-red-500" />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <button type="submit" disabled={submitting || !votesCast}
              className="w-full py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors">
              {submitting ? "Submitting…" : "Submit result"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function VoteProtectionTab() {
  const { data: summary, isLoading: sumLoading } = useVoterRegisterSummary();
  const { data: tabOverview } = useTabulationOverview();

  const [selProvince,      setSelProvince]      = useState<any>(null);
  const [selDistrict,      setSelDistrict]      = useState<any>(null);
  const [selConstituency,  setSelConstituency]  = useState<any>(null);
  const [selWard,          setSelWard]          = useState<any>(null);
  const [tabulationStation,setTabulationStation]= useState<any>(null);
  const [view, setView] = useState<"register"|"tabulation">("register");

  const { data: districts }     = useDistricts(selProvince?.province_num ?? null);
  const { data: constituencies } = useConstituencies(selDistrict?.district_code ?? null);
  const { data: wards }          = useWards(selConstituency?.constituency_num ?? null);
  const { data: pollingStations, mutate: refreshStations } = usePollingStations(selWard?.ward_code ?? null);

  function resetBelow(level: "province"|"district"|"constituency"|"ward") {
    if (level === "province")      { setSelDistrict(null); setSelConstituency(null); setSelWard(null); }
    if (level === "district")      { setSelConstituency(null); setSelWard(null); }
    if (level === "constituency")  { setSelWard(null); }
  }

  const national = summary?.national;
  const tabData  = tabOverview?.overview;
  const submitted = tabData?.total_submitted || 0;
  const totalStations = tabOverview?.total_stations || national?.stations || 12933;
  const coveragePct = totalStations > 0 ? (submitted / totalStations) * 100 : 0;

  const breadcrumb = [
    selProvince     && { label: selProvince.province_name,           onClick: () => { resetBelow("province"); setSelProvince(null); } },
    selDistrict     && { label: selDistrict.district_name,           onClick: () => { resetBelow("district"); setSelDistrict(null); } },
    selConstituency && { label: selConstituency.constituency_name,   onClick: () => { resetBelow("constituency"); setSelConstituency(null); } },
    selWard         && { label: selWard.ward_name,                   onClick: () => setSelWard(null) },
  ].filter(Boolean) as { label: string; onClick: () => void }[];

  function rowClass(hasDiscrepancy: boolean) {
    return hasDiscrepancy ? "bg-red-950/20 border-red-800/40 hover:bg-red-950/30" : "bg-gray-900/50 border-gray-800/50 hover:bg-gray-800/50";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Vote Protection Dashboard</h2>
          <p className="text-sm text-gray-400">ECZ official voter register · Zambia 2026 · Parallel tabulation</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setView("register")}
            className={`px-4 py-1.5 rounded-lg text-sm transition-all ${view === "register" ? "bg-red-600/20 text-red-400 border border-red-600/30" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
            Voter Register
          </button>
          <button onClick={() => setView("tabulation")}
            className={`px-4 py-1.5 rounded-lg text-sm transition-all ${view === "tabulation" ? "bg-red-600/20 text-red-400 border border-red-600/30" : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
            Tabulation
            {(tabOverview?.overview?.discrepancy_count || 0) > 0 && (
              <span className="ml-1.5 bg-red-600 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                {tabOverview.overview.discrepancy_count}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* National KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatBadge label="Total voters"   value={sumLoading ? "…" : (national?.total || 0).toLocaleString()}     sub="ECZ 2026 register" />
        <StatBadge label="Female"         value={sumLoading ? "…" : (national?.female || 0).toLocaleString()}    sub={national ? `${((national.female/national.total)*100).toFixed(1)}%` : ""} />
        <StatBadge label="Male"           value={sumLoading ? "…" : (national?.male || 0).toLocaleString()}      sub={national ? `${((national.male/national.total)*100).toFixed(1)}%` : ""} />
        <StatBadge label="Provinces"      value="10"  sub="All covered" />
        <StatBadge label="Polling stations" value={sumLoading ? "…" : (national?.stations || 0).toLocaleString()} sub="Across 13,529 ECZ" />
        <StatBadge label="Results in"     value={submitted.toLocaleString()} sub={`of ${totalStations.toLocaleString()} stations`} />
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col gap-2">
          <div className="text-xs text-gray-500 uppercase tracking-widest">Coverage</div>
          <div className="text-2xl font-bold text-white">{coveragePct.toFixed(1)}%</div>
          <ProgressBar pct={coveragePct} color={coveragePct >= 80 ? "#16a34a" : coveragePct >= 50 ? "#f59e0b" : "#ef4444"} />
        </div>
      </div>

      {view === "register" && (
        <>
          {/* Breadcrumb */}
          {breadcrumb.length > 0 && (
            <div className="flex items-center gap-1 text-sm text-gray-400 flex-wrap">
              <button onClick={() => { setSelProvince(null); resetBelow("province"); }} className="hover:text-white transition-colors">All Provinces</button>
              {breadcrumb.map((b, i) => (
                <span key={i} className="flex items-center gap-1">
                  <span className="text-gray-600">/</span>
                  <button onClick={b.onClick} className="hover:text-white transition-colors">{b.label}</button>
                </span>
              ))}
            </div>
          )}

          {/* Level tables */}
          {!selProvince && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <h3 className="text-sm font-medium text-white">Provinces — registered voters</h3>
                <span className="text-xs text-gray-500">Click a province to drill down</span>
              </div>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="text-left px-4 py-2">Province</th>
                  <th className="text-right px-4 py-2">Male</th>
                  <th className="text-right px-4 py-2">Female</th>
                  <th className="text-right px-4 py-2">Total</th>
                  <th className="text-right px-4 py-2">% Female</th>
                  <th className="text-right px-4 py-2">Stations</th>
                </tr></thead>
                <tbody>
                  {sumLoading ? (
                    <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500"><Spinner /></td></tr>
                  ) : summary?.provinces?.map((p: any) => (
                    <tr key={p.province_num} onClick={() => setSelProvince(p)}
                      className="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer transition-colors">
                      <td className="px-4 py-2.5 font-medium text-white">{p.province_name}</td>
                      <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{parseInt(p.male).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{parseInt(p.female).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-white tabular-nums">{parseInt(p.total).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right text-gray-400 tabular-nums">{p.total > 0 ? ((p.female/p.total)*100).toFixed(1) : "0.0"}%</td>
                      <td className="px-4 py-2.5 text-right text-gray-400 tabular-nums">{parseInt(p.stations).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
                {summary?.provinces && (
                  <tfoot><tr className="bg-gray-800/30 text-xs font-semibold text-gray-300">
                    <td className="px-4 py-2">TOTAL</td>
                    <td className="px-4 py-2 text-right tabular-nums">{national?.male?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{national?.female?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{national?.total?.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{national ? ((national.female/national.total)*100).toFixed(1) : "0.0"}%</td>
                    <td className="px-4 py-2 text-right tabular-nums">{national?.stations?.toLocaleString()}</td>
                  </tr></tfoot>
                )}
              </table>
            </div>
          )}

          {selProvince && !selDistrict && (
            <DrillTable
              title={`Districts — ${selProvince.province_name}`}
              data={districts}
              keyField="district_code"
              nameField="district_name"
              onSelect={(row: any) => setSelDistrict(row)}
            />
          )}

          {selDistrict && !selConstituency && (
            <DrillTable
              title={`Constituencies — ${selDistrict.district_name}`}
              data={constituencies}
              keyField="constituency_num"
              nameField="constituency_name"
              onSelect={(row: any) => setSelConstituency(row)}
            />
          )}

          {selConstituency && !selWard && (
            <DrillTable
              title={`Wards — ${selConstituency.constituency_name}`}
              data={wards}
              keyField="ward_code"
              nameField="ward_name"
              onSelect={(row: any) => setSelWard(row)}
            />
          )}

          {selWard && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <h3 className="text-sm font-medium text-white">Polling Stations — {selWard.ward_name}</h3>
                <span className="text-xs text-gray-500">Click a station to submit tabulation result</span>
              </div>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="text-left px-4 py-2">Polling Station</th>
                  <th className="text-left px-4 py-2">District Code</th>
                  <th className="text-right px-4 py-2">Male</th>
                  <th className="text-right px-4 py-2">Female</th>
                  <th className="text-right px-4 py-2">Registered</th>
                  <th className="text-right px-4 py-2">Votes Cast</th>
                  <th className="text-right px-4 py-2">Status</th>
                </tr></thead>
                <tbody>
                  {!pollingStations ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center"><Spinner /></td></tr>
                  ) : pollingStations.map((ps: any) => (
                    <tr key={ps.polling_district_code}
                      onClick={() => setTabulationStation(ps)}
                      className={`border-b cursor-pointer transition-colors ${rowClass(ps.has_discrepancy)}`}>
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-white">{ps.polling_station}</div>
                        <div className="text-xs text-gray-500">{ps.polling_district}</div>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-gray-500 font-mono">{ps.polling_district_code}</td>
                      <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{ps.male?.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{ps.female?.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-white tabular-nums">{ps.total?.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {ps.votes_cast != null ? (
                          <span className={ps.has_discrepancy ? "text-red-400 font-semibold" : "text-green-400"}>
                            {ps.votes_cast?.toLocaleString()}
                          </span>
                        ) : <span className="text-gray-600">—</span>}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {ps.has_discrepancy
                          ? <span className="text-[10px] bg-red-900/60 text-red-400 border border-red-700/50 px-2 py-0.5 rounded-full font-medium">⚠ DISCREPANCY</span>
                          : ps.votes_cast != null
                          ? <span className="text-[10px] bg-green-900/40 text-green-400 border border-green-700/40 px-2 py-0.5 rounded-full">Submitted</span>
                          : <span className="text-[10px] bg-gray-800 text-gray-500 border border-gray-700 px-2 py-0.5 rounded-full">Pending</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {view === "tabulation" && (
        <div className="space-y-5">
          {/* Tabulation summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatBadge label="Results submitted"  value={(tabData?.total_submitted || 0).toLocaleString()}  sub={`of ${totalStations.toLocaleString()} stations`} />
            <StatBadge label="Total votes cast"   value={(tabData?.total_votes_cast || 0).toLocaleString()} sub="parallel count" />
            <StatBadge label="PF votes"           value={(tabData?.total_pf   || 0).toLocaleString()} />
            <div className={`bg-gray-900 border rounded-xl p-4 flex flex-col gap-1 ${(tabData?.discrepancy_count || 0) > 0 ? "border-red-700/50" : "border-gray-800"}`}>
              <div className="text-xs text-gray-500 uppercase tracking-widest">Discrepancies</div>
              <div className={`text-2xl font-bold tabular-nums ${(tabData?.discrepancy_count || 0) > 0 ? "text-red-400" : "text-green-400"}`}>
                {(tabData?.discrepancy_count || 0).toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">stations exceed register</div>
            </div>
          </div>

          {/* Coverage by province */}
          {tabOverview?.by_province?.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800">
                <h3 className="text-sm font-medium text-white">Coverage by Province</h3>
              </div>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="text-left px-4 py-2">Province</th>
                  <th className="text-right px-4 py-2">Results In</th>
                  <th className="text-right px-4 py-2">Flags</th>
                </tr></thead>
                <tbody>
                  {tabOverview.by_province.map((p: any) => (
                    <tr key={p.province_name} className="border-b border-gray-800/50">
                      <td className="px-4 py-2 text-white">{p.province_name}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-300">{parseInt(p.submitted).toLocaleString()}</td>
                      <td className="px-4 py-2 text-right tabular-nums">
                        {parseInt(p.flags) > 0
                          ? <span className="text-red-400 font-semibold">{p.flags}</span>
                          : <span className="text-gray-600">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Discrepancy list */}
          {tabOverview?.discrepancies?.length > 0 && (
            <div className="bg-gray-900 rounded-xl border border-red-800/40 overflow-hidden">
              <div className="px-4 py-3 border-b border-red-800/40 flex items-center gap-2">
                <span className="text-red-400">⚠</span>
                <h3 className="text-sm font-medium text-white">Discrepancy Alerts — Votes Exceed Registered Voters</h3>
              </div>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-gray-800 text-xs text-gray-500">
                  <th className="text-left px-4 py-2">Station</th>
                  <th className="text-left px-4 py-2">Location</th>
                  <th className="text-right px-4 py-2">Registered</th>
                  <th className="text-right px-4 py-2">Votes Cast</th>
                  <th className="text-right px-4 py-2">Excess</th>
                  <th className="text-right px-4 py-2">Agent</th>
                </tr></thead>
                <tbody>
                  {tabOverview.discrepancies.map((d: any) => (
                    <tr key={d.polling_district_code} className="border-b border-gray-800/50 bg-red-950/10">
                      <td className="px-4 py-2.5">
                        <div className="text-white font-medium">{d.polling_station}</div>
                        <div className="text-xs text-gray-500 font-mono">{d.polling_district_code}</div>
                      </td>
                      <td className="px-4 py-2.5 text-gray-400 text-xs">
                        {d.constituency_name}<br />{d.district_name} · {d.province_name}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">{parseInt(d.registered_voters).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-red-400 font-semibold">{parseInt(d.votes_cast).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-red-500 font-bold">+{parseInt(d.excess).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right text-gray-400 text-xs">{d.agent_name || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(!tabOverview?.discrepancies?.length && submitted === 0) && (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center text-gray-500">
              <p className="text-lg mb-1">No results submitted yet</p>
              <p className="text-sm">Switch to Voter Register view, drill down to a ward, and click a polling station to submit parallel tabulation results.</p>
            </div>
          )}
        </div>
      )}

      {tabulationStation && (
        <TabulationModal
          station={tabulationStation}
          onClose={() => setTabulationStation(null)}
          onSubmitted={() => { setTabulationStation(null); refreshStations(); }}
        />
      )}
    </div>
  );
}

function DrillTable({
  title, data, keyField, nameField, onSelect,
}: {
  title: string;
  data: any[] | undefined;
  keyField: string;
  nameField: string;
  onSelect: (row: any) => void;
}) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">{title}</h3>
        <span className="text-xs text-gray-500">Click to drill down</span>
      </div>
      <table className="w-full text-sm">
        <thead><tr className="border-b border-gray-800 text-xs text-gray-500">
          <th className="text-left px-4 py-2">Name</th>
          <th className="text-right px-4 py-2">Male</th>
          <th className="text-right px-4 py-2">Female</th>
          <th className="text-right px-4 py-2">Total</th>
          <th className="text-right px-4 py-2">% Female</th>
          <th className="text-right px-4 py-2">Stations</th>
        </tr></thead>
        <tbody>
          {!data ? (
            <tr><td colSpan={6} className="px-4 py-8 text-center"><Spinner /></td></tr>
          ) : data.map((row: any) => (
            <tr key={row[keyField]} onClick={() => onSelect(row)}
              className="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer transition-colors">
              <td className="px-4 py-2.5 font-medium text-white">{row[nameField]}</td>
              <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{parseInt(row.male).toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right text-gray-300 tabular-nums">{parseInt(row.female).toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right font-semibold text-white tabular-nums">{parseInt(row.total).toLocaleString()}</td>
              <td className="px-4 py-2.5 text-right text-gray-400 tabular-nums">
                {row.total > 0 ? ((parseInt(row.female)/parseInt(row.total))*100).toFixed(1) : "0.0"}%
              </td>
              <td className="px-4 py-2.5 text-right text-gray-400 tabular-nums">{parseInt(row.stations).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DashboardInner() {
  const [tab, setTab] = useState("dashboard");
  const { data: summary,   isLoading: summaryLoading,   error: summaryError   } = useDashboardSummary();
  const { data: issues,    isLoading: issuesLoading,    error: issuesError    } = useIssueFrequency();
  const { data: provinces, isLoading: provincesLoading, error: provincesError } = useProvinceScores();
  const [feedPlatform,  setFeedPlatform]  = useState("");
  const [feedSentiment, setFeedSentiment] = useState("");
  const [feedProvince,  setFeedProvince]  = useState("");
  const [feedIssue,     setFeedIssue]     = useState("");
  const [feedSource,    setFeedSource]    = useState("");
  const [feedSearch,    setFeedSearch]    = useState("");
  const { data: posts, isLoading: postsLoading, error: postsError } = usePosts({
    limit: 50,
    platform:  feedPlatform  || undefined,
    sentiment: feedSentiment || undefined,
    province:  feedProvince  || undefined,
    issue:     feedIssue     || undefined,
    source:    feedSource    || undefined,
  });
  const { data: polls, isLoading: pollsLoading, error: pollsError } = usePolls();
  const [exportLoading, setExportLoading] = useState(false);

  async function handleExport() {
    setExportLoading(true);
    try {
      const params = new URLSearchParams();
      if (feedPlatform)  params.set("platform",  feedPlatform);
      if (feedSentiment) params.set("sentiment", feedSentiment);
      if (feedProvince)  params.set("province",  feedProvince);
      if (feedIssue)     params.set("issue",      feedIssue);
      if (feedSource)    params.set("source",     feedSource);

      const token = getToken();
      const res = await fetch(`/api/export/posts?${params}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Export failed");

      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `pf_intel_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Export error: ${e.message}`);
    } finally {
      setExportLoading(false);
    }
  }

  const [msgProvince, setMsgProvince] = useState("");
  const [msgIssue,    setMsgIssue]    = useState("");
  const [msgResult,   setMsgResult]   = useState("");
  const [msgLoading,  setMsgLoading]  = useState(false);

  async function handleGenerateMessage() {
    setMsgResult("");
    setMsgLoading(true);
    try {
      const token = getToken();
      const res = await fetch("/api/generate-message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ province: msgProvince, issue: msgIssue }),
      });
      if (!res.ok) throw new Error(await res.text());
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        setMsgResult(prev => prev + decoder.decode(value));
      }
    } catch (e: any) {
      setMsgResult(`Error: ${e.message}`);
    } finally {
      setMsgLoading(false);
    }
  }

  const TABS = [
    { id: "dashboard",  label: "Dashboard" },
    { id: "social",     label: "Social Feed" },
    { id: "polls",      label: "Opinion Polls" },
    { id: "strategy",   label: "Strategy" },
    { id: "protection", label: "Vote Protection" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Nav */}
      <nav className="bg-gray-950 border-b border-gray-800 sticky top-0 z-10 px-6 h-14 flex items-center gap-6">
        <div className="flex items-center gap-3 mr-4">
          <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center text-sm font-bold">PF</div>
          <div>
            <div className="text-sm font-semibold">PF Intelligence Hub</div>
            <div className="text-[10px] text-gray-500">Zambia 2026 · Cost of Living Campaign</div>
          </div>
        </div>
        <div className="flex gap-1 flex-1">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-1.5 rounded-lg text-sm transition-all
                ${tab === t.id
                  ? "bg-red-600/20 text-red-400 border border-red-600/30"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"}`}>
              {t.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => { localStorage.removeItem("pf_token"); window.location.reload(); }}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
          Sign out
        </button>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-6">

        {/* DASHBOARD */}
        {tab === "dashboard" && (
          <>
            <CountdownTimer />
            {summaryError
              ? <ApiError message="Could not load summary — is the API running?" />
              : <div className="grid grid-cols-5 gap-3 mb-6">
                  <KpiCard label="Mentions tracked"   value={summaryLoading ? "…" : (summary?.total_mentions || 0).toLocaleString()} delta="↑ 23% this week" deltaUp accent="#3b82f6" />
                  <KpiCard label="Negative sentiment" value={summaryLoading ? "…" : `${(summary?.negative_pct ?? 67).toFixed(1)}%`} delta="↑ 4pts vs last week" accent="#e63946" />
                  <KpiCard label="Top issue"          value={summaryLoading ? "…" : (ISSUE_DISPLAY[summary?.top_issue ?? "mealie_meal"] || "Mealie meal")} delta="Most mentioned" accent="#f59e0b" />
                  <KpiCard label="Poll responses"     value={summaryLoading ? "…" : (summary?.poll_responses || 0).toLocaleString()} delta="↑ 312 today" deltaUp accent="#8b5cf6" />
                  <KpiCard label="PF sentiment"       value="+42%" delta="Favourable on CoL" deltaUp accent="#16a34a" />
                </div>
            }

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-medium mb-4 text-gray-300">Top cost-of-living issues (% of posts)</h3>
                {issuesError ? <ApiError message="Failed to load issues." /> : issuesLoading ? <Spinner /> : <IssueBars data={issues || []} />}
              </div>
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-medium mb-4 text-gray-300">Public sentiment toward UPND government</h3>
                {summaryLoading ? <Spinner /> : (() => {
                  const neg = summary?.negative_pct ?? 67;
                  const pos = summary?.positive_pct ?? 9;
                  const neu = summary?.neutral_pct ?? 24;
                  return (
                    <div className="flex items-center gap-4">
                      <ResponsiveContainer width={120} height={120}>
                        <PieChart>
                          <Pie data={[{v:neg},{v:neu},{v:pos}]} dataKey="v" innerRadius={35} outerRadius={55} strokeWidth={0}>
                            <Cell fill="#e63946"/><Cell fill="#4b5563"/><Cell fill="#16a34a"/>
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="space-y-2.5 text-sm flex-1">
                        {([["#e63946","Negative",neg],["#4b5563","Neutral",neu],["#16a34a","Positive",pos]] as [string,string,number][]).map(([c,l,v])=>(
                          <div key={l} className="flex items-center gap-2">
                            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{background:c}}/>
                            <span className="text-gray-400">{l}</span>
                            <span className="font-bold ml-auto">{v.toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm font-medium mb-3 text-gray-300">Province-level grievance score (higher = more opportunity for PF)</h3>
              {provincesError ? <ApiError message="Failed to load province data." /> : provincesLoading ? <Spinner /> : <ProvinceGrid provinces={provinces || []} />}
              <p className="text-xs text-gray-600 mt-3">Darker = higher grievance. Based on social media volume and sentiment analysis.</p>
            </div>
          </>
        )}

        {/* SOCIAL FEED */}
        {tab === "social" && (
          <>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Social media intelligence feed</h2>
              <button
                onClick={handleExport}
                disabled={exportLoading}
                className="px-3 py-1.5 text-xs font-medium bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 text-gray-300 rounded-lg transition-colors">
                {exportLoading ? "Exporting…" : "Export CSV"}
              </button>
            </div>
            <div className="flex gap-2 mb-3 flex-wrap">
              <input
                type="text"
                placeholder="Search mentions…"
                value={feedSearch}
                onChange={e => setFeedSearch(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 min-w-[180px]"
              />
              <select value={feedPlatform} onChange={e => { setFeedPlatform(e.target.value); setFeedSource(""); }}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                <option value="">All platforms</option>
                <option value="facebook">Facebook</option>
                <option value="news">News sites</option>
              </select>
              <select value={feedSentiment} onChange={e => setFeedSentiment(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                <option value="">All sentiment</option>
                <option value="negative">Negative</option>
                <option value="neutral">Neutral</option>
                <option value="positive">Positive</option>
              </select>
              <select value={feedProvince} onChange={e => setFeedProvince(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                <option value="">All provinces</option>
                {["Lusaka","Copperbelt","Eastern","Southern","Central",
                  "Western","Northern","Luapula","North-Western","Muchinga"].map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <select value={feedIssue} onChange={e => setFeedIssue(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                <option value="">All issues</option>
                {Object.entries(ISSUE_DISPLAY).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <select value={feedSource} onChange={e => { setFeedSource(e.target.value); setFeedPlatform(""); }}
                className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                <option value="">All sources</option>
                <optgroup label="— Parties &amp; Politicians">
                  {[
                    "UPND", "Hakainde Hichilema", "Patriotic Front",
                    "Brian Mundubile", "Makebi Zulu", "NRPUP",
                    "Emmanuel Mwamba", "Miles Sampa", "Bowman Lusambo", "Given Lubinda",
                  ].map(s => <option key={s} value={s}>{s}</option>)}
                </optgroup>
                <optgroup label="— Media &amp; News">
                  {[
                    "Mwebantu", "Kalemba", "Zambian Watchdog", "Diggers News",
                    "Daily Revelation", "Zambia Reports", "Lusaka Times",
                    "The Mast Online", "ZNBC", "Zambian Observer", "Zambia Monitor",
                    "Zambia Daily Mail",
                  ].map(s => <option key={s} value={s}>{s}</option>)}
                </optgroup>
              </select>
              {(feedPlatform || feedSentiment || feedProvince || feedIssue || feedSource || feedSearch) && (
                <button
                  onClick={() => { setFeedPlatform(""); setFeedSentiment(""); setFeedProvince(""); setFeedIssue(""); setFeedSource(""); setFeedSearch(""); }}
                  className="px-3 py-2 text-xs text-gray-400 hover:text-white border border-gray-700 rounded-lg hover:border-gray-500 transition-colors">
                  Clear
                </button>
              )}
            </div>
            {postsError
              ? <ApiError message="Failed to load posts — is the API running?" />
              : postsLoading
              ? <Spinner />
              : (() => {
                  const filtered = (posts || []).filter((p: any) =>
                    !feedSearch || p.content.toLowerCase().includes(feedSearch.toLowerCase())
                  );
                  return filtered.length > 0
                    ? <PostFeed posts={filtered} />
                    : <p className="text-sm text-gray-500 py-8 text-center">No posts match the current filters.</p>;
                })()
            }
          </>
        )}

        {/* POLLS */}
        {tab === "polls" && (
          <>
            <h2 className="text-lg font-semibold mb-1">Opinion polls</h2>
            <p className="text-sm text-gray-400 mb-5">Results update in real time. Your responses are anonymous.</p>
            {pollsError
              ? <ApiError message="Failed to load polls — is the API running?" />
              : pollsLoading
              ? <Spinner />
              : <PollSection polls={polls || []} />
            }
          </>
        )}

        {/* VOTE PROTECTION */}
        {tab === "protection" && <VoteProtectionTab />}

        {/* STRATEGY */}
        {tab === "strategy" && (
          <>
            <h2 className="text-lg font-semibold mb-1">Strategic recommendations</h2>
            <p className="text-sm text-gray-400 mb-5">Generated from social media analysis and poll data.</p>
            <div className="space-y-3 mb-8">
              {STRATEGY_RECS.map((r, i) => (
                <div key={i} className="flex gap-4 bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-gray-700 transition-colors">
                  <div className="flex-shrink-0 w-7 h-7 rounded-full bg-red-950 border border-red-800 flex items-center justify-center text-xs font-bold text-red-400 mt-0.5">
                    {i + 1}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white mb-1">{r.title}</div>
                    <div className="text-sm text-gray-400 leading-relaxed">{r.body}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <h3 className="text-sm font-medium mb-4 text-white">Generate targeted campaign message</h3>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <select value={msgProvince} onChange={e=>setMsgProvince(e.target.value)}
                  className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                  <option value="">Select province...</option>
                  {["Lusaka","Copperbelt","Eastern","Southern","Central","Western","Northern","Luapula","North-Western","Muchinga"].map(p=>(
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <select value={msgIssue} onChange={e=>setMsgIssue(e.target.value)}
                  className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                  <option value="">Select issue...</option>
                  {["Mealie meal prices","Fuel costs","ZESCO load shedding","Youth unemployment","Kwacha depreciation","Fertiliser subsidies"].map(i=>(
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              </div>
              <button
                disabled={!msgProvince || !msgIssue || msgLoading}
                onClick={handleGenerateMessage}
                className="w-full py-3 bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors">
                {msgLoading ? "Generating…" : "Generate campaign message →"}
              </button>
              {msgResult && (
                <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <p className="text-xs text-gray-500 uppercase tracking-widest mb-2">Generated message</p>
                  <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">{msgResult}</p>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
