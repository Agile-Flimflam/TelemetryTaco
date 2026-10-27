// Record the README walkthrough: a ~15 second tour of the live dashboard, exported as MP4,
// WebM and a GIF.
//
//   node docs/demo/walkthrough.mjs [http://localhost:5173] [docs/assets]
//
// Needs Playwright, ffmpeg, and live traffic from demo_traffic.py. Frames come from the
// DevTools screencast rather than Playwright's recordVideo, which encodes at a low bitrate.
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";
import { openDashboard, waitForLateMinute } from "./screenshots.mjs";

const outDir = process.argv[3] ?? "docs/assets";

// Headless Chromium draws no pointer, so draw one that follows the mouse.
const cursorScript = `
  window.addEventListener('DOMContentLoaded', () => {
    const cursor = document.createElement('div')
    cursor.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:99999;' +
      'pointer-events:none;border-radius:50%;background:rgba(255,255,255,.9);' +
      'box-shadow:0 0 0 4px rgba(255,140,57,.45),0 4px 14px rgba(0,0,0,.5);' +
      'transform:translate(-50%,-50%);transition:transform .12s'
    document.body.appendChild(cursor)
    window.addEventListener('mousemove', (e) => {
      cursor.style.left = e.clientX + 'px'
      cursor.style.top = e.clientY + 'px'
    })
    window.addEventListener('mousedown', () => (cursor.style.transform = 'translate(-50%,-50%) scale(.7)'))
    window.addEventListener('mouseup', () => (cursor.style.transform = 'translate(-50%,-50%)'))
  })`;

async function tour(page) {
  const pause = (ms) => page.waitForTimeout(ms);
  const glide = (x, y, steps = 40) => page.mouse.move(x, y, { steps });

  await page.mouse.move(720, 120);
  await pause(2500);

  // Sweep the chart so the tooltip reads out minute by minute.
  const chart = await page.locator(".recharts-wrapper").first().boundingBox();
  const chartY = chart.y + chart.height * 0.45;
  await glide(chart.x + 70, chartY, 30);
  await page.mouse.move(chart.x + chart.width - 30, chartY, { steps: 150 });
  await pause(800);

  // Open an event to show its properties.
  const row = page.locator("main > *").nth(1).locator("button").nth(2);
  const rowBox = await row.boundingBox();
  await glide(rowBox.x + 120, rowBox.y + rowBox.height / 2, 45);
  await pause(300);
  await page.mouse.down();
  await page.mouse.up();
  await pause(4000);

  // New events keep arriving above the open one. Then finish back on the chart.
  await glide(chart.x + chart.width * 0.62, chartY, 45);
  await pause(2500);
}

async function encode(frames, framesDir) {
  // The screencast only sends a frame when something changes, so give each one its real duration.
  const lines = [];
  frames.forEach((frame, i) => {
    const next = frames[i + 1]?.timestamp ?? frame.timestamp + 0.5;
    lines.push(
      `file '${frame.file}'`,
      `duration ${(next - frame.timestamp).toFixed(4)}`,
    );
  });
  lines.push(`file '${frames.at(-1).file}'`);
  const list = join(framesDir, "frames.txt");
  await writeFile(list, lines.join("\n"));

  const input = [
    "-y",
    "-loglevel",
    "error",
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    list,
  ];
  const run = (args) =>
    execFileSync("ffmpeg", [...input, ...args], { stdio: "inherit" });
  run([
    "-vf",
    "fps=30,format=yuv420p",
    "-c:v",
    "libx264",
    "-crf",
    "20",
    "-preset",
    "slow",
    "-movflags",
    "+faststart",
    join(outDir, "walkthrough.mp4"),
  ]);
  run([
    "-vf",
    "fps=30",
    "-c:v",
    "libvpx-vp9",
    "-crf",
    "34",
    "-b:v",
    "0",
    "-row-mt",
    "1",
    join(outDir, "walkthrough.webm"),
  ]);
  run([
    "-vf",
    "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];" +
      "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
    join(outDir, "walkthrough.gif"),
  ]);
}

async function main() {
  await mkdir(outDir, { recursive: true });
  const framesDir = await mkdtemp(join(tmpdir(), "taco-frames-"));
  const browser = await chromium.launch();

  // Start late in the minute so the chart's last point isn't a partial-minute dip all tour long.
  await waitForLateMinute();
  const { context, page } = await openDashboard(browser, {
    width: 1440,
    height: 900,
    scale: 1,
    initScript: cursorScript,
  });

  const cdp = await context.newCDPSession(page);
  const frames = [];
  const writes = [];
  cdp.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
    const file = join(
      framesDir,
      `${String(frames.length).padStart(5, "0")}.jpg`,
    );
    frames.push({ file, timestamp: metadata.timestamp });
    writes.push(writeFile(file, Buffer.from(data, "base64")));
    cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 95 });
  await tour(page);
  await cdp.send("Page.stopScreencast");
  await Promise.all(writes);
  await context.close();
  await browser.close();

  await encode(frames, framesDir);
  await rm(framesDir, { recursive: true });
  console.log(`Recorded ${frames.length} frames.`);
}

await main();
