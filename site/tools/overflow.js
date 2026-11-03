const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  await p.goto(process.argv[2], { waitUntil: 'networkidle' }); await p.waitForTimeout(2000);
  const r = await p.evaluate(() => ['page scrollWidth ' + document.documentElement.scrollWidth + ' vs ' + window.innerWidth].concat([...document.querySelectorAll('body *')].filter(e => !e.closest('.tscroll') && e.getBoundingClientRect().right > window.innerWidth + 1).slice(0, 12).map(e => `${e.tagName}.${e.className} right=${Math.round(e.getBoundingClientRect().right)}`)));
  console.log(r.join('\n')); await p.screenshot({ path: '_shots/_vp390.png' }); await b.close(); })();
