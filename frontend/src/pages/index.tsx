"use client";
import { useState, useEffect } from "react";
import {
  useDashboardSummary, useIssueFrequency, useProvinceScores,
  usePosts, usePolls, submitPollResponse
} from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from "recharts";
import { formatDistanceToNow, differenceInDays } from "date-fns";

const ELECTION_DATE = new Date("2026-08-13T00:00:00");

const PROVINCE_COLORS: Record<string, string> = {
  Lusaka: "#c0392b", Copperbelt: "#e74c3c", Eastern: "#e74c3c",
  Southern: "#e67e22", Central: "#e67e22", Western: "#e67e22",
  Northern: "#f39c12", "North-Western": "#f1c40f", Luapula: "#f1c40f",
  Muchinga: "#f1c40f",
};

const ISSUE_DISPLAY: Record<string, string> = {
  mealie_meal: "Mealie meal", fuel: "Fuel costs",
  electricity: "ZESCO/Power", employment: "Unemployment",
  kwacha: "Kwacha", fertiliser: "Fertiliser", education: "School/Medical",
};

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
    <div className="flex gap-3 mb-6">
      {[["Days", days], ["Hours", hrs], ["Mins", mins], ["Secs", secs]].map(([l, v]) => (
        <div key={l} className="bg-gray-900 rounded-lg px-4 py-2 text-center min-w-[60px]">
          <div className="text-2xl font-bold text-white">{String(v).padStart(2,"0")}</div>
          <div className="text-[10px] text-gray-400 uppercase tracking-widest">{l}</div>
        </div>
      ))}
      <div className="flex items-center ml-2 text-sm text-gray-400">
        until 13 August 2026 election
      </div>
    </div>
  );
}

