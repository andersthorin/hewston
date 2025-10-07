import React from 'react'

export default class ErrorBoundary extends React.Component<
  {
    children?: React.ReactNode
    fallback?: React.ReactNode
    title?: string
  },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children?: React.ReactNode; fallback?: React.ReactNode; title?: string }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Minimal logging in dev
    try {
      console.warn('[ErrorBoundary] caught', error, info)
    } catch {
      // Ignore logging errors
    }
  }

  handleReload = () => {
    try {
      location.reload()
    } catch {
      // Ignore reload errors
    }
  }

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallback
      if (Fallback) return <>{Fallback}</>
      const message = this.state.error?.message || String(this.state.error || 'Unknown error')
      return (
        <div
          role="alert"
          className="rounded border border-amber-300 bg-amber-50 text-amber-700 p-3"
        >
          <div className="font-medium mb-1">{this.props.title || 'Something went wrong'}</div>
          <div className="text-xs whitespace-pre-wrap break-all">{message}</div>
          <button
            className="mt-2 inline-flex items-center rounded border border-amber-400 px-2 py-1 text-xs"
            onClick={this.handleReload}
          >
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children as React.ReactNode
  }
}
