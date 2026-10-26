# O.R.A.C.L.E.

**Omniscient Recorder And Campaign Lore Engine**

An all-in-one tool for running D&D 5e at a real table. Every player's phone becomes a microphone,
the session is transcribed live (Serbian and English mixed, the way we actually talk), and the tool
grows around that transcript: recaps, NPC voices, a DM copilot, mood music and a world that keeps
living between sessions.

It runs on the DM's Windows PC (RTX 3070 Ti, 8 GB VRAM). Phones connect over the home Wi-Fi.
Nothing needs the internet except the optional cloud AI calls.

## Status

| # | Module | What it does at the table | Status |
|---|---|---|---|
| 0 | Foundation | Local HTTPS server, DM dashboard, live connection to phones | Done |
| 1 | Phone mics | Players scan a QR code, pick their character, their phone streams audio; one WAV per player per session | Done |
| 2 | Live scribe | Live transcript with names, Whisper on the GPU, D&D vocabulary prompt, Cyrillic to Latin | Next |
| 3 | After-session brain | Cleanup, table talk filtered out, events, loot and NPCs logged, a "Previously on…" recap | Planned |
| 4 | NPC voices | One English voice per NPC (Kokoro / Piper / XTTS), click to speak; Voicemod routing later | Planned |
| 5 | DM copilot | Quick ideas on the fly, "what did they promise the priest?", homebrew rule lookup | Planned |
| 6 | Mood director | Scene detection switches music; nat 20 sound effects; LED lights later | Planned |
| 7 | Plot tracker | Quests, open threads, NPCs met, party promises, updated from transcripts | Planned |
| 8 | Living world | NPCs live between sessions, "while you were away" report | Planned |
| Later | Upgrades | Clip-on mics, Voicemod, ESP32 table lights, Discord chats with NPCs | Ideas |

Rule of the project: one module at a time, each useful at the table on its own. If a module does not
work in a real session, it gets cut.

## Setup (Windows)

You need [Python 3.11+](https://www.python.org/downloads/) (tick "Add python.exe to PATH") and
[Node.js LTS](https://nodejs.org/).

```powershell
git clone https://github.com/Piksi-eng/O.R.A.C.L.E. oracle
cd oracle
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

The server prints two addresses:

- **Dashboard** for you: `https://localhost:8443/dm`
- **Join page** for the players: `https://<your PC's IP>:8443/join` (also shown as a QR code on the dashboard)

## At the table

1. Start the server and open the dashboard.
2. Players scan the QR code with their phone camera, enter their name and character, and tap
   **Join with microphone**.
3. The first time, the browser warns about the certificate. Tap **Advanced → Proceed**. This is
   expected: the server makes its own certificate because phones only allow the microphone over HTTPS.
4. Each player's meter moves on the dashboard when they talk. Press **Start recording**.
5. Phones stay on the table with the screen on. The page keeps the screen awake where the browser
   allows it.
6. **Stop recording** saves everything to `data/sessions/<date>_<time>/`: one WAV per player
   (16 kHz mono, aligned to the same session clock) and a `session.json` describing the tracks.

## Troubleshooting

- **Phones can't open the page:** the first time the server starts, Windows asks whether Python may
  use the network. Allow it on **Private networks**. Your Wi-Fi must also be set to Private
  (Settings → Network & Internet → Wi-Fi → your network → Private).
- **"Microphone permission was denied":** allow the microphone in the browser's site settings for
  the page, then reload.
- **The address changed:** the PC got a new IP from the router. Restart the server; it makes a
  new certificate and QR code automatically.
- **iPhone shows no mic option:** use Safari, and accept the certificate warning first.

## Development

```powershell
# Backend tests
cd server; .\.venv\Scripts\python.exe -m pytest

# Frontend with hot reload (the Python server must be running too)
cd web; npm run dev
```

The dev server at `http://localhost:5173` forwards API and socket calls to the Python server.
Phones always use the built app the Python server serves, so run `npm run build` before a session.

### Layout

```
server/oracle/   Python backend (FastAPI)
  app.py               HTTP API and WebSockets (/ws/mic for phones, /ws/dm for the dashboard)
  session.py           Players at the table and the recording in progress
  audio.py             Loudness and the per-player WAV writer
  certs.py             Self-signed HTTPS certificate for the LAN address
web/src/               React + TypeScript
  pages/Join.tsx       The phone page
  pages/Dashboard.tsx  The DM dashboard
  lib/mic.ts           Microphone capture
web/public/pcm-worklet.js   Audio thread: 48 kHz float to 16 kHz int16, 100 ms chunks
scripts/               Windows setup and start
```

## Privacy

Recordings never leave the PC unless a module is configured to use a cloud AI. Ask the players
before recording.
