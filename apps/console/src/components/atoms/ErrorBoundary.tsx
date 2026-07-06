import React, { Component, ErrorInfo } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught exception:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center p-6 border border-dashed border-imminent/40 bg-imminent/5 rounded-md text-center max-w-md mx-auto select-none my-4 font-mono text-xs">
          <AlertCircle className="h-8 w-8 text-imminent mb-2 animate-pulse" />
          <span className="font-bold text-imminent uppercase tracking-wide">
            Panel Render Crash
          </span>
          <p className="text-ink-dim leading-relaxed mt-1 select-text">
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            onClick={this.handleReload}
            className="mt-3 h-7 px-3 bg-imminent/20 border border-imminent/40 text-imminent rounded hover:bg-imminent/30 cursor-pointer font-bold uppercase transition-colors"
          >
            Reload Interface
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
