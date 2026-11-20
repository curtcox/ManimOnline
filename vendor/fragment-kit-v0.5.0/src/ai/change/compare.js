import { validateDocument } from './apply.js';
import { createBudget } from '../budget.js';
import { createChangeRequests } from './propose.js';
import { changePrompt } from '../prompts.js';
/** A private, in-memory blind comparison. Acceptance remains an explicit action. */
export async function compareChanges({ ai, type, request, models, budget, getSnapshot, getFingerprint, onApply, urlState, signal }) {
  if (!Array.isArray(models) || models.length < 2 || models.length > 4 || new Set(models).size !== models.length || models.some(m => m.startsWith('paste:'))) throw new Error('Choose 2–4 automated models.');
  const snapshot = structuredClone(getSnapshot()), fingerprint = getFingerprint(), cap = createBudget({ total: budget });
  const prompt = await changePrompt({ type, snapshot, request });
  const costs = models.map(model => ai.estimate({ model, messages: prompt.messages, maxTokens: 2048 }));
  // Refuse the entire comparison before making the first call.
  if (costs.reduce((a,b) => a+b,0) > budget) throw new Error('Comparison exceeds the budget.');
  const entries = [];
  const shuffled = models.map((model,i) => ({ model, cost:costs[i], order:crypto.getRandomValues(new Uint32Array(1))[0] })).sort((a,b) => a.order-b.order);
  for (const { model, cost } of shuffled) {
    signal?.throwIfAborted(); const reservation = cap.reserve(cost);
    const change = createChangeRequests({ ai, type, getSnapshot: () => snapshot, getFingerprint: () => fingerprint, onApply: () => {} });
    try {
      const proposal = await change.propose({ request, model, signal }); if (proposal.cost != null) reservation.settle(proposal.cost);
      const document = validateDocument(type, proposal.document); let accepted = false;
      entries.push({ label: String.fromCharCode(65+entries.length), model, proposal, accept() {
        if (accepted) throw new Error('This comparison was already accepted.');
        if (getFingerprint() !== fingerprint) throw new Error('The document changed during comparison. Regenerate before accepting.');
        const validated = validateDocument(type, document); onApply(structuredClone(validated)); urlState?.commit(validated, { previous: snapshot }); accepted = true; return validated;
      } });
    } catch (error) { if (signal?.aborted) throw error; entries.push({ label:String.fromCharCode(65+entries.length), model, error:'Request or validation failed.' }); }
  }
  return { entries, spent:cap.spent().total };
}
