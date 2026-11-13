import { string } from '../data.js';
export const chatDestinations = Object.freeze({ chatgpt: 'https://chatgpt.com/', claude: 'https://claude.ai/new', gemini: 'https://gemini.google.com/' });
export function pasteHandoff(session, { clipboard = globalThis.navigator?.clipboard, open = (...args) => globalThis.open(...args) } = {}) {
  string(session.prompt, 'prompt', 5 * 1024 * 1024);
  return Object.freeze({ prompt: session.prompt, bytes: new TextEncoder().encode(session.prompt).length,
    copy: () => clipboard.writeText(session.prompt),
    open(chat = 'chatgpt') { if (!Object.hasOwn(chatDestinations, chat)) throw new Error('Unknown chat destination.'); return open(chatDestinations[chat], '_blank', 'noopener,noreferrer'); },
  });
}
