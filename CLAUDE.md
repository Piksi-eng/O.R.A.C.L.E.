# O.R.A.C.L.E.: notes for Claude

## What this is

The owner's personal tool for running D&D 5e at an in-person table, and the basis of their
diplomski (final thesis) at Elektronski fakultet Niš, smer Računarstvo i informatika. The README's
status table is the roadmap: modules are built one at a time, each must be useful at a real
session, and anything that fails at the table gets cut.

Thesis core: the scribe (modules 1–3). Phone-per-player capture, transcription of mixed
Serbian/English speech (code-switching inside sentences: "imam advantage na ovaj attack"),
speaker attribution during crosstalk, and event extraction. The experiments to support:
- word error rate on the group's mixed speech: plain Whisper → + vocabulary prompt → + LLM correction → fine-tuned
- speaker attribution: one room mic + diarization vs. one phone per player, calm vs. chaotic moments
- extracted events vs. the DM's own notes

Keep raw per-player audio and timestamps; the experiments need them.

## The table

- 4–6 players, in person, lots of shouting and talking over each other.
- Mostly Serbian with English game terms; players role-play in English most of the time.
- A published 5e adventure with many homebrew rules.
- NPC voices are English only (more and better voices). Voicemod Pro is owned; routing TTS through
  it comes later.

## Hardware and platform

- Windows PC with an RTX 3070 Ti: 8 GB VRAM is the hard budget. During a session only
  transcription (and later live TTS) runs on the GPU; heavy LLM work runs after the session or in
  the cloud.
- LLM: hybrid, local via Ollama when it fits, cloud API for heavy jobs, switchable in one setting.
- Phones join over the LAN; browsers require HTTPS for the microphone, so the server always runs
  TLS with its own certificate (`server/oracle/certs.py`).

## Architecture

- `server/`: Python 3.11+, FastAPI + uvicorn. Python because Whisper, TTS and audio tooling live there.
- `web/`: React + TypeScript (Vite), built into `web/dist` and served by the Python server.
- Phones send 16 kHz mono int16 PCM in 100 ms binary WebSocket frames to `/ws/mic?id&name&character`;
  text frames are JSON (`ping` → `pong`). The server tells phones `{"type":"status","recording":bool}`.
- The dashboard receives the full table state from `/ws/dm` ten times a second.
- Recordings: `data/sessions/<date>_<time>/` with one WAV per player and `session.json`
  (`start_offset_s` puts every track on one session clock; gaps over 1 s are filled with silence).

## Commands

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # once
powershell -ExecutionPolicy Bypass -File scripts\start.ps1   # run
cd server; .\.venv\Scripts\python.exe -m pytest              # backend tests
cd web; npm run build                                        # typecheck + build
cd web; npm run dev                                          # UI hot reload, proxies to the server
```

## Conventions

- Plain, small modules; comments explain why, not what.
- Every backend feature gets pytest coverage; WebSocket tests round-trip a `ping` before asserting
  so the server has handled earlier frames.
- `localStorage` access goes through `web/src/lib/storage.ts` (it can throw on phones).
- Never commit `data/` or `certs/`.
