import { Component } from "react";
import { captureError } from "../lib/monitoring";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
    captureError(error, {
      contexts: { react: { componentStack: errorInfo?.componentStack } },
      tags: { area: "error_boundary" },
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" style={{
          padding: "2rem",
          maxWidth: "32rem",
          margin: "2rem auto",
          textAlign: "center",
          fontFamily: "system-ui, sans-serif",
        }}>
          <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Something went wrong</h1>
          <p style={{ color: "#666", marginBottom: "1.5rem" }}>
            The app hit an error. Try refreshing the page.
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "1rem",
              cursor: "pointer",
              background: "#333",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
