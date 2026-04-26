// Catches render errors anywhere in the tree so a thrown exception during
// pitch doesn't blank the whole screen. Without this the demo falls back to
// React's default "white screen of death" with no message.

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] render crash:", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
          <div className="max-w-md rounded-2xl border border-rose-500/40 bg-rose-500/10 p-6">
            <h2 className="text-lg font-semibold text-rose-200 mb-2">Something broke.</h2>
            <p className="text-sm text-rose-100/80 mb-3">
              {this.state.error.message || "Unknown render error."}
            </p>
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
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
