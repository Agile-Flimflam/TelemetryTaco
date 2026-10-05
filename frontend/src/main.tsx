import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/app/App'
import { AppProviders } from '@/app/providers'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </StrictMode>,
)
