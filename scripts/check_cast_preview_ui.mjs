// Requires an existing Playwright package and a running local Vite server; no installs.
import assert from 'node:assert/strict'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'
const modulePath = process.env.PLAYWRIGHT_MODULE_PATH
if (!modulePath) throw new Error('Set PLAYWRIGHT_MODULE_PATH to an existing Playwright package.')
const { chromium } = await import(pathToFileURL(resolve(modulePath, 'index.mjs')))
const { expect } = await import(pathToFileURL(resolve(modulePath, 'test.mjs')))
const base = process.env.CAST_UI_URL || 'http://127.0.0.1:5175'
const browser = await chromium.launch({ headless: true })
let passed = 0
const failures = []
const plan = (ids) => ({
  schema_version: 1,
  estimated_total_duration_seconds: 30,
  characters: ids.map((id) => ({ id: `character-${id}`, name: 'আলো' })),
  shots: Array.from({ length: 6 }, (_, i) => ({
    id: `shot-${i + 1}`,
    order: i + 1,
    duration_seconds: 5,
    seed: i + 1,
    status: 'pending',
    visible_character_ids: ids.map((id) => `character-${id}`),
    image_prompt: `নদীর ধারে\nhair: কালো চুল ${ids.join(',')}`,
    motion_prompt: 'ধীরে হাঁটা',
    negative_prompt: 'লাল পোশাক',
  })),
})
const origin = (id, mock) =>
  mock === undefined
    ? { character_id: id, schema_version: 1, source: 'user_provided', is_mock: null }
    : { character_id: id, schema_version: 2, source: 'reviewed_extraction', is_mock: mock }
const savedProfile = (id, mock) =>
  mock === undefined
    ? {
        character_id: id,
        schema_version: 1,
        created_at: '2026-10-12',
        profile: {
          name: 'আলো',
          description: 'Description',
          source: 'user_provided',
          visual_traits: {
            face: 'Face',
            hair: 'Hair',
            eyes: 'Eyes',
            outfit: 'Outfit',
            colors: ['Blue'],
            accessories: [],
          },
          negative_traits: [],
        },
      }
    : {
        character_id: id,
        schema_version: 2,
        profile: {
          character_id: id,
          schema_version: 2,
          source: 'reviewed_extraction',
          values: { name: 'আলো' },
          provenance: {
            report: {
              request: { character_id: id },
              provider: { is_mock: mock },
              status: 'REVIEW_REQUIRED',
            },
            review: { character_id: id, confirmed: true },
          },
        },
      }
