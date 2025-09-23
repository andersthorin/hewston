import { Routes, Route, Navigate } from 'react-router-dom'
import RunsListContainer from './containers/RunsListContainer'
import RunDetailView from './views/RunDetail'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/runs" replace />} />
      <Route path="/runs" element={<RunsListContainer />} />
      <Route path="/runs/:run_id" element={<RunDetailView />} />
    </Routes>
  )
}

export default App
