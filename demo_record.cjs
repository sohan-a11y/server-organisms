'use strict';
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const REHEARSE = process.argv.includes('--rehearse');
const env = Object.fromEntries(fs.readFileSync('.env', 'utf8').split('\n').filter(l => l.includes('=')).map(l => { const i = l.indexOf('='); return [l.slice(0, i), l.slice(i + 1)]; }));
const URL = `http://127.0.0.1:18000/?token=${encodeURIComponent(env.BROKER_TOKEN || '')}`;
const OUT = path.join(__dirname, 'demo-output');

async function inject(page) {
  await page.evaluate(() => {
    if (!document.getElementById('demo-cursor')) {
      const c = document.createElement('div'); c.id = 'demo-cursor';
      c.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5"/></svg>';
      c.style.cssText = 'position:fixed;z-index:999999;pointer-events:none;transition:left .1s,top .1s;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.3))';
      document.body.appendChild(c);
      document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
    }
    if (!document.getElementById('demo-subtitle')) {
      const b = document.createElement('div'); b.id = 'demo-subtitle';
      b.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:999998;text-align:center;padding:12px;background:rgba(20,30,18,.82);color:#fff;font:500 16px sans-serif;opacity:0;pointer-events:none';
      document.body.appendChild(b);
    }
  });
}
const sub = async (page, t) => { await page.evaluate(x => { const b = document.getElementById('demo-subtitle'); if (b) { b.textContent = x; b.style.opacity = x ? '1' : '0'; } }, t); if (t) await page.waitForTimeout(700); };
async function click(page, sel, label, wait = 1200) {
  const el = page.locator(sel).first();
  if (!await el.isVisible().catch(() => false)) { console.error('FAIL not visible:', label, sel); return false; }
  await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(250);
  const box = await el.boundingBox();
  if (box) { await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 }); await page.waitForTimeout(350); }
  await el.click(); await page.waitForTimeout(wait); return true;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext(REHEARSE ? { viewport: { width: 1280, height: 720 } } : { viewport: { width: 1280, height: 720 }, recordVideo: { dir: OUT, size: { width: 1280, height: 720 } } });
  const page = await ctx.newPage();
  await page.goto(URL); await inject(page);
  const steps = [['#btn-exploit', 'Exploit'], ['#btn-heal', 'Heal'], ['#btn-kill', 'Kill'], ['#ask-q', 'Ask input'], ['#grid', 'Grid']];
  let ok = true;
  for (const [sel, label] of steps) { const v = await page.locator(sel).first().isVisible().catch(() => false); console.log((v ? 'REHEARSAL OK: ' : 'REHEARSAL FAIL: ') + label); ok = ok && v; }
  if (REHEARSE || !ok) { console.log(ok ? 'REHEARSAL PASSED' : 'REHEARSAL FAILED'); await browser.close(); return; }
  await sub(page, 'Server Organisms — life that guards your server');
  await page.waitForTimeout(1800);
  await sub(page, 'Step 1 — Attacker exploits the API');
  await click(page, '#btn-exploit', 'Exploit', 3000);
  await sub(page, 'Tissue is damaged. Swarm senses and converges.');
  await page.waitForTimeout(1800);
  await sub(page, 'Step 2 — Muse patches. Verifier judges on canary.');
  await click(page, '#btn-heal', 'Heal', 5000);
  await sub(page, 'Healed. Tissue regrows. Brain remembers.');
  await page.waitForTimeout(2200);
  await sub(page, 'Step 3 — Ask the organisms in English');
  await page.locator('#ask-q').fill('what stops sql injection?');
  await click(page, '#btn-ask', 'Ask', 2500);
  await sub(page, 'Step 4 — Kill switch: they do not own their off-switch');
  await click(page, '#btn-kill', 'Kill', 2500);
  await sub(page, '');
  await page.waitForTimeout(1500);
  await ctx.close();
  const files = fs.readdirSync(OUT).filter(f => f.endsWith('.webm')).map(f => path.join(OUT, f));
  const dest = path.join(OUT, 'demo-server-organisms.webm');
  if (files.length) { fs.copyFileSync(files[0], dest); console.log('Video saved:', dest); }
  await browser.close();
})();
