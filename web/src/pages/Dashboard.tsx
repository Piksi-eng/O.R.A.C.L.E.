import QRCode from "qrcode";
import { useEffect, useState } from "react";
import { meterWidth } from "../lib/mic";
import { reconnectingSocket, wsUrl } from "../lib/socket";

interface PlayerState {
  id: string;
  name: string;
  character: string;
  connected: boolean;
  level: number;
  recording: boolean;
}

interface TableState {
  recording: { elapsed_s: number; dir: string } | null;
  players: PlayerState[];
}

export default function Dashboard() {
  const [state, setState] = useState<TableState>({ recording: null, players: [] });
  const [online, setOnline] = useState(false);
  const [joinUrl, setJoinUrl] = useState("");
  const [qr, setQr] = useState("");
  const [lastSaved, setLastSaved] = useState("");

  useEffect(() => {
    const socket = reconnectingSocket(() => wsUrl("/ws/dm"), {
      onStatus: setOnline,
      onMessage: (m) => setState(m as TableState),
    });
    return () => socket.close();
  }, []);

  useEffect(() => {
    fetch("/api/info")
      .then((r) => r.json())
      .then((info: { join_url: string }) => {
        setJoinUrl(info.join_url);
        return QRCode.toDataURL(info.join_url, { margin: 1, width: 220 });
      })
      .then(setQr)
      .catch(() => setJoinUrl(""));
  }, []);

  async function toggleRecording() {
    if (state.recording) {
      const r = await fetch("/api/recording/stop", { method: "POST" }).then((r) => r.json());
      setLastSaved(r.saved_to ?? "");
    } else {
      setLastSaved("");
      await fetch("/api/recording/start", { method: "POST" });
    }
  }

  const forget = (id: string) => fetch(`/api/players/${id}`, { method: "DELETE" });

  return (
    <main className="dashboard">
      <header>
        <h1>DM Companion</h1>
        <span className={online ? "ok" : "warn"}>{online ? "Server connected" : "Server offline"}</span>
      </header>

      <section className="panel recording">
        <button className={state.recording ? "stop" : ""} onClick={toggleRecording} disabled={!online}>
          {state.recording ? "■ Stop recording" : "● Start recording"}
        </button>
        {state.recording && <span className="rec">● {formatTime(state.recording.elapsed_s)}</span>}
        {lastSaved && <span className="muted">Saved to {lastSaved}</span>}
      </section>

      <div className="columns">
        <section className="panel">
          <h2>At the table</h2>
          {state.players.length === 0 && <p className="muted">No phones yet. Players scan the code to join.</p>}
          <ul className="players">
            {state.players.map((p) => (
              <li key={p.id} className={p.connected ? "" : "gone"}>
                <div className="who">
                  <strong>{p.character || p.name}</strong>
                  {p.character && <span className="muted"> {p.name}</span>}
                  {p.recording && <span className="rec small"> ●</span>}
                </div>
                <div className="meter">
                  <div style={{ width: `${meterWidth(p.level)}%` }} />
                </div>
                {!p.connected && (
                  <button className="link" onClick={() => forget(p.id)}>
                    remove
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="panel join">
          <h2>Players join here</h2>
          {qr && <img src={qr} alt="QR code to join" width={220} height={220} />}
          <code>{joinUrl || "…"}</code>
          <p className="muted small">Same Wi-Fi as this PC. Accept the certificate warning once.</p>
        </section>
      </div>
    </main>
  );
}

function formatTime(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}
