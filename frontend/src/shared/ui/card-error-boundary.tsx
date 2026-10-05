import { Component, type ErrorInfo, type PropsWithChildren } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/primitives/card'
import { PanelMessage } from '@/shared/ui/panel-message'

interface CardErrorBoundaryProps extends PropsWithChildren {
  /** Shown as the fallback card's title, so the reader knows which panel broke. */
  title: string
}

interface CardErrorBoundaryState {
  error: Error | null
}

// A render error in one card would otherwise unmount the whole dashboard. Query errors
// are handled inside each card; this only catches bugs thrown while rendering.
export class CardErrorBoundary extends Component<CardErrorBoundaryProps, CardErrorBoundaryState> {
  state: CardErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): CardErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`${this.props.title} failed to render`, error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle>{this.props.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <PanelMessage
              title="This panel crashed"
              description={this.state.error.message || 'An unexpected error occurred.'}
              tone="error"
            />
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}
