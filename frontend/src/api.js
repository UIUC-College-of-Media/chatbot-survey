export async function fetchJson(path, options = {}) {
  const response = await fetch(path, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'Request failed')
  return body
}

export async function fetchStream(path, options = {}, onChunk, onDone, onError) {
  const response = await fetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || 'Request failed')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() // keep incomplete fragment

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      let event
      try { event = JSON.parse(line.slice(6)) } catch { continue }

      if (event.error) { onError?.(new Error(event.error)); return }
      if (event.done) { onDone?.(event); return }
      if (event.chunk !== undefined) onChunk?.(event.chunk)
    }
  }
}
