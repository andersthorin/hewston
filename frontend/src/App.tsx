import { Routes, Route, Navigate } from 'react-router-dom'
import BacktestsListContainer from './containers/BacktestsListContainer'
import BacktestDetailView from './views/BacktestDetail'
import BFFPerformanceMonitor from './components/dev/BFFPerformanceMonitor'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/backtests" replace />} />
        {/* Canonical backtest routes only */}
        <Route path="/backtests" element={<BacktestsListContainer />} />
        <Route path="/backtests/:backtest_id" element={<BacktestDetailView />} />
      </Routes>

      {/* Development tools - only shown in dev mode with debug enabled */}
      <BFFPerformanceMonitor />
    </>
  )
}

export default App
