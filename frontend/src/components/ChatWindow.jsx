import { useState, useEffect, useRef } from 'react'
import { fetchJson } from '../api'
import MessageInput from './MessageInput'

export default function ChatWindow({ prolificId, initialSession }) {
  const [chatHistory, setChatHistory] = useState(initialSession || null)
  const [status, setStatus] = useState('')
  const [statusError, setStatusError] = useState(false)
  const [sending, setSending] = useState(false)
  const messagesRef = useRef(null)

  useEffect(() => {
    loadHistory()
  }, [prolificId])

  useEffect(() => {
    scrollToBottom()
  }, [chatHistory])

  function scrollToBottom() {
    setTimeout(() => {
      if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }, 0)
  }

  function showStatus(text, isError = false) {
    setStatus(text)
    setStatusError(isError)
  }

  async function loadHistory() {
    try {
      const body = await fetchJson(`/api/v1/chat/session/${encodeURIComponent(prolificId)}`)
      setChatHistory(body)
      showStatus('')
    } catch (err) {
      setChatHistory(null)
      showStatus(String(err.message || err), true)
    }
  }

  async function onSend(text) {
    if (sending || !chatHistory) return
    setSending(true)
    showStatus('Waiting for assistant reply...')
    const clientMessageId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    try {
      const body = await fetchJson('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prolific_id: prolificId,
          message: text,
          client_message_id: clientMessageId
        })
      })
      setChatHistory((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          messages: [...(prev.messages || []), body.user_message, body.assistant_message]
        }
      })
      showStatus('')
    } catch (err) {
      showStatus(String(err.message || err), true)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="workspace">
      <div className="workspace-layout">
        <main className="panel">
          <div className="section">
            {chatHistory
              ? `${chatHistory.condition_label} | Topic: ${chatHistory.topic}`
              : 'No active chat session.'}
          </div>
          <div className="messages" ref={messagesRef}>
            {!chatHistory || !chatHistory.messages || chatHistory.messages.length === 0
              ? <div>No messages yet.</div>
              : chatHistory.messages.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <strong>{m.role}</strong><br />{m.content}
                </div>
              ))
            }
          </div>
          <div className={`status${statusError ? ' error' : ''}`}>{status}</div>
          <MessageInput
            onSubmit={onSend}
            disabled={sending || !chatHistory}
          />
        </main>
      </div>
    </section>
  )
}
