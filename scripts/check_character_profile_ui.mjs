// Uses an existing Playwright installation; does not install packages or browsers.
// PLAYWRIGHT_MODULE_PATH=/absolute/path/to/playwright node scripts/check_character_profile_ui.mjs
import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'
const modulePath = process.env.PLAYWRIGHT_MODULE_PATH
if (!modulePath) throw new Error('Set PLAYWRIGHT_MODULE_PATH to an existing Playwright package.')
const { chromium } = await import(pathToFileURL(resolve(modulePath, 'index.mjs')))
const { expect } = await import(pathToFileURL(resolve(modulePath, 'test.mjs')))
const base = process.env.PROFILE_UI_URL || 'http://127.0.0.1:5175'
const browser = await chromium.launch({ headless: true })
const failures = []
let passed = 0
const initial = [
  { id: 1, name: 'Legacy One', description: 'নদীর ধারে', created_at: '2026-10-12' },
  { id: 2, name: 'Legacy Two', description: null, created_at: '2026-10-12' },
]
const draft = {
  name: 'আলো',
  description: 'নদীর ধারে',
  source: 'user_provided',
  visual_traits: {
    face: 'গোল মুখ',
    hair: 'কালো চুল',
    eyes: 'বাদামি',
    outfit: 'নীল পোশাক',
    colors: ['নীল', 'সাদা'],
    accessories: [],
  },
  negative_traits: ['লাল পোশাক'],
}
const snapshot = (id, profile = draft) => ({
  character_id: id,
  schema_version: 1,
  created_at: '2026-10-12',
  profile,
})

async function scenario(name, run) {
  const context = await browser.newContext()
  const page = await context.newPage()
  page.setDefaultTimeout(5000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  const state = {
    characters: structuredClone(initial),
    profiles: {},
    posts: [],
    gets: [],
    getError: false,
    postMode: 'success',
    hold: null,
    invalid: false,
  }
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (pathname === '/characters') {
      if (request.method() === 'GET') return json(state.characters)
      const character = { id: 3, ...request.postDataJSON(), created_at: '2026-10-12' }
      state.characters.push(character)
      return json(character, 201)
    }
    const match = pathname.match(/^\/characters\/(\d+)\/profile$/)
    assert.ok(match, `Unexpected API call: ${pathname}`)
    const id = Number(match[1])
    if (request.method() === 'GET') {
      state.gets.push(id)
      if (state.hold) await state.hold(id)
      if (state.getError) return json({ detail: 'private diagnostic' }, 500)
      if (state.invalid) return json(snapshot(999))
      return json(state.profiles[id] ?? null)
    }
    state.posts.push({ id, payload: request.postDataJSON() })
    if (state.postMode === 'reject') return json({ detail: 'private diagnostic' }, 422)
    if (state.postMode === 'failure') return json({ detail: 'private diagnostic' }, 500)
    state.profiles[id] = snapshot(
      id,
      state.postMode === 'conflict' ? draft : request.postDataJSON(),
    )
    if (state.postMode === 'conflict') return json({ detail: 'Already saved' }, 409)
    if (state.postMode === 'timeout') {
      await new Promise((resolve) => setTimeout(resolve, 11000))
      return route.abort('timedout')
    }
    if (state.postMode === 'lost') return route.abort('failed')
    return json(state.profiles[id], 201)
  })
  const open = async () => {
    await page.goto(`${base}/#/characters`)
    await expect(page.getByRole('button', { name: 'View visual profile' }).first()).toBeVisible()
    await page.getByRole('button', { name: 'View visual profile' }).first().click()
  }
  const fill = async () => {
    const values = {
      name: ' আলো ',
      description: 'নদীর ধারে',
      ...draft.visual_traits,
      colors: 'নীল\n\nসাদা',
      accessories: '',
      negative_traits: 'লাল পোশাক',
    }
    for (const [field, value] of Object.entries(values))
      await page.locator(`[name="profile-${field}"]`).fill(value)
  }
  const save = () => page.getByRole('button', { name: 'Save immutable profile' }).click()
  try {
    await run({ page, state, open, fill, save })
    assert.deepEqual(errors, [])
    passed++
    console.log(`PASS ${name}`)
  } catch (error) {
    failures.push(name)
    console.error(`FAIL ${name}: ${error.message}`)
  } finally {
    await context.close()
  }
}

