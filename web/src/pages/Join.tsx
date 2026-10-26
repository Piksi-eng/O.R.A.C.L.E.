import { useEffect, useRef, useState } from "react";
import { level, meterWidth, startMic } from "../lib/mic";
import { reconnectingSocket, wsUrl } from "../lib/socket";
import { load, playerId, save } from "../lib/storage";

type Phase = "setup" | "starting" | "live" | "error";

const PING_INTERVAL_MS = 5000;

export default function Join() {
  const [name, setName] = useState(load("dmc.name"));
  const [character, setCharacter] = useState(load("dmc.character"));
  const [phase, setPhase] = useState<Phase>("setup");
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const [mic, setMic] = useState(0);
  const stopRef = useRef<() => void>();

  useEffect(() => () => stopRef.current?.(), []);

  async function join() {
    save("dmc.name", name.trim());
    save("dmc.character", character.trim());
    setPhase("starting");
    setError("");
    const id = playerId();
    const socket = reconnectingSocket(
      () => wsUrl(`/ws/mic?${new URLSearchParams({ id, name: name.trim(), character: character.trim() })}`),
      {
        onStatus: setConnected,
        onMessage: (msg) => {
          const m = msg as { type: string; recording?: boolean };
          if (m.recording !== undefined) setRecording(m.recording);
        },
      },
    );
    let stopMic: (() => void) | undefined;
    try {
      stopMic = await startMic((pcm) => {
        setMic(level(pcm));
        socket.send(pcm);
      });
    } catch (e) {
      socket.close();
      setPhase("error");
      setError(micError(e));
      return;
    }
    const ping = window.setInterval(() => socket.send(JSON.stringify({ type: "ping" })), PING_INTERVAL_MS);
    const releaseWakeLock = keepScreenOn();
    stopRef.current = () => {
      window.clearInterval(ping);
      releaseWakeLock();
      stopMic?.();
      socket.close();
    };
    setPhase("live");
  }

  function leave() {
    stopRef.current?.();
    stopRef.current = undefined;
    setPhase("setup");
    setConnected(false);
    setRecording(false);
    setMic(0);
  }

  if (phase === "live") {
    return (
      <main className="phone live">
        <div className={`badge ${recording ? "rec" : ""}`}>{recording ? "● Recording" : "Not recording"}</div>
        <h1>{character || name}</h1>
        {character && <p className="muted">{name}</p>}
        <div className="meter big" aria-label="Microphone level">
          <div style={{ width: `${meterWidth(mic)}%` }} />
        </div>
        <p className={connected ? "ok" : "warn"}>{connected ? "Connected to the DM" : "Reconnecting…"}</p>
        <p className="hint">Keep this screen open and the phone in front of you.</p>
        <button className="secondary" onClick={leave}>
          Leave table
        </button>
      </main>
    );
  }

  return (
    <main className="phone">
      <h1>Join the table</h1>
      <label>
        Your name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="given-name" />
      </label>
      <label>
        Character
        <input value={character} onChange={(e) => setCharacter(e.target.value)} placeholder="e.g. Thorin" />
      </label>
      <button disabled={!name.trim() || phase === "starting"} onClick={join}>
        {phase === "starting" ? "Starting mic…" : "Join with microphone"}
      </button>
      {error && <p className="warn">{error}</p>}
    </main>
  );
}

function micError(e: unknown): string {
  const name = e instanceof DOMException ? e.name : "";
  if (name === "NotAllowedError") return "Microphone permission was denied. Allow it in the browser's site settings and try again.";
  if (name === "NotFoundError") return "No microphone found on this device.";
  if (!window.isSecureContext) return "The page must be opened over https:// for the microphone to work.";
  return `Could not start the microphone: ${e instanceof Error ? e.message : String(e)}`;
}

/** Phones kill the mic when the screen locks, so keep it on while at the table. */
function keepScreenOn(): () => void {
  let lock: WakeLockSentinel | null = null;
  let released = false;
  const request = async () => {
    try {
      if (!released && "wakeLock" in navigator && document.visibilityState === "visible") {
        lock = await navigator.wakeLock.request("screen");
      }
    } catch {
      /* not supported or denied: the hint on screen covers it */
    }
  };
  const onVisible = () => void request();
  document.addEventListener("visibilitychange", onVisible);
  void request();
  return () => {
    released = true;
    document.removeEventListener("visibilitychange", onVisible);
    void lock?.release();
  };
}
