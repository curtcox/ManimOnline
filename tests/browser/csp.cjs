// Collects Content-Security-Policy violations from every page a browser opens.
module.exports = function watchCSP(browser) {
  const violations = [];
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async options => {
    const context = await newContext(options);
    await context.exposeBinding('__cspViolation', (_, text) => violations.push(text));
    await context.addInitScript(() => addEventListener('securitypolicyviolation', event =>
      globalThis.__cspViolation?.(`${event.violatedDirective} ${event.blockedURI} ${location.pathname}`)));
    return context;
  };
  browser.newPage = async options => {
    const context = await browser.newContext(options);
    const page = await context.newPage();
    page.on('close', () => context.close().catch(() => {}));
    return page;
  };
  // Proves the policy is active: a script from an unlisted host must be refused and reported.
  violations.probe = async page => {
    await page.evaluate(() => { const script = document.createElement('script'); script.src = 'https://example.invalid/injected.js'; document.head.append(script); });
    for (let tries = 0; !violations.some(text => text.includes('example.invalid')); tries++) {
      if (tries > 100) throw new Error('Content-Security-Policy did not block an unlisted script host.');
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    violations.splice(0, violations.length, ...violations.filter(text => !text.includes('example.invalid')));
  };
  violations.check = () => { if (violations.length) throw new Error('Content-Security-Policy violations: ' + violations.join('; ')); };
  return violations;
};
