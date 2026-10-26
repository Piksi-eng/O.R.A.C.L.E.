export function wsUrl(path: string): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${path}`;
}

/** A WebSocket that reconnects with backoff until `close()` is called. */
export function reconnectingSocket(
  url: () => string,
  handlers: {
    onOpen?: (ws: WebSocket) => void;
    onMessage?: (data: unknown) => void;
    onStatus?: (connected: boolean) => void;
  },
) {
  let ws: WebSocket | null = null;
  let closed = false;
  let delay = 500;
  let timer: number | undefined;

  const open = () => {
    ws = new WebSocket(url());
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      delay = 500;
      handlers.onStatus?.(true);
      handlers.onOpen?.(ws!);
    };
    ws.onmessage = (e) => {
      if (typeof e.data === "string") handlers.onMessage?.(JSON.parse(e.data));
    };
    ws.onclose = () => {
      handlers.onStatus?.(false);
      if (closed) return;
      timer = window.setTimeout(open, delay);
      delay = Math.min(delay * 2, 5000);
    };
  };
  open();

  return {
    send(data: ArrayBuffer | string) {
      if (ws?.readyState === WebSocket.OPEN) ws.send(data);
    },
    close() {
      closed = true;
      window.clearTimeout(timer);
      ws?.close();
    },
  };
}
