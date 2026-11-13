import { compatibleDriver } from './openai-compatible.js';
export const openrouterDriver = options => compatibleDriver({ ...options, provider: 'openrouter', baseURL: 'https://openrouter.ai/api/v1/' });
