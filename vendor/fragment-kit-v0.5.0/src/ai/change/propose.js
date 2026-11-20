import { changePrompt } from '../prompts.js';
import { applyOutput, validateDocument } from './apply.js';
import { diff } from './diff.js';
import { clone, abort, parseData, byteLimit } from '../data.js';
export function createChangeRequests({ ai, type, getSnapshot, getFingerprint, onApply, urlState }) {
  let revision = 0, controller, undoEntry;
  const sessions = new WeakMap(), proposals = new WeakMap();
  function cancel() { revision++; controller?.abort(); }
  async function prepare({ request, previousProposal }) {
    const current = revision, fingerprint = getFingerprint(), snapshot = validateDocument(type, getSnapshot());
    const prompt = await changePrompt({ type, snapshot, request, previousProposal });
    if (current !== revision) throw new Error('The change request was cancelled.');
    const session = Object.freeze({ ...prompt, snapshot: clone(snapshot), fingerprint });
    sessions.set(session, { current, snapshot, fingerprint }); return session;
  }
  function review(session, output, result = { model:'paste:chat', cost:0 }) {
    const saved = sessions.get(session);
    if (!saved || saved.current !== revision) throw new Error('This change request is no longer active.');
    output = parseData(output, byteLimit(type.ai?.maxBytes));
    const document = applyOutput({ type, snapshot: saved.snapshot, output });
    const proposal = Object.freeze({ summary: output?.summary ?? 'Proposed document', document: clone(document), diff: diff(saved.snapshot, document), promptHash: session.promptHash,
      model: result.model ?? 'paste:chat', cost: result.cost ?? null, stale: saved.fingerprint !== getFingerprint() });
    proposals.set(proposal, { ...saved, output: clone(typeof output === 'string' ? JSON.parse(output) : output), document });
    return proposal;
  }
  async function propose({ request, model, signal, onText, maxTokens = 2048, confirmedCost, refine }) {
    const previousProposal = refine ? proposals.get(refine)?.output : null;
    if (refine && !previousProposal) throw new Error('This refinement is no longer active.');
    cancel(); const current = revision; controller = new AbortController();
    const combined = signal ? AbortSignal.any([signal, controller.signal]) : controller.signal;
    const session = await prepare({ request, previousProposal }); abort(combined);
    const result = await ai.generate({ model, messages: session.messages, maxTokens, signal: combined, onText, confirmedCost });
    abort(combined); if (current !== revision) throw new Error('The change request was cancelled.');
    return review(session, result.json ?? result.text, result);
  }
  function apply(proposal) {
    const saved = proposals.get(proposal);
    if (!saved || saved.current !== revision) throw new Error('This proposal is no longer active.');
    const previous = validateDocument(type, getSnapshot());
    const doc = saved.fingerprint === getFingerprint() ? validateDocument(type, saved.document) : type.ai?.output === 'full' ? (() => { throw new Error('The document changed. Regenerate this full replacement.'); })() : applyOutput({ type, snapshot: previous, output: saved.output });
    onApply(clone(doc)); urlState?.commit(doc, { previous });
    undoEntry = { previous, fingerprint: getFingerprint() }; proposals.delete(proposal); return doc;
  }
  function undo() {
    if (!undoEntry) throw new Error('There is no accepted change to undo.');
    if (getFingerprint() !== undoEntry.fingerprint) throw new Error('The document changed after accepting. Use history to recover the earlier version.');
    const previous = validateDocument(type, getSnapshot()), doc = undoEntry.previous;
    onApply(clone(doc)); urlState?.commit(doc, { previous }); undoEntry = null; return doc;
  }
  return Object.freeze({ prepare, review, propose, apply, undo, cancel });
}
