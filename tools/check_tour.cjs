const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

async function inspectViewport(page, width, height) {
  await page.setViewportSize({ width, height });
  await page.reload({ waitUntil: 'load' });
  return page.evaluate(() => {
    const visible = (element) => {
      const style = getComputedStyle(element);
      return style.display !== 'none' && style.visibility !== 'hidden';
    };
    const overflow = [...document.querySelectorAll('h1, p, button, textarea, svg, img')]
      .filter(visible)
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          text: (element.textContent || '').trim().slice(0, 80),
          left: Math.round(rect.left * 10) / 10,
          right: Math.round(rect.right * 10) / 10,
          width: Math.round(rect.width * 10) / 10,
        };
      })
      .filter((item) => item.left < -0.5 || item.right > window.innerWidth + 0.5);
    const root = document.getElementById('nova-tour').getBoundingClientRect();
    const logo = document.querySelector('.nova-brandlogo');
    return {
      viewport: window.innerWidth,
      documentClientWidth: document.documentElement.clientWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      root: { left: root.left, right: root.right, width: root.width },
      brand: logo ? {
        complete: logo.complete,
        naturalWidth: logo.naturalWidth,
        embedded: logo.currentSrc.startsWith('data:image/png;base64,'),
      } : null,
      overflow,
    };
  });
}

async function inspectFocusedControl(page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    const style = getComputedStyle(element);
    return {
      tag: element.tagName.toLowerCase(),
      text: (element.textContent || '').trim(),
      focusVisible: element.matches(':focus-visible'),
      outline: {
        style: style.outlineStyle,
        width: style.outlineWidth,
        offset: style.outlineOffset,
      },
    };
  });
}

function assertVisibleFocus(focus, expectedText) {
  assert.equal(focus.tag, 'button');
  assert.equal(focus.text, expectedText);
  assert.equal(focus.focusVisible, true, `${expectedText} is not :focus-visible`);
  assert.equal(focus.outline.style, 'solid', `${expectedText} has no solid focus outline`);
  assert.equal(focus.outline.width, '2px', `${expectedText} focus outline is not 2px`);
  assert.equal(focus.outline.offset, '2px', `${expectedText} focus outline offset is not 2px`);
}

function assertNoOverflow(layout, label) {
  assert.equal(layout.documentScrollWidth, layout.documentClientWidth, `${label} layout overflows`);
  assert.deepEqual(layout.overflow, [], `${label} visible element clips`);
}

function allDurationsAreZero(value) {
  return value.split(',').every((duration) => duration.trim() === '0s');
}

