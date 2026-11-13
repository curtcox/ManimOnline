export class AiError extends Error {
  constructor(code, message, { status, cause } = {}) { super(message, { cause }); this.name = 'AiError'; this.code = code; if (status !== undefined) this.status = status; }
}
