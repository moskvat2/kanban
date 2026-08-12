import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, message: error instanceof Error ? error.message : "Erro desconhecido" };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Kanban error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="screen-center">
          <div className="empty-state-icon">!</div>
          <h2>Algo deu errado</h2>
          <p className="empty-state">Ocorreu um erro inesperado. Recarregue a página para continuar.</p>
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>
            Recarregar
          </button>
          <p className="inline-error">{this.state.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