(async () => {
  const tour = path.resolve(process.argv[2]);
  const tourUrl = pathToFileURL(tour).href;
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu'],
  });
  try {
    const pointerContext = await browser.newContext();
    const page = await pointerContext.newPage();
    await page.goto(tourUrl, { waitUntil: 'load' });

    const wide = await inspectViewport(page, 900, 1000);
    const mobile = await inspectViewport(page, 390, 844);
    if (process.argv[3]) {
      await page.screenshot({ path: path.resolve(process.argv[3]), fullPage: false });
    }
    if (process.argv[4]) {
      await page.setViewportSize({ width: 900, height: 1000 });
      await page.reload({ waitUntil: 'load' });
      await page.screenshot({ path: path.resolve(process.argv[4]), fullPage: false });
    }
    let dark = null;
    let reducedMotion = null;
    if (process.argv[5]) {
      await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
      dark = await inspectViewport(page, 900, 1000);
      reducedMotion = await page.evaluate(() => {
        const coreHalo = getComputedStyle(document.querySelector('.core-halo'));
        const node = getComputedStyle(document.querySelector('.nova-map .node'));
        const spoke = getComputedStyle(document.querySelector('.nova-map .spoke'));
        return {
          mediaMatches: matchMedia('(prefers-reduced-motion: reduce)').matches,
          coreHaloAnimationName: coreHalo.animationName,
          nodeTransitionDuration: node.transitionDuration,
          spokeTransitionDuration: spoke.transitionDuration,
        };
      });
      await page.screenshot({ path: path.resolve(process.argv[5]), fullPage: false });
    } else {
      await page.emulateMedia({ reducedMotion: 'reduce' });
      reducedMotion = await page.evaluate(() => {
        const coreHalo = getComputedStyle(document.querySelector('.core-halo'));
        const node = getComputedStyle(document.querySelector('.nova-map .node'));
        const spoke = getComputedStyle(document.querySelector('.nova-map .spoke'));
        return {
          mediaMatches: matchMedia('(prefers-reduced-motion: reduce)').matches,
          coreHaloAnimationName: coreHalo.animationName,
          nodeTransitionDuration: node.transitionDuration,
          spokeTransitionDuration: spoke.transitionDuration,
        };
      });
    }

    assertNoOverflow(wide, 'wide');
    assertNoOverflow(mobile, 'mobile');
    assert.deepEqual(wide.brand, { complete: true, naturalWidth: 166, embedded: true });
    assert.deepEqual(mobile.brand, { complete: true, naturalWidth: 166, embedded: true });
    if (dark) {
      assertNoOverflow(dark, 'dark');
      assert.deepEqual(dark.brand, { complete: true, naturalWidth: 166, embedded: true });
    }
    assert.equal(reducedMotion.mediaMatches, true, 'reduced-motion media query does not match');
    assert.equal(reducedMotion.coreHaloAnimationName, 'none', 'core halo animation remains active');
    assert.equal(
      allDurationsAreZero(reducedMotion.nodeTransitionDuration),
      true,
      'node transitions remain active',
    );
    assert.equal(
      allDurationsAreZero(reducedMotion.spokeTransitionDuration),
      true,
      'spoke transitions remain active',
    );

    await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'no-preference' });
    await page.reload({ waitUntil: 'load' });
    await page.getByRole('button', { name: 'Research something slippery' }).click();
    assert.equal(
      await page.getByRole('button', { name: 'Research something slippery' }).getAttribute('aria-pressed'),
      'true',
    );
    assert.match(await page.locator('#nova-route-copy').innerText(), /sourced answer/i);
    await page.getByRole('button', { name: 'Show me how you keep it honest' }).click();
    assert.equal(await page.locator('[data-stage="proof"]').isVisible(), true);
    await page.getByRole('button', { name: 'What about memory and control?' }).click();
    assert.equal(await page.locator('[data-stage="control"]').isVisible(), true);
    assert.match(await page.locator('#nova-starter').inputValue(), /slippery claim/i);

    const keyboardContext = await browser.newContext({ viewport: { width: 900, height: 1000 } });
    const keyboardPage = await keyboardContext.newPage();
    await keyboardPage.goto(tourUrl, { waitUntil: 'load' });
    await keyboardPage.keyboard.press('Tab');
    const firstTabFocus = await inspectFocusedControl(keyboardPage);
    assertVisibleFocus(firstTabFocus, 'Untangle a decision');
    await keyboardPage.keyboard.press('Tab');
    const enterFocus = await inspectFocusedControl(keyboardPage);
    assertVisibleFocus(enterFocus, 'Research something slippery');
    await keyboardPage.keyboard.press('Enter');
    const enterRouteCopy = await keyboardPage.locator('#nova-route-copy').innerText();
    const enterActivation = {
      control: enterFocus.text,
      ariaPressed: await keyboardPage.locator('[data-route-button="research"]').getAttribute('aria-pressed'),
      matchedExpectedCopy: /sourced answer/i.test(enterRouteCopy),
    };
    assert.equal(enterActivation.ariaPressed, 'true');
    assert.equal(enterActivation.matchedExpectedCopy, true);
    await keyboardPage.keyboard.press('Tab');
    const spaceFocus = await inspectFocusedControl(keyboardPage);
    assertVisibleFocus(spaceFocus, 'Make something worth keeping');
    await keyboardPage.keyboard.press('Space');
    const spaceRouteCopy = await keyboardPage.locator('#nova-route-copy').innerText();
    const spaceActivation = {
      control: spaceFocus.text,
      ariaPressed: await keyboardPage.locator('[data-route-button="make"]').getAttribute('aria-pressed'),
      matchedExpectedCopy: /something made/i.test(spaceRouteCopy),
    };
    assert.equal(spaceActivation.ariaPressed, 'true');
    assert.equal(spaceActivation.matchedExpectedCopy, true);
    const keyboard = {
      tabFocusChecks: 3,
      firstTabFocus,
      enterFocus,
      enterActivation,
      spaceFocus,
      spaceActivation,
      activations: 2,
    };
    await keyboardContext.close();

    const touchContext = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true,
    });
    const touchPage = await touchContext.newPage();
    await touchPage.goto(tourUrl, { waitUntil: 'load' });
    const touchLayout = await inspectViewport(touchPage, 390, 844);
    assertNoOverflow(touchLayout, 'touch mobile');
    const touchPoints = await touchPage.evaluate(() => navigator.maxTouchPoints);
    assert.ok(touchPoints > 0, 'touch context exposes no touch points');
    await touchPage.locator('[data-route-button="play"]').tap();
    const touchRouteCopy = await touchPage.locator('#nova-route-copy').innerText();
    const touchRoute = {
      ariaPressed: await touchPage.locator('[data-route-button="play"]').getAttribute('aria-pressed'),
      matchedExpectedCopy: /world answers back/i.test(touchRouteCopy),
    };
    assert.equal(touchRoute.ariaPressed, 'true');
    assert.equal(touchRoute.matchedExpectedCopy, true);
    await touchPage.locator('[data-stage="routes"] [data-next]').tap();
    const proofVisible = await touchPage.locator('[data-stage="proof"]').isVisible();
    assert.equal(proofVisible, true);
    const touch = {
      hasTouch: true,
      maxTouchPoints: touchPoints,
      layout: touchLayout,
      routeActivation: touchRoute,
      proofStageVisible: proofVisible,
      tapActivations: 2,
    };
    await touchContext.close();

    const noJavaScriptContext = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    const noJavaScriptPage = await noJavaScriptContext.newPage();
    await noJavaScriptPage.goto(tourUrl, { waitUntil: 'load' });
    const noJavaScriptLayout = await inspectViewport(noJavaScriptPage, 390, 844);
    assertNoOverflow(noJavaScriptLayout, 'no-JavaScript mobile');
    const noJavaScript = await noJavaScriptPage.locator('noscript').evaluate((element) => ({
      visible: element.getBoundingClientRect().height > 0 && getComputedStyle(element).display !== 'none',
      text: element.innerText.trim(),
    }));
    assert.equal(noJavaScript.visible, true, 'noscript fallback is not visible');
    assert.match(noJavaScript.text, /Nova works without this interaction/i);
    assert.match(noJavaScript.text, /Starter:/i);
    assert.ok(noJavaScript.text.length >= 180, 'noscript fallback is not meaningfully complete');
    const noJavaScriptEvidence = {
      javaScriptEnabled: false,
      layout: noJavaScriptLayout,
      noscript: {
        visible: noJavaScript.visible,
        textLength: noJavaScript.text.length,
        hasCapabilitySummary: /enlists specialists/i.test(noJavaScript.text),
        hasStarter: /Starter:/i.test(noJavaScript.text),
      },
      assertions: 8,
    };
    assert.equal(noJavaScriptEvidence.noscript.hasCapabilitySummary, true);
    assert.equal(noJavaScriptEvidence.noscript.hasStarter, true);
    await noJavaScriptContext.close();

    const counts = {
      layoutViewports: dark ? 5 : 4,
      pointerActivations: 3,
      pointerAssertions: 5,
      keyboardTabFocusChecks: keyboard.tabFocusChecks,
      keyboardActivations: keyboard.activations,
      touchTapActivations: touch.tapActivations,
      reducedMotionProperties: 3,
      noJavaScriptAssertions: noJavaScriptEvidence.assertions,
      totalActivations: 7,
    };

    console.log(JSON.stringify({
      valid: true,
      wide,
      mobile,
      dark,
      interactions: 4,
      pointer: { interactions: 4, routeActivation: true, stageTransitions: 2, promptUpdate: true },
      keyboard,
      touch,
      reducedMotion,
      noJavaScript: noJavaScriptEvidence,
      counts,
    }, null, 2));
    await pointerContext.close();
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
