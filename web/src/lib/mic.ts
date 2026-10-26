/** Captures the microphone as 16 kHz mono int16 PCM chunks of 100 ms. */
export async function startMic(onChunk: (pcm: ArrayBuffer) => void): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      // Echo cancellation would try to remove the other players' voices as "echo" and
      // mangle the speech we want; noise suppression and auto gain help with a loud table.
      echoCancellation: false,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });
  const ctx = new AudioContext();
  await ctx.audioWorklet.addModule("/pcm-worklet.js");
  const source = ctx.createMediaStreamSource(stream);
  const worklet = new AudioWorkletNode(ctx, "pcm-worklet");
  // Some browsers only run a node that ends at the speakers, so route it there at zero volume.
  const mute = ctx.createGain();
  mute.gain.value = 0;
  source.connect(worklet).connect(mute).connect(ctx.destination);
  worklet.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onChunk(e.data);
  if (ctx.state === "suspended") await ctx.resume();

  return () => {
    worklet.port.onmessage = null;
    source.disconnect();
    worklet.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    void ctx.close();
  };
}

export function level(pcm: ArrayBuffer): number {
  const s = new Int16Array(pcm);
  if (s.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < s.length; i++) sum += s[i] * s[i];
  return Math.min(1, Math.sqrt(sum / s.length) / 32768);
}

/** Loudness meters read better on a log-ish scale: normal speech sits mid-bar, not at 5%. */
export function meterWidth(level: number): number {
  if (level <= 0) return 0;
  const db = 20 * Math.log10(level);
  return Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
}
