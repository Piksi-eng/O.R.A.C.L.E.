// Runs on the browser's audio thread. Turns the microphone (usually 48 kHz float) into
// 16 kHz mono 16-bit PCM and posts it in 100 ms chunks.
const TARGET_RATE = 16000;
const CHUNK_SAMPLES = 1600;

class PcmWorklet extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / TARGET_RATE;
    this.rest = new Float32Array(0); // input not yet consumed
    this.pos = 0; // fractional read position into `rest`
    this.out = new Int16Array(CHUNK_SAMPLES);
    this.outLen = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;

    const data = new Float32Array(this.rest.length + channel.length);
    data.set(this.rest);
    data.set(channel, this.rest.length);

    // Each output sample is the average of the input samples it spans: a simple low-pass
    // that keeps the downsampling from folding high frequencies into speech.
    let pos = this.pos;
    while (pos + this.ratio <= data.length) {
      const start = Math.floor(pos);
      const end = Math.floor(pos + this.ratio);
      let sum = 0;
      for (let i = start; i < end; i++) sum += data[i];
      const v = sum / Math.max(1, end - start);
      this.out[this.outLen++] = Math.max(-1, Math.min(1, v)) * 0x7fff;
      if (this.outLen === CHUNK_SAMPLES) {
        this.port.postMessage(this.out.buffer, [this.out.buffer]);
        this.out = new Int16Array(CHUNK_SAMPLES);
        this.outLen = 0;
      }
      pos += this.ratio;
    }
    const consumed = Math.floor(pos);
    this.rest = data.slice(consumed);
    this.pos = pos - consumed;
    return true;
  }
}

registerProcessor("pcm-worklet", PcmWorklet);
