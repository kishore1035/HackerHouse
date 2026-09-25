const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function capture() {
  const screenshotsDir = path.resolve(__dirname, '../docs/screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  console.log('Launching Edge browser...');
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  console.log('1. Navigating to dashboard...');
  await page.goto('http://127.0.0.1:8088/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // Screenshot 1: Main Dashboard Overview
  await page.screenshot({
    path: path.join(screenshotsDir, '01_main_dashboard.png'),
    fullPage: false,
  });
  console.log('Saved 01_main_dashboard.png');

  // Screenshot 2: How It Works Guide Modal
  const guideBtn = await page.$('.guide-trigger-btn');
  if (guideBtn) {
    console.log('Opening How It Works modal...');
    await guideBtn.click();
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(screenshotsDir, '02_how_it_works_modal.png'),
      fullPage: false,
    });
    console.log('Saved 02_how_it_works_modal.png');
    const closeBtn = await page.$('.modal-close-btn');
    if (closeBtn) await closeBtn.click();
    await page.waitForTimeout(500);
  }

  // Screenshot 3: Splash Modal Intro
  const splashBtn = await page.$('.splash-trigger-btn');
  if (splashBtn) {
    console.log('Opening Splash Intro modal...');
    await splashBtn.click();
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(screenshotsDir, '07_splash_intro.png'),
      fullPage: false,
    });
    console.log('Saved 07_splash_intro.png');
    const splashClose = await page.$('.splash-close-btn, .modal-close-btn');
    if (splashClose) await splashClose.click();
    await page.waitForTimeout(500);
  }

  // Screenshot 4: Execute Investigation
  console.log('Executing case investigation...');
  const execBtn = await page.locator('.case-top-bar button', { hasText: 'Execute Investigation' }).first();
  if (await execBtn.isVisible()) {
    console.log('Clicking Execute Investigation button...');
    await execBtn.click();
    
    // Wait for investigation to finish (button will say "Re-run Investigation" or gauge appears)
    console.log('Waiting for agent investigation to complete...');
    await page.waitForSelector('.gauge-box, .kpi-row', { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(3000);

    await page.screenshot({
      path: path.join(screenshotsDir, '03_case_investigated.png'),
      fullPage: false,
    });
    console.log('Saved 03_case_investigated.png');

    // Screenshot 5: Subgraph Topology
    console.log('Locating Subgraph Topology...');
    const topologyCard = await page.locator('.card', { hasText: 'Subgraph Topology' }).first();
    if (await topologyCard.isVisible()) {
      await topologyCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await page.screenshot({
        path: path.join(screenshotsDir, '04_topology_subgraph.png'),
        fullPage: false,
      });
      console.log('Saved 04_topology_subgraph.png');
    }

    // Screenshot 6: FinCEN SAR Report
    console.log('Locating FinCEN SAR Report...');
    const sarCard = await page.locator('.card', { hasText: 'Suspicious Activity Report' }).first();
    if (await sarCard.isVisible()) {
      await sarCard.scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      await page.screenshot({
        path: path.join(screenshotsDir, '05_fincen_sar_report.png'),
        fullPage: false,
      });
      console.log('Saved 05_fincen_sar_report.png');
    }
  } else {
    console.log('Execute button not found!');
  }

  // Screenshot 7: GRIP GraphRAG Studio
  console.log('Switching to GRIP GraphRAG studio...');
  // Scroll back to top
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  const gripNavBtn = await page.locator('.nav-switch-btn', { hasText: 'GRIP GRAPHRAG' }).first();
  if (gripNavBtn) {
    await gripNavBtn.click();
    await page.waitForTimeout(1500);

    const presetChip = await page.locator('.preset-chip', { hasText: 'out-of-region card fraud' }).first();
    if (presetChip) {
      await presetChip.click();
      await page.waitForTimeout(4000);
    }

    await page.screenshot({
      path: path.join(screenshotsDir, '06_grip_graphrag_studio.png'),
      fullPage: false,
    });
    console.log('Saved 06_grip_graphrag_studio.png');
  }

  await browser.close();
  console.log('All screenshots completed successfully!');
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});