try {
  await scenario('empty library and legacy create', async ({ page, state }) => {
    state.characters = []
    await page.goto(`${base}/#/characters`)
    await expect(page.getByText('No characters yet.', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'View visual profile' })).toHaveCount(0)
    await page.locator('input[name="name"]').fill('New character')
    await page.getByRole('button', { name: 'Save character', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'New character', exact: true })).toBeVisible()
    assert.deepEqual(state.gets, [])
  })
  await scenario(
    'loading, empty form, Unicode save, double submit, refresh',
    async ({ page, state, open, fill, save }) => {
      let release
      state.hold = () =>
        new Promise((resolve) => {
          release = resolve
        })
      await open()
      await expect(page.getByText('Loading profile…', { exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Save immutable profile' })).toHaveCount(0)
      state.hold = null
      release()
      await expect(page.getByText('No visual profile saved yet.')).toBeVisible()
      await expect(page.locator('[name="profile-hair"]')).toHaveValue('')
      await fill()
      await page.locator('.character-traits-panel form').evaluate((form) => {
        form.requestSubmit()
        form.requestSubmit()
      })
      await expect(page.getByText('Saved profile · Read-only', { exact: true })).toBeVisible()
      assert.equal(state.posts.length, 1)
      assert.deepEqual(state.posts[0].payload, draft)
      await expect(page.locator('.character-traits-panel textarea')).toHaveCount(0)
      await page.reload()
      await page.getByRole('button', { name: 'View visual profile' }).first().click()
      await expect(page.getByRole('heading', { name: 'আলো', exact: true })).toBeVisible()
      await expect(
        page.locator('.character-traits-panel').getByText('কালো চুল', { exact: true }),
      ).toBeVisible()
      assert.equal(state.posts.length, 1)
    },
  )
  await scenario(
    'GET error cannot become editable, retry recovers',
    async ({ page, state, open }) => {
      state.getError = true
      await open()
      await expect(page.getByRole('button', { name: 'Retry profile load' })).toBeVisible()
      await expect(page.locator('.character-traits-panel textarea')).toHaveCount(0)
      await expect(page.getByText('private diagnostic')).toHaveCount(0)
      state.getError = false
      await page.getByRole('button', { name: 'Retry profile load' }).click()
      await expect(page.getByText('No visual profile saved yet.')).toBeVisible()
    },
  )
  await scenario(
    'required traits and length/count validation',
    async ({ page, state, open, fill, save }) => {
      await open()
      await fill()
      for (const [field, value, message] of [
        ['hair', ' ', 'Hair must contain'],
        ['face', 'x'.repeat(501), 'Face must contain'],
        ['name', 'x'.repeat(121), 'Profile name must contain'],
        ['description', 'x'.repeat(4001), 'Profile description must contain'],
        ['colors', Array(21).fill('blue').join('\n'), 'Colors must contain'],
        ['accessories', Array(21).fill('hat').join('\n'), 'Accessories must contain'],
        ['negative_traits', Array(101).fill('red').join('\n'), 'Traits to avoid must contain'],
      ]) {
        await fill()
        await page.locator(`[name="profile-${field}"]`).fill(value)
        await save()
        await expect(page.getByRole('alert')).toContainText(message)
        assert.equal(state.posts.length, 0)
      }
      await fill()
      await page.locator('[name="profile-hair"]').fill('😀'.repeat(500))
      await save()
      await expect(page.getByText('Saved profile · Read-only', { exact: true })).toBeVisible()
      assert.equal(Array.from(state.posts[0].payload.visual_traits.hair).length, 500)
    },
  )
  for (const mode of ['conflict', 'lost', 'timeout']) {
    await scenario(
      `${mode} save reconciles through GET without POST retry`,
      async ({ page, state, open, fill, save }) => {
        state.postMode = mode
        await open()
        await fill()
        const readsBeforeSave = state.gets.length
        await save()
        await expect(page.getByText('Saved profile · Read-only', { exact: true })).toBeVisible({
          timeout: 15000,
        })
        assert.equal(state.posts.length, 1)
        assert.equal(state.gets.length, readsBeforeSave + 1)
        assert.ok(state.gets.every((id) => id === 1))
      },
    )
  }
  await scenario(
    'failed save with null reconciliation preserves draft',
    async ({ page, state, open, fill, save }) => {
      state.postMode = 'failure'
      await open()
      await fill()
      const readsBeforeSave = state.gets.length
      await save()
      await expect(page.getByRole('alert')).toContainText('No saved profile was found')
      await expect(page.locator('[name="profile-hair"]')).toHaveValue('কালো চুল')
      assert.equal(state.posts.length, 1)
      assert.equal(state.gets.length, readsBeforeSave + 1)
      state.postMode = 'success'
      await save()
      await expect(page.getByText('Saved profile · Read-only', { exact: true })).toBeVisible()
    },
  )
  await scenario(
    'failed reconciliation locks save until successful GET',
    async ({ page, state, open, fill, save }) => {
      await open()
      await fill()
      state.postMode = 'failure'
      state.getError = true
      await save()
      await expect(page.getByRole('button', { name: 'Retry profile load' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Save immutable profile' })).toHaveCount(0)
      state.getError = false
      await page.getByRole('button', { name: 'Retry profile load' }).click()
      await expect(page.locator('[name="profile-hair"]')).toHaveValue('কালো চুল')
      assert.equal(state.posts.length, 1)
    },
  )
  await scenario('422 stays editable and sanitized', async ({ page, state, open, fill, save }) => {
    state.postMode = 'reject'
    await open()
    await fill()
    const readsBeforeSave = state.gets.length
    await save()
    await expect(page.getByRole('alert')).toContainText('profile was rejected')
    await expect(page.locator('[name="profile-hair"]')).toHaveValue('কালো চুল')
    await expect(page.getByText('private diagnostic')).toHaveCount(0)
    assert.equal(state.gets.length, readsBeforeSave)
  })
  await scenario('mismatched server identity is rejected', async ({ page, state, open }) => {
    state.invalid = true
    await open()
    await expect(page.getByRole('button', { name: 'Retry profile load' })).toBeVisible()
    await expect(page.getByText('Saved profile · Read-only', { exact: true })).toHaveCount(0)
  })
  await scenario(
    'late old GET cannot replace new selection; mobile layout',
    async ({ page, state, open }) => {
      let release
      state.hold = (id) =>
        id === 1
          ? new Promise((resolve) => {
              release = resolve
            })
          : Promise.resolve()
      state.profiles[1] = snapshot(1)
      await open()
      await expect(page.getByText('Loading profile…', { exact: true })).toBeVisible()
      await page.getByRole('button', { name: 'View visual profile' }).nth(1).click()
      await expect(page.getByRole('region', { name: 'Profile for Legacy Two' })).toBeVisible()
      await expect(page.locator('[name="profile-name"]')).toHaveValue('Legacy Two')
      release()
      await expect(page.locator('[name="profile-name"]')).toHaveValue('Legacy Two')
      await page.setViewportSize({ width: 390, height: 844 })
      assert.ok(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      )
      await page.screenshot({ path: '/tmp/character-profile-mobile.png', fullPage: true })
    },
  )
  await scenario(
    'navigation aborts pending save without leaking state',
    async ({ page, state, open, fill }) => {
      await open()
      await fill()
      let release
      await page.route('**/characters/1/profile', async (route) => {
        if (route.request().method() !== 'POST') return route.fallback()
        await new Promise((resolve) => {
          release = resolve
        })
        return route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(snapshot(1)),
        })
      })
      await page.getByRole('button', { name: 'Save immutable profile' }).click()
      await expect(page.getByRole('button', { name: 'Saving profile…' })).toBeDisabled()
      await page.getByRole('button', { name: 'View visual profile' }).nth(1).click()
      release()
      await expect(page.locator('[name="profile-name"]')).toHaveValue('Legacy Two')
      assert.deepEqual([...new Set(state.gets)], [1, 2])
    },
  )
} finally {
  await browser.close()
}
console.log(`${passed} browser scenarios passed; ${failures.length} failed.`)
if (failures.length) process.exitCode = 1
