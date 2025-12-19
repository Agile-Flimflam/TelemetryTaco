import { LiveEventStream } from '@/components/LiveEventStream'
import { InsightChart } from '@/components/InsightChart'

function App() {
  return (
    <div className="min-h-screen bg-[#2d2d2d] text-white">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-2 font-mono">TelemetryTaco</h1>
        <p className="text-gray-400 mb-8 font-mono">Lightweight telemetry tool</p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <InsightChart lookbackMinutes={60} />
        </div>
        <LiveEventStream />
      </div>
    </div>
  )
}

export default App

