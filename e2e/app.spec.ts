import { test, expect } from '@playwright/test'

test.describe('MisconceptionMap E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('Landing page loads and shows hero', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Learn from every answer')
    await expect(page.locator('text=Start learning')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Find my level', exact: true })).toBeVisible()
  })

  test('Navigation works', async ({ page }) => {
    await page.click('text=Learning Map')
    await expect(page.locator('h1')).toContainText('Your interactive learning pathway')
    
    await page.click('text=Practice & Quests')
    await expect(page.locator('h1')).toContainText('Practice & quests')
    
    await page.click('text=Insights')
    await expect(page.locator('h1')).toContainText('Insights & misconceptions')
    
    await page.click('text=Progress')
    await expect(page.locator('h1')).toContainText('Progress & achievements')
    
    await page.click('text=Find my level')
    await expect(page.locator('h1')).toContainText('Find your level')
  })

  test('Can start Level 3 diagnostic', async ({ page }) => {
    await page.click('text=Learning Map')
    await page.locator('article', { hasText: 'Algebra Essentials' }).getByText('Start diagnostic').click()
    
    // Should navigate to journey page
    await expect(page.url()).toContain('/journey/')
    
    // Should show a question
    await expect(page.locator('text=Diagnostic')).toBeVisible()
    await expect(page.locator('input[type="radio"]').first()).toBeVisible()
  })

  test('Answer flow works', async ({ page }) => {
    await page.goto('/journey/new?level=3')
    await page.waitForLoadState('networkidle')
    
    // Wait for question to load
    await expect(page.locator('text=Diagnostic')).toBeVisible({ timeout: 10000 })
    
    // Select first option
    await page.locator('input[type="radio"]').first().check()
    await page.click('button:has-text("Check answer")')
    
    // Should show feedback
    await expect(page.locator('.notice')).toBeVisible({ timeout: 5000 })
    
    // Continue
    await page.click('button:has-text("Next question")')
  })

  test('Mobile viewport works', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    await expect(page.locator('h1')).toContainText('Learn from every answer')
    // On a phone the sidebar becomes a compact top bar; the page must not scroll sideways
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(0)
  })

  test('Accessibility: no critical violations', async ({ browser }) => {
    // axe-core is injected as an inline script, which the app's strict security policy
    // (correctly) blocks, so this one test turns the policy check off.
    const context = await browser.newContext({ bypassCSP: true, baseURL: test.info().project.use.baseURL })
    const page = await context.newPage()
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Run axe
    await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
    const accessibility = await page.evaluate(async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return await (window as any).axe.run()
    })

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const criticalViolations = accessibility.violations.filter((v: any) => v.impact === 'critical')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const seriousViolations = accessibility.violations.filter((v: any) => v.impact === 'serious')
    
    expect(criticalViolations).toHaveLength(0)
    expect(seriousViolations).toHaveLength(0)
    await context.close()
  })

  test('Cold start handling', async ({ page }) => {
    // This test verifies the cold start UI appears
    // In practice, this would require a sleeping service
    await page.goto('/')
    // If service is cold, should show waking message
    // We just verify the page loads
    await expect(page.locator('h1')).toBeVisible({ timeout: 30000 })
  })
})