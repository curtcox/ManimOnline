import { validateDocument } from '../change/apply.js';
import { parseSuite } from './suite.js';
/** Judges are calibrated on both references; an uncalibrated judge exposes no scores. */
export async function calibrateJudge({ ai, type, suite: input, model, decoys, signal, maxTokens = 256 }) {
  const suite = parseSuite(input, type), references = suite.cases.filter(c => c.kind === 'change');
  if (!Array.isArray(decoys) || decoys.length < 1 || decoys.length > 20 || decoys.some(d => typeof d !== 'string' || !d.trim())) throw new Error('Judge calibration needs 1–20 decoy requests.');
  const answers = [];
  for (const c of references) for (const kind of ['good', 'bad']) {
    const document = c.reference[kind];
    const result = await ai.decide({ model, state: { base: c.base, document }, questions: { fulfilled: { type: 'choice', instructions: 'Which request does this changed document fulfill? Choose none when no request fits.', criteria: { target: c.request, ...Object.fromEntries(decoys.map((d, i) => ['decoy' + i, d])), none: 'None of these requests is fulfilled.' } } }, maxTokens, signal });
    answers.push({ case: c.id, kind, correct: kind === 'good' ? result.answers.fulfilled.choice === 'target' : result.answers.fulfilled.choice !== 'target' });
  }
  const correct = answers.filter(a => a.correct).length;
  return Object.freeze({ model, n: answers.length, accuracy: answers.length ? correct / answers.length : null, calibrated: answers.length > 0 && correct === answers.length, answers });
}
export async function judgeChange({ ai, type, calibration, model, base, document, request, decoys, signal }) {
  if (!calibration?.calibrated || calibration.model !== model) return { visible: false, score: null };
  const result = await ai.decide({ model, state: { base, document: validateDocument(type, document) }, questions: { fulfilled: { type: 'choice', instructions: 'Which request does the change fulfill?', criteria: { target: request, ...Object.fromEntries(decoys.map((d, i) => ['decoy' + i, d])), none: 'None' } } }, signal });
  return { visible: true, score: Number(result.answers.fulfilled.choice === 'target'), calibrationAccuracy: calibration.accuracy };
}
