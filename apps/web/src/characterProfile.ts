export interface ProfileDraft {
  name: string
  description: string
  source: 'user_provided'
  visual_traits: {
    face: string
    hair: string
    eyes: string
    outfit: string
    colors: string[]
    accessories: string[]
  }
  negative_traits: string[]
}

export interface SavedProfile {
  character_id: number
  schema_version: 1
  created_at: string
  profile: ProfileDraft
}

export const profileFields = [
  ['name', 'Profile name', 120],
  ['description', 'Profile description', 4000],
  ['face', 'Face', 500],
  ['hair', 'Hair', 500],
  ['eyes', 'Eyes', 500],
  ['outfit', 'Outfit', 500],
] as const
export const profileLists = [
  ['colors', 'Colors', 1, 20],
  ['accessories', 'Accessories', 0, 20],
  ['negative_traits', 'Traits to avoid', 0, 100],
] as const
export type ProfileField = (typeof profileFields)[number][0] | (typeof profileLists)[number][0]
export type ProfileForm = Record<ProfileField, string>

function text(value: unknown, label: string, limit: number): string {
  if (typeof value !== 'string' || !value.trim() || Array.from(value.trim()).length > limit)
    throw new Error(`${label} must contain 1–${limit} characters.`)
  return value.trim()
}

function list(value: unknown, label: string, min: number, max: number): string[] {
  if (!Array.isArray(value) || value.length < min || value.length > max)
    throw new Error(`${label} must contain ${min}–${max} items.`)
  return value.map((item) => text(item, label, 500))
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value))
    throw new Error('Invalid profile response.')
  return value as Record<string, unknown>
}

function draft(value: unknown): ProfileDraft {
  const data = record(value)
  const traits = record(data.visual_traits)
  if (data.source !== 'user_provided') throw new Error('Invalid profile source.')
  return {
    name: text(data.name, 'Profile name', 120),
    description: text(data.description, 'Profile description', 4000),
    source: 'user_provided',
    visual_traits: {
      face: text(traits.face, 'Face', 500),
      hair: text(traits.hair, 'Hair', 500),
      eyes: text(traits.eyes, 'Eyes', 500),
      outfit: text(traits.outfit, 'Outfit', 500),
      colors: list(traits.colors, 'Colors', 1, 20),
      accessories: list(traits.accessories, 'Accessories', 0, 20),
    },
    negative_traits: list(data.negative_traits, 'Traits to avoid', 0, 100),
  }
}

export function profileFromForm(form: ProfileForm): ProfileDraft {
  const lines = (value: string) =>
    value
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
  return draft({
    name: form.name,
    description: form.description,
    source: 'user_provided',
    visual_traits: {
      face: form.face,
      hair: form.hair,
      eyes: form.eyes,
      outfit: form.outfit,
      colors: lines(form.colors),
      accessories: lines(form.accessories),
    },
    negative_traits: lines(form.negative_traits),
  })
}

export function readSavedProfile(value: unknown, characterId: number): SavedProfile {
  const data = record(value)
  if (
    data.character_id !== characterId ||
    data.schema_version !== 1 ||
    typeof data.created_at !== 'string'
  )
    throw new Error('Invalid profile response.')
  return {
    character_id: characterId,
    schema_version: 1,
    created_at: data.created_at,
    profile: draft(data.profile),
  }
}
