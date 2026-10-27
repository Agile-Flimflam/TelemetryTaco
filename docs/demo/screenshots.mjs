// Capture the README and portfolio screenshots from a running dashboard.
//
//   node docs/demo/screenshots.mjs [http://localhost:5173] [docs/assets]
//
// Needs Playwright (`npx playwright install chromium` once) and a stack with traffic from
// demo_traffic.py, so the chart and the stream have something to show.
import { mkdir, readFile } from "node:fs/promises";
import { chromium } from "playwright";

const baseUrl = process.argv[2] ?? "http://localhost:5173";
const outDir = process.argv[3] ?? "docs/assets";
const timezoneId = "America/Chicago";

// The chart's last point is the current, partial minute, so early in a minute it dips toward
// zero. Shoot late in the minute so it doesn't read as a traffic drop.
export async function waitForLateMinute() {
  const second = new Date().getSeconds();
  if (second < 40)
    await new Promise((resolve) => setTimeout(resolve, (45 - second) * 1000));
}

export async function openDashboard(
  browser,
  { width, height, scale, initScript },
) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: scale,
    colorScheme: "dark",
    timezoneId,
  });
  if (initScript) await context.addInitScript(initScript);
  const page = await context.newPage();
  await page.goto(baseUrl);
  // Wait for real data, then for the chart's draw-in animation to finish.
  await page.locator(".recharts-line-curve").waitFor();
  await page.getByText("props").first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(2500);
  return { context, page };
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const browser = await chromium.launch();

  for (const scale of [1, 2]) {
    await waitForLateMinute();
    const suffix = scale === 1 ? "" : "@2x";
    const { context, page } = await openDashboard(browser, {
      width: 1440,
      height: 900,
      scale,
    });
    await page.screenshot({ path: `${outDir}/dashboard${suffix}.png` });

    // Hover the chart so the tooltip shows a real reading.
    const chart = page.locator(".recharts-wrapper").first();
    const box = await chart.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.5);
      await page.waitForTimeout(400);
    }
    // The card stretches to the stream's height, so crop to the chart instead of the card.
    const insightsCard = await page.locator("main > *").first().boundingBox();
    if (box && insightsCard) {
      await page.screenshot({
        path: `${outDir}/insights${suffix}.png`,
        clip: {
          ...insightsCard,
          height: box.y + box.height + 28 - insightsCard.y,
        },
      });
    }
    await page.mouse.move(0, 0);

    // Expand a checkout event to show its properties.
    const row = page
      .locator("button", { hasText: "checkout_completed" })
      .first();
    await row.click();
    await page.waitForTimeout(400);
    const streamCard = page.locator("main > *").nth(1);
    await streamCard.screenshot({
      path: `${outDir}/event-stream${suffix}.png`,
    });
    await context.close();
  }

  await frame(browser, `${outDir}/dashboard@2x.png`, `${outDir}/hero.png`);
  await browser.close();
}

// A window-framed copy on a warm backdrop, for the portfolio site and social previews.
async function frame(browser, screenshotPath, outPath) {
  const image = (await readFile(screenshotPath)).toString("base64");
  const page = await browser.newPage({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
  });
  await page.setContent(`
    <body style="margin:0;height:100vh;display:grid;place-items:center;
      background:radial-gradient(circle at 15% 10%,#ff8c39 0,transparent 45%),
        radial-gradient(circle at 90% 90%,#ffd663 0,transparent 40%),#1a1410">
      <div style="width:1120px;border-radius:14px;overflow:hidden;background:#0c0e12;
        box-shadow:0 40px 120px -20px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.08)">
        <div style="height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;background:#181b22">
          <span style="width:12px;height:12px;border-radius:50%;background:#ff5f57"></span>
          <span style="width:12px;height:12px;border-radius:50%;background:#febc2e"></span>
          <span style="width:12px;height:12px;border-radius:50%;background:#28c840"></span>
        </div>
        <img src="data:image/png;base64,${image}" style="display:block;width:100%">
      </div>
    </body>`);
  await page.screenshot({ path: outPath });
  await page.close();
}

if (import.meta.url === `file://${process.argv[1]}`) await main();
