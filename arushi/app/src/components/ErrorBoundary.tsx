// Catches render errors anywhere in the tree so a thrown exception during
// pitch doesn't blank the whole screen. Without this the demo falls back to
// React's default "white screen of death" with no message.
//
// Also captures unhandled promise rejections (async errors) since React's
// componentDidCatch only sees render-phase throws.

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  retryCount: number;
}

const MAX_RETRIES = 3;
const STABLE_RESET_MS = 60_000;

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null, retryCount: 0 };
  private resetTimer: number | null = null;

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  componentDidMount() {
    window.addEventListener("unhandledrejection", this.handleUnhandledRejection);
    this.scheduleStableReset();
  }

  componentDidUpdate(_: Props, prevState: State) {
    // If we just transitioned from error → no error, restart the stability timer.
    if (prevState.error && !this.state.error) {
      this.scheduleStableReset();
    }
    // If a new error appeared, cancel pending reset.
    if (!prevState.error && this.state.error) {
      this.clearStableReset();
    }
  }

  componentWillUnmount() {
    window.removeEventListener("unhandledrejection", this.handleUnhandledRejection);
    this.clearStableReset();
  }

  componentDidCatch(error: Error) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] render crash:", error);
  }

  private handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    const err =
      reason instanceof Error
        ? reason
        : new Error(typeof reason === "string" ? reason : "Unhandled promise rejection");
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] unhandled rejection:", err);
    this.setState((prev) => (prev.error ? prev : { ...prev, error: err }));
  };

  private scheduleStableReset() {
    this.clearStableReset();
    this.resetTimer = window.setTimeout(() => {
      // After a stable run, forgive past retries so a much-later failure
      // doesn't immediately trip the "repeated failure" gate.
      this.setState((prev) => (prev.retryCount > 0 ? { ...prev, retryCount: 0 } : prev));
    }, STABLE_RESET_MS);
  }

  private clearStableReset() {
    if (this.resetTimer !== null) {
      window.clearTimeout(this.resetTimer);
      this.resetTimer = null;
    }
  }

  private handleRetry = () => {
    this.setState((prev) => ({ error: null, retryCount: prev.retryCount + 1 }));
  };

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      const exhausted = this.state.retryCount >= MAX_RETRIES;
      if (exhausted) {
        return (
          <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
            <div className="max-w-md rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6">
              <h2 className="text-lg font-semibold text-rose-200 mb-2">Repeated failure</h2>
              <p className="text-sm text-rose-100/80 mb-3">
                We tried recovering {MAX_RETRIES} times but the app keeps crashing
                {this.state.error.message ? `: ${this.state.error.message}` : "."} Reloading the
                page may clear the underlying state.
              </p>
              <button
                type="button"
                onClick={this.handleReload}
                className="rounded-xl bg-rose-500 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-rose-400"
              >
                Reload page
              </button>
            </div>
          </div>
        );
      }
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
          <div className="max-w-md rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6">
            <h2 className="text-lg font-semibold text-rose-200 mb-2">Something broke.</h2>
            <p className="text-sm text-rose-100/80 mb-3">
              {this.state.error.message || "Unknown render error."}
            </p>
            <button
              type="button"
              onClick={this.handleRetry}
              className="rounded-xl bg-rose-500 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-rose-400"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