const legacy = plan([])
legacy.shots.forEach((shot) => {
  shot.image_prompt = 'Original no-cast prompt'
})
async function scenario(name, run) {
  const context = await browser.newContext({ reducedMotion: 'reduce' })
  const page = await context.newPage()
  page.setDefaultTimeout(5000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  const state = {
    reviewed: {},
    missing: [],
    profileError: false,
    profileHold: null,
    profileCorrupt: null,
    choices: [
      { id: 1, name: 'Same name' },
      { id: 2, name: 'Same name' },
    ],
    listError: false,
    listHold: null,
    hold: null,
    posts: [],
    writes: [],
    status: 200,
    corrupt: null,
    lost: false,
  }
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (request.method() !== 'GET') state.writes.push(path)
    if (path === '/characters') {
      if (state.listHold) await state.listHold()
      return json(
        state.listError ? { detail: 'private-diagnostic' } : state.choices,
        state.listError ? 500 : 200,
      )
    }
    const profileMatch = path.match(/^\/v2\/characters\/(\d+)\/profile$/)
    if (profileMatch) {
      const id = Number(profileMatch[1])
      const value = state.missing.includes(id) ? null : savedProfile(id, state.reviewed[id])
      if (state.profileCorrupt && value) state.profileCorrupt(value)
      if (state.profileHold) await state.profileHold()
      return json(
        state.profileError ? { detail: 'private-diagnostic' } : value,
        state.profileError ? 500 : 200,
      )
    }
    if (path === '/jobs') return json([])
    if (/^\/projects\/\d+$/.test(path))
      return json({
        id: Number(path.split('/')[2]),
        title: 'Fixture project',
        master_prompt: 'নদীর ধারে',
        target_duration_seconds: 30,
        status: 'draft',
      })
    if (/^\/projects\/\d+\/plan$/.test(path)) {
      assert.equal(request.method(), 'GET', 'Preview must never write persisted plan')
      return json({ plan: legacy, revision: 0, approved: false, result: null })
    }
    assert.match(path, /^\/projects\/\d+\/mock-plan$/)
    assert.equal(request.method(), 'POST')
    const ids = request.postDataJSON().character_ids
    state.posts.push({ path, ids })
    const reply = {
      is_mock: true,
      status: 'REVIEW_REQUIRED',
      plan: plan(ids),
      profile_origins: ids.map((id) => origin(id, state.reviewed[id])),
    }
    if (state.corrupt) state.corrupt(reply)
    if (state.hold) await state.hold()
    if (state.lost) return route.abort('failed')
    return json(state.status === 200 ? reply : { detail: 'private-diagnostic' }, state.status)
  })
  const panel = page.getByRole('region', { name: 'Character mock preview', exact: true })
  const open = async () => {
    await page.goto(`${base}/#/projects/1`)
    await expect(panel).toBeVisible()
  }
  const choose = async (id) =>
    panel.getByRole('checkbox', { name: `Same name · ID ${id}`, exact: true }).check()
  const create = () =>
    panel.getByRole('button', { name: 'Create character preview', exact: true }).click()
  const success = () =>
    panel.getByText('Mock preview · Review required · Read-only', { exact: true })
  try {
    await run({ page, state, panel, open, choose, create, success })
    assert.deepEqual(errors, [])
    assert.ok(
      state.writes.every((path) => /^\/projects\/\d+\/mock-plan$/.test(path)),
      'Only preview POST is allowed',
    )
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
  await scenario(
    'loading, no automatic cast or preview, empty list',
    async ({ state, panel, open }) => {
      let release
      state.listHold = () =>
        new Promise((resolve) => {
          release = resolve
        })
      await open()
      await expect(panel.getByText('Loading preview characters…')).toBeVisible()
      await expect.poll(() => Boolean(release)).toBe(true)
      state.listHold = null
      state.choices = []
      release()
      await expect(panel.getByText('No saved characters yet.', { exact: false })).toBeVisible()
      assert.equal(state.posts.length, 0)
    },
  )
  await scenario('list error sanitized and retry works', async ({ state, panel, open }) => {
    state.listError = true
    await open()
    await expect(panel.getByRole('alert')).toContainText('Unable to load characters')
    await expect(panel.getByText('private-diagnostic')).toHaveCount(0)
    state.listError = false
    await panel.getByRole('button', { name: 'Retry character list' }).click()
    await expect(panel.getByRole('checkbox')).toHaveCount(2)
    await expect(panel.getByRole('button', { name: 'Create character preview' })).toBeDisabled()
    assert.equal(state.posts.length, 0)
  })
  await scenario(
    'explicit order, same-name IDs, Unicode, read-only, legacy plan unchanged, refresh resets',
    async ({ page, state, panel, open, choose, success }) => {
      await open()
      await choose(2)
      await choose(1)
      await panel.locator('form').evaluate((form) => {
        form.requestSubmit()
        form.requestSubmit()
      })
      await expect(success()).toBeVisible()
      assert.deepEqual(
        state.posts.map((p) => p.ids),
        [[2, 1]],
      )
      await expect(panel.getByRole('heading', { name: /Preview shot/ })).toHaveCount(6)
      await expect(panel.getByText('লাল পোশাক', { exact: true })).toHaveCount(6)
      await expect(panel.locator('.cast-preview-result textarea')).toHaveCount(0)
      await expect(panel.getByRole('button', { name: /save|approve|render/i })).toHaveCount(0)
      await expect(page.getByRole('textbox', { name: 'Shot 1 prompt', exact: true })).toHaveValue(
        'Original no-cast prompt',
      )
      await page.setViewportSize({ width: 390, height: 844 })
      assert.ok(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      )
      await panel.screenshot({ path: '/tmp/cast-preview-mobile.png' })
      await page.reload()
      await expect(panel.getByRole('checkbox')).toHaveCount(2)
      await expect(panel.locator('input:checked')).toHaveCount(0)
      await expect(success()).toHaveCount(0)
      assert.equal(state.posts.length, 1)
    },
  )
  for (const [status, message] of [
    [404, 'not found'],
    [409, 'no saved visual profile'],
    [422, 'prompt limits'],
    [500, 'Unable to create'],
  ]) {
    await scenario(
      `HTTP ${status} hides old result and allows manual retry`,
      async ({ state, panel, open, choose, create, success }) => {
        await open()
        await choose(1)
        await create()
        await expect(success()).toBeVisible()
        state.status = status
        await create()
        await expect(panel.getByRole('alert')).toContainText(message)
        await expect(success()).toHaveCount(0)
        await expect(panel.getByText('private-diagnostic')).toHaveCount(0)
        assert.equal(state.posts.length, 2)
        state.status = 200
        await create()
        await expect(success()).toBeVisible()
        assert.equal(state.posts.length, 3)
      },
    )
  }
  for (const [name, corrupt] of [
    [
      'mock marker',
      (r) => {
        r.is_mock = false
      },
    ],
    [
      'cast identity',
      (r) => {
        r.plan.characters[0].id = 'character-999'
      },
    ],
    [
      'timeline',
      (r) => {
        r.plan.shots[0].duration_seconds = 6
      },
    ],
    [
      'shot status',
      (r) => {
        r.plan.shots[0].status = 'completed'
      },
    ],
    [
      'visible identity',
      (r) => {
        r.plan.shots[0].visible_character_ids = ['character-999']
      },
    ],
  ]) {
    await scenario(
      `invalid ${name} rejected`,
      async ({ state, panel, open, choose, create, success }) => {
        state.corrupt = corrupt
        await open()
        await choose(1)
        await create()
        await expect(panel.getByRole('alert')).toContainText('Invalid mock preview response')
        await expect(success()).toHaveCount(0)
      },
    )
  }
  await scenario(
    'selection change aborts old request; newer result survives',
    async ({ state, panel, open, choose, create, success }) => {
      let release
      state.hold = () =>
        new Promise((resolve) => {
          release = resolve
        })
      await open()
      await choose(1)
      await create()
      await expect(panel.getByText('Creating read-only mock preview…')).toBeVisible()
      await expect.poll(() => Boolean(release)).toBe(true)
      await choose(2)
      await expect(panel.getByText('Creating read-only mock preview…')).toHaveCount(0)
      state.hold = null
      await create()
      await expect(success()).toBeVisible()
      release()
      await expect(panel.getByText('আলো · character-2', { exact: true })).toBeVisible()
      assert.deepEqual(
        state.posts.map((p) => p.ids),
        [[1], [1, 2]],
      )
      await panel.getByRole('checkbox', { name: 'Same name · ID 1', exact: true }).uncheck()
      await expect(success()).toHaveCount(0)
    },
  )
  await scenario(
    'project navigation aborts old preview and resets selection',
    async ({ page, state, panel, open, choose, create, success }) => {
      let release
      state.hold = () =>
        new Promise((resolve) => {
          release = resolve
        })
      await open()
      await choose(1)
      await create()
      await expect.poll(() => Boolean(release)).toBe(true)
      await page.evaluate(() => {
        window.location.hash = '#/projects/2'
      })
      await expect(panel.getByRole('checkbox')).toHaveCount(2)
      await expect(panel.locator('input:checked')).toHaveCount(0)
      state.hold = null
      release()
      await choose(2)
      await create()
      await expect(success()).toBeVisible()
      assert.equal(state.posts[1].path, '/projects/2/mock-plan')
      await expect(panel.getByText('আলো · character-1', { exact: true })).toHaveCount(0)
    },
  )
  await scenario(
    'reload characters clears result and selection',
    async ({ panel, open, choose, create, success }) => {
      await open()
      await choose(1)
      await create()
      await expect(success()).toBeVisible()
      await panel.getByRole('button', { name: 'Reload preview characters' }).click()
      await expect(panel.getByRole('checkbox')).toHaveCount(2)
      await expect(panel.locator('input:checked')).toHaveCount(0)
      await expect(success()).toHaveCount(0)
    },
  )
  await scenario(
    'network failure and real timeout have no automatic retry',
    async ({ state, panel, open, choose, create, success }) => {
      state.lost = true
      await open()
      await choose(1)
      await create()
      await expect(panel.getByRole('alert')).toContainText('failed or timed out')
      assert.equal(state.posts.length, 1)
      state.lost = false
      let release
      state.hold = () =>
        new Promise((resolve) => {
          release = resolve
        })
      await create()
      await expect(panel.getByRole('alert')).toContainText('failed or timed out', {
        timeout: 15000,
      })
      assert.equal(state.posts.length, 2)
      state.hold = null
      release()
      await expect(success()).toHaveCount(0)
    },
  )
  await scenario(
    'mixed saved profiles show origin in selection and result',
    async ({ state, panel, open, choose, create, success }) => {
      state.reviewed = { 1: true }
      await open()
      await expect(
        panel.getByText('Reviewed profile · Mock extraction', { exact: true }),
      ).toBeVisible()
      await choose(1)
      await choose(2)
      await create()
      await expect(success()).toBeVisible()
      await expect(
        panel
          .locator('.cast-preview-result')
          .getByText('Reviewed profile · Mock extraction', { exact: true }),
      ).toBeVisible()
      await expect(
        panel.locator('.cast-preview-result').getByText('Manual profile', { exact: true }),
      ).toBeVisible()
    },
  )
  await scenario(
    'non-mock extraction does not label plan real',
    async ({ state, panel, open, choose, create, success }) => {
      state.reviewed = { 1: false }
      await open()
      await choose(1)
      await create()
      await expect(success()).toBeVisible()
      await expect(
        panel
          .locator('.cast-preview-result')
          .getByText('Reviewed profile · Non-mock extraction', { exact: true }),
      ).toBeVisible()
    },
  )
  await scenario(
    'missing profile disabled; corrupt profile fails closed and retries',
    async ({ state, panel, open }) => {
      state.missing = [1]
      await open()
      await expect(
        panel.getByRole('checkbox', { name: 'Same name · ID 1', exact: true }),
      ).toBeDisabled()
      await expect(panel.getByText('No saved visual profile', { exact: true })).toBeVisible()
      state.missing = []
      state.reviewed = { 1: true }
      state.profileCorrupt = (p) => {
        p.character_id = 999
      }
      await panel.getByRole('button', { name: 'Reload preview characters' }).click()
      await expect(panel.getByRole('alert')).toContainText('Unable to load characters')
      state.profileCorrupt = null
      await panel.getByRole('button', { name: 'Retry character list' }).click()
      await expect(panel.getByRole('checkbox')).toHaveCount(2)
    },
  )
  await scenario('profile loading and error sanitized', async ({ state, panel, open }) => {
    const releases = []
    state.profileHold = () => new Promise((resolve) => releases.push(resolve))
    await open()
    await expect(panel.getByText('Loading preview characters…')).toBeVisible()
    await expect.poll(() => releases.length).toBe(2)
    state.profileError = true
    state.profileHold = null
    releases.forEach((release) => release())
    await expect(panel.getByRole('alert')).toContainText('Unable to load characters')
    await expect(panel.getByText('private-diagnostic')).toHaveCount(0)
  })
  for (const [name, corrupt] of [
    [
      'missing origins',
      (r) => {
        delete r.profile_origins
      },
    ],
    [
      'wrong origin identity',
      (r) => {
        r.profile_origins[0].character_id = 999
      },
    ],
    [
      'invalid mock type',
      (r) => {
        r.profile_origins[0] = {
          character_id: 1,
          schema_version: 2,
          source: 'reviewed_extraction',
          is_mock: 'true',
        }
      },
    ],
    [
      'mismatched source',
      (r) => {
        r.profile_origins[0].schema_version = 2
      },
    ],
  ]) {
    await scenario(name, async ({ state, panel, open, choose, create, success }) => {
      state.corrupt = corrupt
      await open()
      await choose(1)
      await create()
      await expect(panel.getByRole('alert')).toContainText('Invalid mock preview response')
      await expect(success()).toHaveCount(0)
    })
  }
  await scenario(
    'navigation during profile load discards stale labels',
    async ({ page, state, panel, open }) => {
      const releases = []
      state.reviewed = { 1: true }
      state.profileHold = () => new Promise((resolve) => releases.push(resolve))
      await open()
      await expect.poll(() => releases.length).toBe(2)
      state.reviewed = { 1: false }
      state.profileHold = null
      await page.evaluate(() => {
        window.location.hash = '#/projects/2'
      })
      await expect(
        panel.getByText('Reviewed profile · Non-mock extraction', { exact: true }),
      ).toBeVisible()
      releases.forEach((release) => release())
      await expect(
        panel.getByText('Reviewed profile · Mock extraction', { exact: true }),
      ).toHaveCount(0)
      await expect(panel.locator('input:checked')).toHaveCount(0)
    },
  )
  await scenario('selection limit and unsafe IDs fail closed', async ({ state, panel, open }) => {
    state.choices = Array.from({ length: 101 }, (_, i) => ({ id: i + 1, name: 'Same name' }))
    await open()
    for (let id = 1; id <= 100; id++)
      await panel.getByRole('checkbox', { name: `Same name · ID ${id}`, exact: true }).check()
    await expect(
      panel.getByRole('checkbox', { name: 'Same name · ID 101', exact: true }),
    ).toBeDisabled()
    state.choices = [{ id: Number.MAX_SAFE_INTEGER + 1, name: 'Unsafe' }]
    await panel.getByRole('button', { name: 'Reload preview characters' }).click()
    await expect(panel.getByRole('alert')).toContainText('Unable to load characters')
    assert.equal(state.posts.length, 0)
  })
} finally {
  await browser.close()
}
console.log(`${passed} browser scenarios passed; ${failures.length} failed.`)
if (failures.length) process.exitCode = 1
