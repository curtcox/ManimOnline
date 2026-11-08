/** Wire-level adapter for baseline codec tests. App validators remain consumer-owned. */
export function corpusAdapter(corpus) {
  const wire = JSON.parse(corpus.example.raw);
  const type = corpus.slug;
  function unpack(payload) {
    let value; try { value = JSON.parse(payload); } catch { return { src: payload }; }
    if (!value || typeof value.src !== 'string') return { src: payload };
    const { format, version, type: language, ...fields } = value;
    if (language && language !== type) fields.legacyType = language;
    return fields;
  }
  return { type, settingsKeys: [], normalize: doc => ({ ...doc }), isDefault: doc => Object.keys(doc).length === 1,
    legacyEnvelopeTypes: [`${wire.format}:${wire.type ?? ''}`], parseLegacy: unpack };
}
