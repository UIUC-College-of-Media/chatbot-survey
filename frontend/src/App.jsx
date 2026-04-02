import { useState, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import { fetchJson } from './api'

export default function App() {
  const params = new URLSearchParams(window.location.search)
  const prolificId = params.get('prolific_id')?.trim() || ''
  return <HomeApp prolificId={prolificId} />
}

function HomeApp({ prolificId }) {
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!prolificId) return
    setLoading(true)
    fetchJson(`/api/v1/chat/start?prolific_id=${encodeURIComponent(prolificId)}`)
      .then(body => {
        setSession(body)
        setError('')
        setLoading(false)
      })
      .catch(err => {
        setError(err.message || String(err))
        setLoading(false)
      })
  }, [prolificId])

  if (!prolificId) {
    return (
      <div className="shell">
        <div className="card">
          <div className="header">
            <h1>Chat</h1>
            <p className="error">Missing prolific_id in URL. Expected: /?prolific_id=&lt;id&gt;</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="shell">
      <div className="card">
        <div className="header">
          <h1>Chat</h1>
          {loading && <p>Initializing session...</p>}
          {error && <p className="error">{error}</p>}
          {session && <p>prolific_id={prolificId}</p>}
        </div>
        {session && <ChatWindow prolificId={prolificId} initialSession={session} />}
      </div>
    </div>
  )
}
