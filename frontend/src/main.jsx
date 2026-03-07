import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import { AuthProvider } from './contexts/AuthContext'
import { JobsProvider } from './contexts/JobsContext'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <JobsProvider>
          <App />
        </JobsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
