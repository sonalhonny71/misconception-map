import { test, expect } from '@playwright/test'

test.describe('MisconceptionMap E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('Landing page loads and shows hero', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Learn from every answer')
    await expect(page.locator('text=Start learning')).toBeVisible()
    await expect(page.locator('text=Find my level')).toBeVisible()
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
    await page.click('text=Algebra Essentials >> text=Start diagnostic')
    
    // Should navigate to journey page
    await expect(page.url()).toContain('/journey/')
    
    // Should show a question
    await expect(page.locator('text=Diagnostic')).toBeVisible()
    await expect(page.locator('input[type="radio"]')).toBeVisible()
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
    // Sidebar should be hidden on mobile
    await expect(page.locator('.sidebar')).toBeHidden()
  })

  test('Accessibility: no critical violations', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Run axe
    const accessibility = await page.evaluate(async () => {
      const axe = await import('axe-core')
      return await axe.default.run()
    })
    
    const criticalViolations = accessibility.violations.filter(v => v.impact === 'critical')
    const seriousViolations = accessibility.violations.filter(v => v.impact === 'serious')
    
    expect(criticalViolations).toHaveLength(0)
    expect(seriousViolations).toHaveLength(0)
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