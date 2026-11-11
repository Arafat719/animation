import pytest
from pydantic import ValidationError

from animation_studio.domain.v1.character_profile import CharacterProfileDraft


def payload():
    return {
        'name': ' আলো ',
        'description': ' নদীর ধারে দাঁড়িয়ে থাকা চরিত্র। ',
        'visual_traits': {
            'face': 'গোল মুখ',
            'hair': 'কালো চুল',
            'eyes': 'বাদামি চোখ',
            'outfit': 'নীল পোশাক',
            'colors': ['নীল', 'সাদা'],
            'accessories': ['রুপার ঘড়ি'],
        },
        'negative_traits': ['লাল পোশাক'],
    }


def test_unicode_roundtrip_and_independent_immutable_snapshot():
    data = payload()
    profile = CharacterProfileDraft.model_validate(data)
    data['visual_traits']['colors'].append('লাল')
    assert profile.name == 'আলো'
    assert profile.visual_traits.colors == ('নীল', 'সাদা')
    assert profile.source == 'user_provided'
    assert CharacterProfileDraft.model_validate_json(profile.model_dump_json()) == profile
    with pytest.raises(ValidationError):
        profile.description = 'Changed'
    with pytest.raises(ValidationError):
        profile.visual_traits.hair = 'Changed'
    with pytest.raises(TypeError):
        profile.visual_traits.colors[0] = 'Changed'


@pytest.mark.parametrize('field', ['face', 'hair', 'eyes', 'outfit', 'colors'])
def test_description_does_not_invent_missing_traits(field):
    data = payload()
    del data['visual_traits'][field]
    with pytest.raises(ValidationError):
        CharacterProfileDraft.model_validate(data)


@pytest.mark.parametrize(
    'field,value',
    [
        ('name', ''),
        ('name', 123),
        ('name', 'x' * 121),
        ('description', '  '),
        ('description', 'x' * 4001),
        ('source', 'model_generated'),
        ('reference_image_paths', ['private.png']),
        ('negative_traits', ['']),
        ('negative_traits', ['x'] * 101),
    ],
)
def test_invalid_or_out_of_scope_fields_rejected(field, value):
    data = payload()
    data[field] = value
    with pytest.raises(ValidationError):
        CharacterProfileDraft.model_validate(data)


@pytest.mark.parametrize(
    'field,value',
    [
        ('hair', 123),
        ('eyes', ' '),
        ('outfit', 'x' * 501),
        ('colors', []),
        ('colors', ['x'] * 21),
        ('colors', [123]),
        ('accessories', ['x'] * 21),
        ('extra', 'x'),
    ],
)
def test_invalid_visual_traits_rejected(field, value):
    data = payload()
    data['visual_traits'][field] = value
    with pytest.raises(ValidationError):
        CharacterProfileDraft.model_validate(data)


def test_optional_traits_and_exact_boundaries():
    data = payload()
    data['name'] = ' ' + 'n' * 120 + ' '
    data['description'] = 'd' * 4000
    data['visual_traits']['hair'] = 'h' * 500
    data['visual_traits']['colors'] = ['c'] * 20
    del data['visual_traits']['accessories']
    del data['negative_traits']
    profile = CharacterProfileDraft.model_validate(data)
    assert profile.visual_traits.accessories == profile.negative_traits == ()
    assert len(profile.name) == 120


def test_unchecked_nested_and_outer_copies_revalidated():
    profile = CharacterProfileDraft.model_validate(payload())
    bad_traits = profile.visual_traits.model_copy(update={'hair': 123})
    with pytest.raises(ValidationError):
        CharacterProfileDraft.model_validate(
            profile.model_copy(update={'visual_traits': bad_traits})
        )
    with pytest.raises(ValidationError):
        CharacterProfileDraft.model_validate(profile.model_copy(update={'name': ''}))
