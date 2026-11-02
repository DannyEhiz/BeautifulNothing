import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing.jsx'
import OrderSoon from './pages/OrderSoon.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/order" element={<OrderSoon />} />
      <Route path="*" element={<Landing />} />
    </Routes>
  )
}
