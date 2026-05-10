import { useState } from 'react'

export default function MessageInput({ onSubmit, disabled }) {
  const [text, setText] = useState('')

  function submitMessage() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSubmit(trimmed)
    setText('')
  }

  function handleSubmit(e) {
    e.preventDefault()
    submitMessage()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submitMessage()
    }
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message (Enter to send, Shift+Enter for newline)"
        disabled={disabled}
      />
      <div className="composer-row">
        <button type="submit" disabled={disabled}>Send</button>
      </div>
    </form>
  )
}
