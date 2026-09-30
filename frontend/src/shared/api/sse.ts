/**
 * Browser SSE client for the per-project realtime stream.
 *
 * The backend forbids tokens in query strings, so the stream is opened with
 * fetch and read as text/event-stream. The client reconnects with a backoff
 * and replays missed events through the Last-Event-ID header.
 */

import { getAccessToken } from './token';
import type { RealtimeEvent } from './types';

/** Connection status reported to the UI. */
export type StreamStatus = 'connected' | 'reconnecting' | 'closed';

/** Handlers and settings of one project stream. */
export interface ProjectStreamOptions {
  /** Project to subscribe to. */
  projectId: number;
  /** Called for every parsed event frame. */
  onEvent: (event: RealtimeEvent) => void;
  /** Called on connection state changes. */
  onStatusChange?: (status: StreamStatus) => void;
  /** Base reconnect delay in milliseconds. */
  reconnectBaseMs?: number;
  /** Maximum reconnect delay in milliseconds. */
  reconnectMaxMs?: number;
}

const HEARTBEAT_TIMEOUT_MS = 60000;

/**
 * Maintain one SSE connection to a project event stream.
 */
export class ProjectEventStream {
  private readonly options: ProjectStreamOptions;
  private controller: AbortController | null = null;
  private stopped = false;
  private attempt = 0;
  private lastEventId: string | null = null;
  private watchdog: number | null = null;

  /**
   * Create a stream client.
   *
   * @param options project id, event handler and reconnect tuning.
   */
  constructor(options: ProjectStreamOptions) {
    this.options = options;
  }

  /**
   * Open the stream and keep reconnecting until stopped.
   */
  start(): void {
    this.stopped = false;
    void this.connect();
  }

  /**
   * Close the stream and cancel pending reconnects.
   */
  stop(): void {
    this.stopped = true;
    this.controller?.abort();
    this.controller = null;
    this.clearWatchdog();
    this.options.onStatusChange?.('closed');
  }

  /**
   * Read the id of the last processed frame.
   *
   * @returns last event id used for replay, or null.
   */
  getLastEventId(): string | null {
    return this.lastEventId;
  }

  /**
   * Open one fetch stream and process frames until it drops.
   */
  private async connect(): Promise<void> {
    if (this.stopped) return;
    const token = getAccessToken();
    if (!token) {
      this.scheduleReconnect();
      return;
    }

    this.controller = new AbortController();
    try {
      const response = await fetch(`/api/v1/projects/${this.options.projectId}/events`, {
        method: 'GET',
        headers: {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
          ...(this.lastEventId ? { 'Last-Event-ID': this.lastEventId } : {}),
        },
        credentials: 'include',
        signal: this.controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed with status ${response.status}`);
      }

      this.attempt = 0;
      this.options.onStatusChange?.('connected');
      await this.readFrames(response.body);
    } catch {
      if (!this.stopped) {
        this.options.onStatusChange?.('reconnecting');
        this.scheduleReconnect();
      }
    } finally {
      this.clearWatchdog();
    }
  }

  /**
   * Parse SSE frames from the response byte stream.
   *
   * @param body readable byte stream of the response.
   */
  private async readFrames(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    for (;;) {
      const { done, value } = await reader.read();
      if (done) throw new Error('Stream closed');
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        this.handleFrame(frame);
        boundary = buffer.indexOf('\n\n');
      }

      this.armWatchdog();
    }
  }

  /**
   * Dispatch one raw SSE frame.
   *
   * @param frame raw frame text without the trailing blank line.
   */
  private handleFrame(frame: string): void {
    let eventName = 'message';
    let eventId: string | null = null;
    const dataLines: string[] = [];

    for (const line of frame.split('\n')) {
      if (line.startsWith(':')) continue;
      if (line.startsWith('event:')) eventName = line.slice(6).trim();
      else if (line.startsWith('id:')) eventId = line.slice(3).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }

    if (dataLines.length === 0) return;
    if (eventId) this.lastEventId = eventId;

    try {
      const payload = JSON.parse(dataLines.join('\n')) as RealtimeEvent;
      this.options.onEvent(payload);
    } catch {
      // Malformed frame is dropped; the replay path covers gaps.
    }
    void eventName;
  }

  /**
   * Reset the inactivity watchdog used to detect dead connections.
   */
  private armWatchdog(): void {
    this.clearWatchdog();
    this.watchdog = window.setTimeout(() => {
      this.controller?.abort();
    }, HEARTBEAT_TIMEOUT_MS);
  }

  /**
   * Clear the inactivity watchdog.
   */
  private clearWatchdog(): void {
    if (this.watchdog !== null) {
      window.clearTimeout(this.watchdog);
      this.watchdog = null;
    }
  }

  /**
   * Schedule a reconnect with exponential backoff and jitter.
   */
  private scheduleReconnect(): void {
    if (this.stopped) return;
    const base = this.options.reconnectBaseMs ?? 1000;
    const max = this.options.reconnectMaxMs ?? 30000;
    const delay = Math.min(max, base * 2 ** this.attempt) * (0.8 + Math.random() * 0.4);
    this.attempt += 1;
    window.setTimeout(() => {
      void this.connect();
    }, delay);
  }
}
