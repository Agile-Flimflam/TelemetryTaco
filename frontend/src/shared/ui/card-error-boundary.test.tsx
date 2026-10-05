import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CardErrorBoundary } from '@/shared/ui/card-error-boundary'

function Broken(): never {
  throw new Error('chart exploded')
}

describe('CardErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders its children when nothing throws', () => {
    render(
      <CardErrorBoundary title="Event insights">
        <p>chart</p>
      </CardErrorBoundary>,
    )

    expect(screen.getByText('chart')).toBeInTheDocument()
  })

  it('contains a render error to its own card', () => {
    // React logs caught render errors; keep the test output clean.
    vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <div>
        <CardErrorBoundary title="Event insights">
          <Broken />
        </CardErrorBoundary>
        <p>other card</p>
      </div>,
    )

    expect(screen.getByText('Event insights')).toBeInTheDocument()
    expect(screen.getByText('This panel crashed')).toBeInTheDocument()
    expect(screen.getByText('chart exploded')).toBeInTheDocument()
    expect(screen.getByText('other card')).toBeInTheDocument()
  })
})
