import { compatibleDriver } from './openai-compatible.js';
export const openaiDriver = options => compatibleDriver({ ...options, provider: 'openai', baseURL: 'https://api.openai.com/v1/' });
