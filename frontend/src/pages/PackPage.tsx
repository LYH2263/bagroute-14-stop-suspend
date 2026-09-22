import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; name: string };
type S = { id: number; suspended: boolean };
type Bag = { id: number; bag_index: number; weight_kg: number; volume_l: number; items: { stop_name: string }[] };
export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [suspendedCount, setSuspendedCount] = useState(0);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  useEffect(() => {
    if (rid === "") return;
    api<S[]>(`/stops?route_id=${rid}`).then(ss => setSuspendedCount(ss.filter(s => s.suspended).length));
  }, [rid]);
  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      setMsg(`完成装袋：${out.length} 袋${suspendedCount ? `（${suspendedCount} 站停投未参与）` : ""}`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
    </div>
    {suspendedCount > 0 && <div className="hint">{suspendedCount} 站停投，不参与装袋；按剩余站点执行重量/体积双约束</div>}
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono">袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L</div>
        <div className="bag-row">{b.items.map((it, i) => <div className="bag-block" key={i}>{it.stop_name}</div>)}</div>
      </div>
    ))}
  </>);
}
