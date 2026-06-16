import { useState, useEffect, useRef } from 'react'
import { fetchJson, fetchStream } from '../api'
import MessageInput from './MessageInput'

export default function ChatWindow({ prolificId, initialSession }) {
  const [chatHistory, setChatHistory] = useState(initialSession || null)
  const [status, setStatus] = useState('')
  const [statusError, setStatusError] = useState(false)
  const [sending, setSending] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState(null)
  const messagesRef = useRef(null)

  useEffect(() => {
    loadHistory()
  }, [prolificId])

  useEffect(() => {
    scrollToBottom()
    if (chatHistory) console.log('[ChatWindow] condition_label:', chatHistory.condition_label)
  }, [chatHistory])

  useEffect(() => {
    if (streamingMessage !== null) scrollToBottom()
  }, [streamingMessage])

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
    setStreamingMessage('')
    showStatus('Assistant is typing...')
    const clientMessageId = crypto.randomUUID()
    // optimistically append user message to chat history first
    setChatHistory((prev) => prev
      ? { ...prev, messages: [...(prev.messages || []), { role: 'user', content: text }] }
      : prev)
    try {
      await fetchStream(
        '/api/v1/chat/stream',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prolific_id: prolificId, message: text, client_message_id: clientMessageId }),
        },
        (chunk) => setStreamingMessage((prev) => prev + chunk),
        (doneEvent) => {
          setChatHistory((prev) => prev
            ? { ...prev, messages: [...(prev.messages || []).slice(0, -1), doneEvent.user_message, doneEvent.assistant_message] }
            : prev)
          setStreamingMessage(null)
          showStatus('')
        },
        (err) => { showStatus(String(err.message || err), true); setStreamingMessage(null); loadHistory() },
      )
    } catch (err) {
      showStatus(String(err.message || err), true)
      setStreamingMessage(null)
      loadHistory()
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="workspace">
      <div className="workspace-layout">
        <main className="panel">
          <div className="section">
            {chatHistory ? `Topic: ${chatHistory.topic}` : 'No active chat session.'}
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
            {streamingMessage !== null && (
              <div className="msg assistant streaming">
                <strong>assistant</strong><br />{streamingMessage}<span className="cursor">▌</span>
              </div>
            )}
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
