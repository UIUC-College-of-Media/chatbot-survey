import { useState, useEffect, useRef } from 'react'
import { fetchJson, fetchStream } from '../api'
import MessageInput from './MessageInput'
import MarkdownMessage from './MarkdownMessage'

export default function ChatWindow({ prolificId, initialSession }) {
  const [chatHistory, setChatHistory] = useState(initialSession || null)
  const [status, setStatus] = useState('')
  const [statusError, setStatusError] = useState(false)
  const [sending, setSending] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState(null)
  const [hasSentMessage, setHasSentMessage] = useState(false)
  const messagesRef = useRef(null)
  const scrollModeRef = useRef('none') // 'bottom' | 'top-user' | 'none'
  const exchangeStartIdxRef = useRef(0)

  useEffect(() => {
    loadHistory()
  }, [prolificId])

  useEffect(() => {
    if (chatHistory) console.log('[ChatWindow] condition_label:', chatHistory.condition_label)
    const mode = scrollModeRef.current
    scrollModeRef.current = 'none'
    if (mode === 'bottom') {
      setTimeout(() => {
        if (messagesRef.current) messagesRef.current.scrollTop = messagesRef.current.scrollHeight
      }, 0)
    } else if (mode === 'top-user') {
      setTimeout(() => {
        const container = messagesRef.current
        if (!container) return
        const userMsgs = container.querySelectorAll('.msg.user')
        const last = userMsgs[userMsgs.length - 1]
        if (last) {
          const rect = last.getBoundingClientRect()
          const containerRect = container.getBoundingClientRect()
          container.scrollTop += rect.top - containerRect.top
        }
      }, 0)
    }
  }, [chatHistory])

  function showStatus(text, isError = false) {
    setStatus(text)
    setStatusError(isError)
  }

  async function loadHistory() {
    try {
      const body = await fetchJson(`/api/v1/chat/session/${encodeURIComponent(prolificId)}`)
      scrollModeRef.current = 'bottom'
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
    exchangeStartIdxRef.current = (chatHistory.messages || []).length
    setHasSentMessage(true)
    scrollModeRef.current = 'top-user'
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

  const allMessages = chatHistory?.messages || []
  const prevMessages = hasSentMessage ? allMessages.slice(0, exchangeStartIdxRef.current) : allMessages
  const exchangeMessages = hasSentMessage ? allMessages.slice(exchangeStartIdxRef.current) : []
  const hasMessages = allMessages.length > 0 || streamingMessage !== null

  return (
    <section className="workspace">
      <div className="workspace-layout">
        <main className="panel">
          <div className="section">
            {chatHistory ? `Topic: ${chatHistory.topic}` : 'No active chat session.'}
          </div>
          <div className={`messages${hasMessages ? ' messages--active' : ''}`} ref={messagesRef}>
            {!hasSentMessage
              ? (!chatHistory || !allMessages.length
                  ? <div>No messages yet.</div>
                  : allMessages.map((m, i) => (
                      <div key={i} className={`msg ${m.role}`}>
                        <strong>{m.role}</strong>
                        {m.role === 'assistant'
                          ? <MarkdownMessage content={m.content} />
                          : <p>{m.content}</p>}
                      </div>
                    ))
                )
              : (
                <>
                  {prevMessages.map((m, i) => (
                    <div key={i} className={`msg ${m.role}`}>
                      <strong>{m.role}</strong><br />{m.content}
                    </div>
                  ))}
                  <div className="current-exchange">
                    {exchangeMessages.map((m, i) => (
                      <div key={i} className={`msg ${m.role}`}>
                        <strong>{m.role}</strong>
                        {m.role === 'assistant'
                          ? <MarkdownMessage content={m.content} />
                          : <p>{m.content}</p>}
                      </div>
                    ))}
                    {streamingMessage !== null && (
                      <div className="msg assistant streaming">
                        <strong>assistant</strong>
                        <MarkdownMessage content={streamingMessage} /><span className="cursor">▌</span>
                      </div>
                    )}
                    <div className="messages-spacer" />
                  </div>
                </>
              )
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
