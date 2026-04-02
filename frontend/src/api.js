export async function fetchJson(path, options = {}) {
  const response = await fetch(path, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'Request failed')
  return body
}
