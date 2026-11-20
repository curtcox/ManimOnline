/** Deterministic provider fixtures. No live model or paid call in CI. */
export function mockAiResponse(body, { broken = false, stream = false } = {}) {
  const input = JSON.parse(body.messages.at(-1).content);
  const output = input.questions ? { answers: Object.fromEntries(Object.entries(input.questions).map(([name, q]) => [name, { type: q.type, choice: Object.keys(q.criteria)[0], probabilities: null }])) } : { summary: 'Update the note', edits: [{ find: input.document.src, replace: broken ? 'Wrong result' : input.request.includes('uppercase') ? input.document.src.toUpperCase() : 'Hello from AI' }] };
  const text = JSON.stringify(output), usage = { prompt_tokens: 100, completion_tokens: 30 };
  if (stream || body.stream) return new Response(`data: ${JSON.stringify({ model: 'mock-snapshot', provider:'fragment-kit-mock', choices: [{ delta: { content: text }, finish_reason: 'stop' }] })}\n\ndata: ${JSON.stringify({ model: 'mock-snapshot', provider:'fragment-kit-mock', choices: [], usage })}\n\ndata: [DONE]\n\n`, { headers: { 'Content-Type': 'text/event-stream' } });
  return Response.json({ model: 'mock-snapshot', provider:'fragment-kit-mock', choices: [{ message: { content: text }, finish_reason: 'stop' }], usage });
}
export const mockFetch = async (_url, opts) => mockAiResponse(JSON.parse(opts.body));
