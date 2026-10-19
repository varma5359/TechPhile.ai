"""Shared choice values for learner preferences and career content targeting."""

LEVEL_BEGINNER = 'beginner'
LEVEL_EXPERIENCED = 'experienced'
LEVEL_CHOICES = [
    (LEVEL_BEGINNER, 'Fresher'),
    (LEVEL_EXPERIENCED, 'Experienced'),
]

EXPERIENCE_FRESHER = 'fresher'
EXPERIENCE_UNDER_1 = 'under_1'
EXPERIENCE_1_2 = '1_2'
EXPERIENCE_3_5 = '3_5'
EXPERIENCE_OVER_5 = 'over_5'
EXPERIENCE_CHOICES = [
    (EXPERIENCE_FRESHER, 'Fresher — no professional experience'),
    (EXPERIENCE_UNDER_1, 'Less than 1 year'),
    (EXPERIENCE_1_2, '1–2 years'),
    (EXPERIENCE_3_5, '3–5 years'),
    (EXPERIENCE_OVER_5, 'More than 5 years'),
]

EXPERIENCE_GENERAL = 'all'
CONTENT_EXPERIENCE_CHOICES = [(EXPERIENCE_GENERAL, 'General — any experience')] + EXPERIENCE_CHOICES
