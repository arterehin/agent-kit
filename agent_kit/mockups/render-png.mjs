/** Render SVGs to PNG next to them with a headless Chromium from Playwright.
 *
 * Usage: node render-png.mjs [--from <package.json>] <svg> [svg ...]
 * Playwright is resolved from --from (a package.json that depends on
 * @playwright/test or playwright), else from the current directory.
 */
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import path from 'node:path';

const args = process.argv.slice(2);
const fromIndex = args.indexOf('--from');
const anchor = fromIndex < 0 ? path.join(process.cwd(), 'package.json') : path.resolve(args[fromIndex + 1]);
const files = args.filter((_, index) => fromIndex < 0 || (index !== fromIndex && index !== fromIndex + 1))
  .map(file => path.resolve(file));

const require = createRequire(anchor);
let chromium;
for (const name of ['@playwright/test', 'playwright']) {
  try {
    ({ chromium } = require(name));
    break;
  } catch {
    // try the next package name
  }
}
if (!chromium) {
  console.error(`render-png: Playwright not found from ${anchor}; set "playwright" in boards.json or install playwright`);
  process.exit(2);
}

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  for (const file of files) {
    const source = await readFile(file, 'utf8');
    const [, width, height] = source.match(/<svg[^>]*width="(\d+)" height="(\d+)"/);
    await page.setViewportSize({ width: Number(width), height: Number(height) });
    await page.goto(pathToFileURL(file).href);
    await page.evaluate(async () => {
      document.documentElement.style.display = 'block';
      document.documentElement.style.margin = '0';
      await document.fonts.ready;
    });
    const target = file.replace(/\.svg$/, '.png');
    await page.screenshot({ path: target });
    console.log(`${path.relative(process.cwd(), target)} (${width}×${height})`);
  }
} finally {
  await browser.close();
}