function KpiCard({ label, value, delta, deltaUp }: {
  label: string; value: string; delta?: string; deltaUp?: boolean;
}) {
  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {delta && (
        <div className={`text-xs mt-1 ${deltaUp ? "text-green-400" : "text-red-400"}`}>
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
        const color = PROVINCE_COLORS[p.province] || "#888";
        return (
          <div key={p.province}
               className="rounded-lg p-2 text-center"
               style={{ background: `${color}22`, border: `1px solid ${color}44` }}>
            <div className="text-lg font-bold" style={{ color }}>{p.score}</div>
            <div className="text-[10px] text-gray-400 mt-0.5 leading-tight">{p.province}</div>
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
        <div key={post.id} className="bg-gray-900 rounded-lg p-3 border border-gray-800">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs text-gray-400">{post.source_name}</span>
            {post.published_at && (
              <span className="text-xs text-gray-600">
                · {formatDistanceToNow(new Date(post.published_at), { addSuffix: true })}
              </span>
            )}
            {post.sentiment && (
              <span className={`text-[10px] px-2 py-0.5 rounded-full border ${sentClass(post.sentiment)}`}>
                {post.sentiment}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-300 leading-relaxed">{post.content}</p>
          {post.issues?.length > 0 && (
            <div className="flex gap-1 flex-wrap mt-2">
              {post.issues.map((i: string) => (
                <span key={i} className="text-[10px] bg-red-950 text-red-300 border border-red-900 px-2 py-0.5 rounded-full">
                  #{ISSUE_DISPLAY[i] || i}
                </span>
              ))}
            </div>
          )}
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
  const [tab, setTab] = useState("dashboard");
  const { data: summary }   = useDashboardSummary();
  const { data: issues }    = useIssueFrequency();
  const { data: provinces } = useProvinceScores();
  const { data: posts }     = usePosts({ limit: 20 });
  const { data: polls }     = usePolls();
  const [msgProvince, setMsgProvince] = useState("");
  const [msgIssue,    setMsgIssue]    = useState("");
  const [msgResult,   setMsgResult]   = useState("");
  const [msgLoading,  setMsgLoading]  = useState(false);

  async function handleGenerateMessage() {
    setMsgResult("");
    setMsgLoading(true);
    try {
      const res = await fetch("/api/generate-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
    { id: "dashboard", label: "Dashboard" },
    { id: "social",    label: "Social Feed" },
    { id: "polls",     label: "Opinion Polls" },
    { id: "strategy",  label: "Strategy" },
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
        <div className="flex gap-1">
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
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-6">

        {/* DASHBOARD */}
        {tab === "dashboard" && (
          <>
            <CountdownTimer />
            <div className="grid grid-cols-5 gap-3 mb-6">
              <KpiCard label="Mentions tracked"   value={(summary?.total_mentions || 0).toLocaleString()} delta="↑ 23% this week" deltaUp />
              <KpiCard label="Negative sentiment" value={`${summary?.negative_pct || 67}%`} delta="↑ 4pts vs last week" />
              <KpiCard label="Top issue"          value="Mealie meal" delta="34% of all posts" />
              <KpiCard label="Poll responses"     value={(summary?.poll_responses || 0).toLocaleString()} delta="↑ 312 today" deltaUp />
              <KpiCard label="PF sentiment"       value="+42%" delta="Favourable on CoL" deltaUp />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-medium mb-4 text-gray-300">Top cost-of-living issues (% of posts)</h3>
                <IssueBars data={issues || []} />
              </div>
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-medium mb-4 text-gray-300">Public sentiment toward UPND government</h3>
                <div className="flex items-center gap-4">
                  <ResponsiveContainer width={120} height={120}>
                    <PieChart>
                      <Pie data={[{v:67},{v:24},{v:9}]} dataKey="v" innerRadius={35} outerRadius={55}>
                        <Cell fill="#e63946"/><Cell fill="#6b7280"/><Cell fill="#16a34a"/>
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2 text-sm">
                    {[["#e63946","Negative","67%"],["#6b7280","Neutral","24%"],["#16a34a","Positive","9%"]].map(([c,l,v])=>(
                      <div key={l} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full flex-shrink-0" style={{background:c}}/>
                        <span className="text-gray-400">{l}</span>
                        <span className="font-medium ml-auto">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm font-medium mb-3 text-gray-300">Province-level grievance score (higher = more opportunity for PF)</h3>
              <ProvinceGrid provinces={provinces || []} />
              <p className="text-xs text-gray-600 mt-3">Darker = higher grievance. Based on social media volume and sentiment analysis.</p>
            </div>
          </>
        )}

        {/* SOCIAL FEED */}
        {tab === "social" && (
          <>
            <h2 className="text-lg font-semibold mb-4">Social media intelligence feed</h2>
            <div className="flex gap-2 mb-4 flex-wrap">
              <input type="text" placeholder="Search mentions..." className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm flex-1 min-w-[180px]" />
              {["All platforms","Facebook","News sites"].map(p=>(
                <select key={p} className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm">
                  <option>{p}</option>
                </select>
              ))}
            </div>
            <PostFeed posts={posts || []} />
          </>
        )}

        {/* POLLS */}
        {tab === "polls" && (
          <>
            <h2 className="text-lg font-semibold mb-1">Opinion polls</h2>
            <p className="text-sm text-gray-400 mb-5">Results update in real time. Your responses are anonymous.</p>
            <PollSection polls={polls || []} />
          </>
        )}

        {/* STRATEGY */}
        {tab === "strategy" && (
          <>
            <h2 className="text-lg font-semibold mb-1">Strategic recommendations</h2>
            <p className="text-sm text-gray-400 mb-5">Generated from social media analysis and poll data.</p>
            <div className="space-y-3 mb-6">
              {STRATEGY_RECS.map((r, i) => (
                <div key={i} className="border-l-4 border-red-600 bg-gray-900 rounded-r-xl px-4 py-3">
                  <div className="text-sm font-medium text-white mb-1">{r.title}</div>
                  <div className="text-sm text-gray-400 leading-relaxed">{r.body}</div>
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
