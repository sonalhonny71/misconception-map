import { test, expect } from '@playwright/test'

// Plays a whole session in the browser: new learner -> level 3 -> every question -> progress page.
test('Full journey: new learner to results', async ({ page }) => {
  test.setTimeout(120000)
  await page.goto('/')
  await expect(page.locator('h1')).toContainText('Learn from every answer')

  await page.goto('/journey/new?level=3')
  const phases: string[] = []
  for (let step = 0; step < 30; step++) {
    await expect(page.locator('input[type="radio"]').first()).toBeVisible({ timeout: 10000 })
    phases.push((await page.locator('#journey-step').innerText()).split('·')[0].trim().toLowerCase())
    // Alternate: wrong-ish first option on diagnostic, then first option
    await page.locator('label.option').first().click()
    await page.click('button:has-text("Check answer")')
    await expect(page.locator('#answer-feedback')).toBeVisible()
    await page.click('#answer-continue')
    if (page.url().endsWith('/progress')) break
  }
  await expect(page).toHaveURL(/\/progress$/)
  await expect(page.locator('h1')).toContainText('Progress & achievements')
  await expect(page.getByText('Total XP')).toBeVisible()
  await page.screenshot({ path: 'test-results/final-progress.png', fullPage: true })
  console.log('PHASES SEEN:', phases.join(' > '))
  expect(phases).toContain('fresh retest')
})
