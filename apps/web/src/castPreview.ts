import { readSavedProfile } from './characterProfile'

export interface CastChoice {
  id: number
  name: string
  origin?: ProfileOrigin | null
}
export type ProfileOrigin =
  | { character_id: number; schema_version: 1; source: 'user_provided'; is_mock: null }
  | { character_id: number; schema_version: 2; source: 'reviewed_extraction'; is_mock: boolean }

export function originLabel(origin: ProfileOrigin): string {
  if (origin.source === 'user_provided') return 'Manual profile'
  return origin.is_mock
    ? 'Reviewed profile · Mock extraction'
    : 'Reviewed profile · Non-mock extraction'
}

export interface CastPreview {
  profile_origins: ProfileOrigin[]
  characters: { id: string; name: string }[]
  estimated_total_duration_seconds: number
  shots: {
    id: string
    order: number
    duration_seconds: number
    seed: number
    image_prompt: string
    motion_prompt: string
    negative_prompt: string
    visible_character_ids: string[]
  }[]
}
const invalid = () => new Error('Invalid mock preview response. Please try again.')
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid()
  return value as Record<string, unknown>
}
function text(value: unknown, max = 4000, empty = false): string {
  if (typeof value !== 'string' || (!empty && !value.trim()) || Array.from(value).length > max)
    throw invalid()
  return value
}
function number(value: unknown, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max)
    throw invalid()
  return value
}
export function readCastChoices(value: unknown): CastChoice[] {
  if (!Array.isArray(value)) throw invalid()
  const choices = value.map((item) => {
    const data = record(item)
    if (typeof data.id !== 'number' || !Number.isSafeInteger(data.id) || data.id < 1)
      throw invalid()
    return { id: data.id, name: text(data.name, 120) }
  })
  if (new Set(choices.map((c) => c.id)).size !== choices.length) throw invalid()
  return choices
}
function readOrigin(value: unknown, id: number): ProfileOrigin {
  const data = record(value)
  if (data.character_id !== id) throw invalid()
  if (data.schema_version === 1 && data.source === 'user_provided' && data.is_mock === null)
    return { character_id: id, schema_version: 1, source: 'user_provided', is_mock: null }
  if (
    data.schema_version === 2 &&
    data.source === 'reviewed_extraction' &&
    typeof data.is_mock === 'boolean'
  )
    return {
      character_id: id,
      schema_version: 2,
      source: 'reviewed_extraction',
      is_mock: data.is_mock,
    }
  throw invalid()
}

// Validate the displayed summary; the server validates full reviewed provenance.
export function readCastProfile(value: unknown, id: number): ProfileOrigin | null {
  if (value === null) return null
  const data = record(value)
  if (data.schema_version === 1) {
    readSavedProfile(value, id)
    return { character_id: id, schema_version: 1, source: 'user_provided', is_mock: null }
  }
  const profile = record(data.profile)
  const provenance = record(profile.provenance)
  const report = record(provenance.report)
  const review = record(provenance.review)
  if (
    data.character_id !== id ||
    data.schema_version !== 2 ||
    profile.schema_version !== 2 ||
    profile.character_id !== id ||
    profile.source !== 'reviewed_extraction' ||
    record(report.request).character_id !== id ||
    review.character_id !== id ||
    review.confirmed !== true ||
    report.status !== 'REVIEW_REQUIRED'
  )
    throw invalid()
  text(record(profile.values).name, 120)
  return readOrigin(
    {
      character_id: id,
      schema_version: 2,
      source: profile.source,
      is_mock: record(report.provider).is_mock,
    },
    id,
  )
}

// Validate the displayed subset and bind returned cast to the exact requested IDs.
// The API remains authoritative for the complete StoryPlan schema.
export function readCastPreview(value: unknown, selected: number[]): CastPreview {
  const body = record(value)
  if (body.is_mock !== true || body.status !== 'REVIEW_REQUIRED') throw invalid()
  if (!Array.isArray(body.profile_origins) || body.profile_origins.length !== selected.length)
    throw invalid()
  const origins = body.profile_origins.map((value, index) => readOrigin(value, selected[index]))
  const plan = record(body.plan)
  if (
    plan.schema_version !== 1 ||
    !Array.isArray(plan.characters) ||
    plan.characters.length !== selected.length
  )
    throw invalid()
  const characters = plan.characters.map((value, index) => {
    const character = record(value)
    if (character.id !== `character-${selected[index]}`) throw invalid()
    return { id: character.id as string, name: text(character.name, 120) }
  })
  const known = new Set(characters.map((c) => c.id))
  if (!Array.isArray(plan.shots) || plan.shots.length < 6 || plan.shots.length > 10) throw invalid()
  const shots = plan.shots.map((value, index) => {
    const shot = record(value)
    if (
      shot.order !== index + 1 ||
      shot.status !== 'pending' ||
      !Array.isArray(shot.visible_character_ids)
    )
      throw invalid()
    const visible = shot.visible_character_ids.map((id) => {
      if (typeof id !== 'string' || !known.has(id)) throw invalid()
      return id
    })
    if (new Set(visible).size !== visible.length || !Number.isInteger(shot.seed)) throw invalid()
    return {
      id: text(shot.id, 120),
      order: index + 1,
      duration_seconds: number(shot.duration_seconds, 3, 6),
      seed: number(shot.seed, 0, 2 ** 32 - 1),
      image_prompt: text(shot.image_prompt),
      motion_prompt: text(shot.motion_prompt),
      negative_prompt: text(shot.negative_prompt, 4000, true),
      visible_character_ids: visible,
    }
  })
  const duration = number(plan.estimated_total_duration_seconds, 30, 60)
  if (
    new Set(shots.map((s) => s.id)).size !== shots.length ||
    Math.abs(shots.reduce((sum, s) => sum + s.duration_seconds, 0) - duration) > 0.000001
  )
    throw invalid()
  return { characters, shots, profile_origins: origins, estimated_total_duration_seconds: duration }
}
