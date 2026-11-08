import { test, expect } from '@playwright/test';
import { adapter, ready, expectSource, expectWrittenURL } from './adapter.js';
test('360px layout has no overflow, uses tabs, and provides resource links with 44px targets', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 }); await ready(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByRole('tab', { name: adapter.tabs[0], exact: true })).toBeVisible();
  await page.getByRole('tab', { name: adapter.tabs[1], exact: true }).click(); await expect(page.locator(adapter.editor)).toBeHidden();
  await page.getByRole('tab', { name: adapter.tabs[0], exact: true }).click(); await expect(page.locator(adapter.editor)).toBeVisible();
  const targets = await page.locator('button:visible').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().height));
  expect(targets.every(height => height >= 44)).toBe(true);
  await adapter.openMore(page);
  for (const name of ['Docs ↗', 'Gallery ↗', 'GitHub ↗']) await expect(page.getByRole('dialog').getByRole('link', { name })).toBeVisible();
  const bounds = await page.getByRole('dialog').boundingBox(); expect(bounds.width).toBe(360); expect(bounds.height).toBe(640);
});
test('desktop header links and keyboard tab navigation remain accessible', async ({ page }) => {
  await page.setViewportSize({ width: 1800, height: 800 }); await ready(page);
  await expect(page.getByRole('navigation', { name: 'Resources' }).getByRole('link', { name: 'Docs ↗' })).toBeVisible();
  const ids=await page.locator('.fk-tabs [role=tab]').evaluateAll(nodes=>nodes.map(node=>node.id));
  expect(ids.every(Boolean)).toBe(true);expect(new Set(ids).size).toBe(ids.length);
  const broken=await page.locator('[role=tabpanel]').evaluateAll(nodes=>nodes.filter(node=>!document.getElementById(node.getAttribute('aria-labelledby'))).map(node=>node.id));
  expect(broken).toEqual([]);
  await page.setViewportSize({ width: 360, height: 640 });
  await page.getByRole('tab', { name: adapter.tabs[0], exact: true }).focus(); await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: adapter.tabs[1], exact: true })).toBeFocused();
});

test('More keeps its close control visible above scrolling content', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 }); await ready(page); await adapter.openMore(page);
  const dialog = page.getByRole('dialog').last();
  await dialog.locator('.fk-dialog-body').evaluate(body => {
    const content = document.createElement('p'); content.textContent = 'Extra settings '.repeat(2000); body.append(content);
    const section=document.createElement('div');section.hidden=true;const action=document.createElement('button');action.id='fk-hidden-action';action.textContent='Hidden action';section.append(action);body.append(section);
  });
  await expect(dialog.locator('#fk-hidden-action')).toBeHidden();
  const close = dialog.getByRole('button', { name: 'Close', exact: true });
  const box = await close.boundingBox();
  expect(box.y).toBeGreaterThanOrEqual(0); expect(box.y + box.height).toBeLessThanOrEqual(640);
  await dialog.locator('.fk-dialog-body').evaluate(body => { body.scrollTop = body.scrollHeight; });
  await close.click(); await expect(dialog).not.toBeVisible();
  await expect(page.locator(adapter.more)).toBeFocused();
});

test('desktop workspace views fill the workspace and preserve selection on resize', async ({ page }) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Consumer adapters test their own view state.');
  await page.setViewportSize({ width: 1200, height: 800 }); await ready(page);
  const write = page.getByRole('tab', { name: 'Write', exact: true });
  const read = page.getByRole('tab', { name: 'Read', exact: true });
  const split = page.getByRole('tab', { name: 'Split', exact: true });
  await expect(split).toHaveAttribute('aria-selected', 'true');
  await write.click(); await expect(page.locator('#preview-panel')).toBeHidden();
  const workspace = await page.locator('#workspace').boundingBox(), editor = await page.locator('#editor-panel').boundingBox();
  expect(Math.abs(workspace.width - editor.width)).toBeLessThan(3);
  await read.click(); await expect(page.locator('#editor-panel')).toBeHidden();
  await page.setViewportSize({ width: 360, height: 640 }); await expect(read).toHaveAttribute('aria-selected', 'true');
  await read.focus(); await page.keyboard.press('End'); await expect(split).toBeFocused();
  await expect(page.locator('#editor-panel')).toBeVisible(); await expect(page.locator('#preview-panel')).toBeVisible();
  await page.keyboard.press('Home'); await expect(write).toBeFocused(); await expect(page.locator('#preview-panel')).toBeHidden();
});
for (const colorScheme of ['light', 'dark']) test(`shared controls have readable text in ${colorScheme} mode`, async ({page}) => {
  await page.emulateMedia({colorScheme}); await ready(page); await adapter.openMore(page);
  const pairs=await page.locator('.fk-header button:visible, .fk-header input[type=button]:visible, #fk-more-drawer button:visible').evaluateAll(nodes=>nodes.filter(node=>!node.disabled).map(node=>({label:node.textContent||node.value,color:getComputedStyle(node).color,background:getComputedStyle(node).backgroundColor})));
  const luminance=css=>{const rgb=css.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];};
  expect(pairs.length).toBeGreaterThan(0);
  for(const pair of pairs){const a=luminance(pair.color),b=luminance(pair.background);expect((Math.max(a,b)+.05)/(Math.min(a,b)+.05),pair.label).toBeGreaterThanOrEqual(4.5);}
});

test('phone chrome keeps primary feedback visible while status details stay in More', async ({page}) => {
  test.skip(Boolean(process.env.FRAGMENT_KIT_CONTRACT_CONFIG), 'Consumer status adapters stay app-owned.');
  await page.setViewportSize({width:360,height:640}); await ready(page);
  await page.locator('.fk-status').evaluate(status=>{const primary=document.createElement('span');primary.id='primary-message';primary.setAttribute('data-fk-primary-status','');primary.textContent='Load failed';status.append(primary);});
  const summary=page.locator('.fk-status-summary');
  await expect(summary).toBeVisible();await expect(summary).toHaveText('Load failed');
  await page.locator('.fk-status #primary-message').evaluate(status=>{status.textContent='Rendered';});
  await expect(summary).toHaveText('Rendered');
  await page.setViewportSize({width:1200,height:800});await expect(summary).toBeHidden();
  await expect(page.locator('.fk-header .fk-status #primary-message')).toBeVisible();
});
