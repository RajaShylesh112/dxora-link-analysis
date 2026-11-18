// Optional UI check: npm install --no-save playwright && npx playwright install chromium
// BASE_URL=http://127.0.0.1:4000 CHROMIUM_PATH=/usr/bin/chromium node scripts/browser_check.cjs
const {chromium} = require('playwright');
const fs = require('node:fs');
(async () => {
  const options = {headless: true};
  if (process.env.CHROMIUM_PATH) options.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(options);
  const page = await browser.newPage({viewport: {width: 1440, height: 1100}, deviceScaleFactor: 1});
  const errors = [];
  const base = process.env.BASE_URL || 'http://127.0.0.1:4000';
  page.on('pageerror', error => errors.push(error.message));
  fs.mkdirSync('docs/evidence', {recursive: true});
  await page.goto(base, {waitUntil: 'networkidle'});
  await page.screenshot({path: 'docs/evidence/desktop-home.png', fullPage: true});
  await page.getByRole('button', {name: 'View illustrative report'}).click();
  await page.locator('#report').waitFor({state: 'visible'});
  await page.screenshot({path: 'docs/evidence/illustrative-report.png', fullPage: true});
  for (const label of ['02 Search', '03 SEO', '04 Services', '05 Audience']) {
    await page.getByRole('tab', {name: label, exact: true}).click();
  }
  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base);
  await page.screenshot({path: 'docs/evidence/mobile-home.png', fullPage: true});
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  await page.getByRole('button', {name: 'View illustrative report'}).click();
  await page.locator('#report').waitFor({state: 'visible'});
  await page.getByRole('tab', {name: '02 Search', exact: true}).click();
  await page.screenshot({path: 'docs/evidence/mobile-illustrative-report.png', fullPage: true});
  // Browser rendering must never interpret untrusted model text as HTML.
  await page.route('**/link-analysis', async route => {
    const data = JSON.parse(fs.readFileSync('app/static/sample-report.json', 'utf8'));
    data.brand.name = '<img src=x onerror="window.XSS=true">';
    await route.fulfill({json: data});
  });
  await page.getByLabel('Website URL', {exact: true}).fill('https://example.com');
  await page.getByRole('button', {name: 'Analyze website'}).click();
  await page.getByText('<img src=x onerror="window.XSS=true">', {exact: true}).waitFor();
  const xss = await page.evaluate(() => window.XSS === true);
  const result = {mode: 'illustrative fixture and intercepted UI request; no live LLM',
    browser: await browser.version(), pageErrors: errors, mobileOverflow: overflow,
    allFiveTabsNavigable: true, modelTextRenderedSafely: !xss};
  fs.writeFileSync('docs/evidence/browser-check.json', JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  await browser.close();
  if (errors.length || overflow || xss) process.exitCode = 1;
})().catch(error => {console.error(error.message); process.exitCode = 1;});
