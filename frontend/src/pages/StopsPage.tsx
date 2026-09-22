import { useEffect, useState } from "react";
import { api } from "../api/client";
type S = { id: number; route_id: number; seq: number; name: string; weight_kg: number; volume_l: number; suspended: boolean };
type R = { id: number; name: string };
export default function StopsPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [rows, setRows] = useState<S[]>([]);
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  useEffect(() => {
    if (rid === "") return;
    api<S[]>(`/stops?route_id=${rid}`).then(setRows);
  }, [rid]);
  async function toggle(s: S) {
    const updated = await api<S>(`/stops/${s.id}/suspension`, {
      method: "PATCH",
      body: JSON.stringify({ suspended: !s.suspended }),
    });
    setRows(rs => rs.map(r => (r.id === updated.id ? updated : r)));
  }
  return (<>
    <h2>订户点</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
    </div>
    <div className="route-strip">
      {rows.map(s => (
        <div className={`stop-chip${s.suspended ? " stop-chip--suspended" : ""}`} key={s.id}>
          <span className="seq">#{s.seq}</span>
          <strong>{s.name}</strong>
          <span className="mono">{s.weight_kg}kg · {s.volume_l}L</span>
          {s.suspended && <span className="stop-badge">停投</span>}
          <button className="chip-toggle" onClick={() => toggle(s)}>
            {s.suspended ? "恢复投送" : "标记停投"}
          </button>
        </div>
      ))}
    </div>
  </>);
}
