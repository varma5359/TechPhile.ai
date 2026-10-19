"""Resolve a learner's role, experience, and learning-path curriculum.

Fallback policy: for each day number or milestone number, use the exact
experience-band record when published. Otherwise use the explicitly general
(``all``) record for the same role and learning path. Never cross role/path
boundaries, and never merge both variants for one sequence number.
"""
from dataclasses import dataclass
from django.db.models import Count, Q

from .choices import (
    EXPERIENCE_CHOICES, EXPERIENCE_FRESHER, EXPERIENCE_GENERAL,
    EXPERIENCE_OVER_5, EXPERIENCE_1_2, EXPERIENCE_3_5, EXPERIENCE_UNDER_1,
    LEVEL_BEGINNER, LEVEL_CHOICES, LEVEL_EXPERIENCED,
)
from .models import LearningDay, MilestoneExam


RECOMMENDED_PATH_BY_EXPERIENCE = {
    EXPERIENCE_FRESHER: LEVEL_BEGINNER,
    EXPERIENCE_UNDER_1: LEVEL_BEGINNER,
    EXPERIENCE_1_2: LEVEL_EXPERIENCED,
    EXPERIENCE_3_5: LEVEL_EXPERIENCED,
    EXPERIENCE_OVER_5: LEVEL_EXPERIENCED,
}


def recommend_learning_path(experience_band):
    """Recommend a path without changing or restricting a learner's choice."""
    if not experience_band or experience_band == EXPERIENCE_GENERAL:
        return LEVEL_BEGINNER
    if experience_band not in RECOMMENDED_PATH_BY_EXPERIENCE:
        raise ValueError('Unknown experience band.')
    return RECOMMENDED_PATH_BY_EXPERIENCE[experience_band]


def effective_learning_path(experience_band, selected_path=''):
    """Return an explicit valid path, otherwise the non-persisted recommendation."""
    valid_paths = dict(LEVEL_CHOICES)
    if selected_path:
        if selected_path not in valid_paths:
            raise ValueError('Unknown learning path.')
        return selected_path
    return recommend_learning_path(experience_band)


def _validate_selection(experience_band, learning_path):
    valid_bands = dict(EXPERIENCE_CHOICES)
    if experience_band and experience_band != EXPERIENCE_GENERAL and experience_band not in valid_bands:
        raise ValueError('Unknown experience band.')
    if learning_path not in dict(LEVEL_CHOICES):
        raise ValueError('Unknown learning path.')


def _prefer_exact(queryset, sequence_field, experience_band):
    """Choose one record per sequence number, exact band before general."""
    candidates = list(queryset)
    if experience_band != EXPERIENCE_GENERAL:
        candidates.sort(key=lambda item: item.experience_band != experience_band)
    selected = {}
    for item in candidates:
        selected.setdefault(getattr(item, sequence_field), item)
    return [selected[key] for key in sorted(selected)]


def _experience_bands(experience_band):
    target = experience_band or EXPERIENCE_GENERAL
    return target, ([EXPERIENCE_GENERAL] if target == EXPERIENCE_GENERAL
                    else [target, EXPERIENCE_GENERAL])


def select_learning_days(role, learning_path, experience_band=''):
    """Select one published day per sequence number, with exact-band priority."""
    _validate_selection(experience_band, learning_path)
    if role is None or not role.is_published:
        return []
    target, bands = _experience_bands(experience_band)
    queryset = LearningDay.objects.filter(
        role=role, level=learning_path, experience_band__in=bands, is_published=True,
    ).annotate(question_total=Count('questions', filter=Q(questions__is_published=True)))
    return _prefer_exact(queryset.order_by('day_number'), 'day_number', target)


def select_milestones(role, learning_path, experience_band=''):
    """Select one published milestone per number using the same fallback rules."""
    _validate_selection(experience_band, learning_path)
    if role is None or not role.is_published:
        return []
    target, bands = _experience_bands(experience_band)
    queryset = MilestoneExam.objects.filter(
        role=role, level=learning_path, experience_band__in=bands, is_published=True,
    ).select_related('role').order_by('number')
    return _prefer_exact(queryset, 'number', target)


@dataclass(frozen=True)
class ResolvedLearningPlan:
    role: object
    experience_band: str
    learning_path: str
    recommended_path: str
    days: list
    milestones: list


def resolve_learning_plan(role, experience_band='', selected_path=''):
    """Resolve ordered day and milestone content for one learner selection."""
    path = effective_learning_path(experience_band, selected_path)
    _validate_selection(experience_band, path)
    return ResolvedLearningPlan(
        role=role,
        experience_band=experience_band,
        learning_path=path,
        recommended_path=recommend_learning_path(experience_band),
        days=select_learning_days(role, path, experience_band),
        milestones=select_milestones(role, path, experience_band),
    )


def resolve_profile_learning_plan(profile):
    """Resolve a saved profile without persisting or overriding recommendations."""
    return resolve_learning_plan(
        role=profile.career_role,
        experience_band=profile.experience_band,
        selected_path=profile.learning_path,
    ) if profile.career_role_id else None


def questions_for_day(day):
    """Questions are inherited from the already-selected role/path/band day."""
    if not day.is_published or not day.role.is_published:
        return []
    return list(day.questions.filter(is_published=True).select_related('skill').prefetch_related('options'))


def questions_for_milestone(milestone):
    """Use the milestone's own exact/general fallback and question validation."""
    if not milestone.is_published or not milestone.role.is_published:
        return []
    return milestone.get_questions()
