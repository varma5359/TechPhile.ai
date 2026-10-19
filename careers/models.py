"""Data model for the role-based career preparation feature.

These tables are intentionally separate from the regular mock exam tables
(``exams.Exam``, ``exams.Question``, ``exams.ExamAttempt`` ...), which are not
touched by this app.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

DAYS_PER_MILESTONE = 5
MILESTONE_PASS_PERCENT = 75
from .choices import (
    CONTENT_EXPERIENCE_CHOICES, EXPERIENCE_GENERAL,
    LEVEL_BEGINNER, LEVEL_EXPERIENCED, LEVEL_CHOICES,
)


def split_lines(text):
    """Return the non-empty, stripped lines of a multi-line text field."""
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


class CareerRole(models.Model):
    """A career track (for example Data Analytics) with its own syllabus."""

    UNLOCK_OPEN = 'open'
    UNLOCK_SEQUENTIAL = 'sequential'
    UNLOCK_MIN_SCORE = 'sequential_min_score'
    UNLOCK_CHOICES = [
        (UNLOCK_OPEN, 'Open - any day, any order'),
        (UNLOCK_SEQUENTIAL, 'Sequential - submit a day to unlock the next'),
        (UNLOCK_MIN_SCORE, 'Sequential with minimum score'),
    ]

    title = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    summary = models.TextField(help_text='What the role involves.')
    objectives = models.TextField(blank=True, help_text='Career objectives, one per line.')
    responsibilities = models.TextField(blank=True, help_text='Typical responsibilities, one per line.')
    expected_skills = models.TextField(blank=True, help_text='Expected skills, one per line.')
    syllabus = models.TextField(blank=True, help_text='High level syllabus overview, one item per line.')
    duration_days = models.PositiveIntegerField(
        default=30, validators=[MinValueValidator(1)],
        help_text='Planned preparation duration in days.')
    unlock_policy = models.CharField(max_length=24, choices=UNLOCK_CHOICES, default=UNLOCK_SEQUENTIAL)
    pass_percent = models.PositiveIntegerField(
        default=60, validators=[MaxValueValidator(100)],
        help_text='Score at or above which a day/milestone counts as solid. Below it, revision is recommended.')
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('careers:role_detail', args=[self.slug])

    @property
    def objective_list(self):
        return split_lines(self.objectives)

    @property
    def responsibility_list(self):
        return split_lines(self.responsibilities)

    @property
    def skill_list(self):
        return split_lines(self.expected_skills)

    @property
    def syllabus_list(self):
        return split_lines(self.syllabus)


class Skill(models.Model):
    """A skill tag used to find strengths and weak areas."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LearningDay(models.Model):
    """One day of a role's ordered learning plan."""

    role = models.ForeignKey(CareerRole, on_delete=models.CASCADE, related_name='days')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_BEGINNER)
    experience_band = models.CharField(
        max_length=20, choices=CONTENT_EXPERIENCE_CHOICES, default=EXPERIENCE_GENERAL,
        help_text='General content is used only when no exact-band content exists for this day.',
    )
    day_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    title = models.CharField(max_length=200)
    objectives = models.TextField(blank=True, help_text='Learning objectives, one per line.')
    topics = models.TextField(blank=True, help_text='Topics to prepare, one per line.')
    lesson_intro = models.TextField(blank=True, help_text='Short introduction shown under the day title (Markdown).')
    difficulty_level = models.CharField(max_length=40, blank=True, help_text='For example Beginner or Intermediate.')
    estimated_minutes = models.PositiveIntegerField(null=True, blank=True, help_text='Estimated learning time.')
    lesson_scenario = models.TextField(
        blank=True, help_text='Real-world scenario that opens the lesson (Markdown). Shown in a highlighted block.')
    lesson_body = models.TextField(
        blank=True, help_text='Main lesson (Markdown): ## headings, lists, tables, code blocks, admonitions '
                              '(!!! tip / note / warning / example) and ```flow / ```tree diagram blocks.')
    lesson_revision = models.TextField(blank=True, help_text='Quick revision notes shown before the questions (Markdown).')
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['role', 'level', 'experience_band', 'day_number']
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'level', 'experience_band', 'day_number'],
                name='unique_day_role_path_experience_number',
            ),
        ]

    def __str__(self):
        return (f'{self.role.title} - {self.get_level_display()} '
                f'({self.get_experience_band_display()}) Day {self.day_number}: {self.title}')

    def get_absolute_url(self):
        if self.level == LEVEL_BEGINNER:
            return reverse('careers:day_detail', args=[self.role.slug, self.day_number])
        return reverse('careers:level_day_detail', args=[self.role.slug, self.level, self.day_number])

    @property
    def objective_list(self):
        return split_lines(self.objectives)

    @property
    def topic_list(self):
        return split_lines(self.topics)

    @property
    def has_lesson(self):
        """True when an administrator has written any lesson content for this day."""
        return any((self.lesson_intro, self.lesson_scenario, self.lesson_body, self.lesson_revision))

    @property
    def milestone_number(self):
        """Number of the five-day block this day belongs to."""
        return (self.day_number - 1) // DAYS_PER_MILESTONE + 1


class ScenarioQuestion(models.Model):
    """A scenario based interview question attached to a learning day."""

    DIFFICULTY_CHOICES = [
        ('fresher', 'Fresher'),
        ('experienced', 'Experienced'),
        ('advanced', 'Advanced'),
        ('production', 'Production'),
    ]
    TYPE_CHOICES = [
        ('mcq', 'Multiple choice'),
        ('tf', 'True / False'),
    ]

    day = models.ForeignKey(LearningDay, on_delete=models.CASCADE, related_name='questions')
    skill = models.ForeignKey(Skill, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')
    topic = models.CharField(max_length=150, blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='fresher')
    question_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='mcq')
    scenario = models.TextField(blank=True, help_text='Business or technical context for the question.')
    text = models.TextField(help_text='The question itself.')
    explanation = models.TextField(blank=True, help_text='Shown after the student submits.')
    takeaway = models.CharField(max_length=300, blank=True, help_text='One-line practical takeaway shown after submitting.')
    marks = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['day__day_number', 'order', 'id']

    def __str__(self):
        return f'Day {self.day.day_number} Q{self.order}: {self.text[:60]}'

    @property
    def role(self):
        return self.day.role


class QuestionOption(models.Model):
    """An answer option. ``is_correct`` is evaluated on the server only."""

    question = models.ForeignKey(ScenarioQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    explanation = models.TextField(blank=True, help_text='Why this option is right or wrong. Shown after submitting.')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.text[:60]


class DayAttempt(models.Model):
    """A student's submitted answers for one learning day."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_day_attempts')
    day = models.ForeignKey(LearningDay, on_delete=models.CASCADE, related_name='attempts')
    submitted_at = models.DateTimeField(auto_now_add=True)
    correct_marks = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    score_percent = models.FloatField(default=0)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [models.Index(fields=['user', 'day', '-submitted_at'])]

    def __str__(self):
        return f'{self.user} - {self.day} ({self.score_percent:.0f}%)'


class DayAnswer(models.Model):
    """One answered question inside a day attempt."""

    attempt = models.ForeignKey(DayAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ScenarioQuestion, on_delete=models.CASCADE, related_name='+')
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='unique_answer_per_day_attempt'),
        ]


class DayProgress(models.Model):
    """Persistent per-student status for a learning day."""

    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    REVISION = 'revision_recommended'
    STATUS_CHOICES = [
        (IN_PROGRESS, 'In progress'),
        (COMPLETED, 'Completed'),
        (REVISION, 'Revision recommended'),
    ]
    # A day with no row is "not started".
    SUBMITTED_STATUSES = (COMPLETED, REVISION)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_day_progress')
    day = models.ForeignKey(LearningDay, on_delete=models.CASCADE, related_name='progress')
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=IN_PROGRESS)
    best_score = models.FloatField(null=True, blank=True)
    last_score = models.FloatField(null=True, blank=True)
    attempts_count = models.PositiveIntegerField(default=0)
    notes_completed = models.BooleanField(default=False)
    notes_completed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'day'], name='unique_progress_per_user_day'),
        ]
        indexes = [models.Index(fields=['user', 'status'])]

    def __str__(self):
        return f'{self.user} - {self.day} [{self.status}]'

    @property
    def is_submitted(self):
        return self.status in self.SUBMITTED_STATUSES

    @property
    def is_completed(self):
        """A day is complete when notes are marked complete and questions are submitted."""
        return bool(self.notes_completed and self.is_submitted)


class MilestoneExam(models.Model):
    """A five-day milestone assessment for a role.

    It is separate from regular mock exams and covers ``start_day`` to
    ``end_day`` of the role's learning plan.
    """

    role = models.ForeignKey(CareerRole, on_delete=models.CASCADE, related_name='milestones')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_BEGINNER)
    experience_band = models.CharField(
        max_length=20, choices=CONTENT_EXPERIENCE_CHOICES, default=EXPERIENCE_GENERAL,
        help_text='General milestone content is the fallback when no exact-band milestone exists.',
    )
    number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    title = models.CharField(max_length=200, blank=True)
    start_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    end_day = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    question_count = models.PositiveIntegerField(
        default=10, validators=[MinValueValidator(1)],
        help_text='Maximum questions used when no questions are assigned explicitly.')
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['role', 'level', 'experience_band', 'number']
        constraints = [
            models.UniqueConstraint(
                fields=['role', 'level', 'experience_band', 'number'],
                name='unique_milestone_role_path_experience_number',
            ),
        ]

    def __str__(self):
        return (f'{self.role.title} - {self.get_level_display()} '
                f'({self.get_experience_band_display()}) Milestone {self.number} '
                f'(days {self.start_day}-{self.end_day})')

    def clean(self):
        if self.start_day and self.end_day and self.end_day < self.start_day:
            raise ValidationError('End day cannot be before start day.')

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f'Milestone Exam {self.number}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.level == LEVEL_BEGINNER:
            return reverse('careers:milestone_detail', args=[self.role.slug, self.number])
        return reverse('careers:level_milestone_detail', args=[self.role.slug, self.level, self.number])

    @property
    def pass_percent(self):
        return MILESTONE_PASS_PERCENT

    def best_score_for_user(self, user):
        scores = self.attempts.filter(user=user).values_list('score_percent', flat=True)
        return max(scores) if scores else None

    def is_passed_by_user(self, user):
        best = self.best_score_for_user(user)
        return best is not None and best >= MILESTONE_PASS_PERCENT

    def covered_days(self, experience_band=None):
        target = experience_band or self.experience_band
        bands = [EXPERIENCE_GENERAL] if target == EXPERIENCE_GENERAL else [target, EXPERIENCE_GENERAL]
        days = list(self.role.days.filter(
            level=self.level, experience_band__in=bands, is_published=True,
            day_number__gte=self.start_day, day_number__lte=self.end_day,
        ).order_by('day_number'))
        selected = {}
        for day in sorted(days, key=lambda item: item.experience_band != target):
            selected.setdefault(day.day_number, day)
        return [selected[number] for number in sorted(selected)]

    def get_questions(self, experience_band=None):
        """Explicitly assigned questions, else the published pool for the day range."""
        target = experience_band or self.experience_band
        bands = {EXPERIENCE_GENERAL} if target == EXPERIENCE_GENERAL else {target, EXPERIENCE_GENERAL}
        assigned_query = self.assigned_questions.select_related(
            'question__day', 'question__skill').prefetch_related('question__options')
        assigned = [
            mq.question for mq in assigned_query
            if mq.question.is_published and mq.question.day.is_published
            and mq.question.day.role_id == self.role_id
            and mq.question.day.level == self.level
            and mq.question.day.experience_band in bands
            and self.start_day <= mq.question.day.day_number <= self.end_day
        ]
        if assigned:
            return self._prefer_exact_questions_per_day(assigned, target)
        pool = ScenarioQuestion.objects.filter(
            is_published=True, day__role=self.role, day__level=self.level, day__is_published=True,
            day__day_number__gte=self.start_day, day__day_number__lte=self.end_day,
            day__experience_band__in=bands,
        ).select_related('day', 'skill').prefetch_related('options').order_by('day__day_number', 'pk')
        selected = self._prefer_exact_questions_per_day(list(pool), target)
        return selected[:self.question_count]

    @staticmethod
    def _prefer_exact_questions_per_day(questions, target):
        """Prefer exact-band questions per day, falling back for uncovered days."""
        if target == EXPERIENCE_GENERAL:
            return questions
        grouped = {}
        for question in questions:
            grouped.setdefault(question.day.day_number, {'exact': [], 'general': []})[
                'exact' if question.day.experience_band == target else 'general'
            ].append(question)
        result = []
        for day_number in sorted(grouped):
            bucket = grouped[day_number]
            result.extend(bucket['exact'] or bucket['general'])
        return result


class MilestoneQuestion(models.Model):
    """Explicit assignment of a question to a milestone exam."""

    milestone = models.ForeignKey(MilestoneExam, on_delete=models.CASCADE, related_name='assigned_questions')
    question = models.ForeignKey(ScenarioQuestion, on_delete=models.CASCADE, related_name='milestone_links')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['milestone', 'question'], name='unique_question_per_milestone'),
        ]

    def clean(self):
        if self.milestone_id and self.question_id:
            if self.question.day.role_id != self.milestone.role_id:
                raise ValidationError('The question belongs to a different role.')
            if self.question.day.level != self.milestone.level:
                raise ValidationError('The question belongs to a different learning level.')
            if not self.milestone.start_day <= self.question.day.day_number <= self.milestone.end_day:
                raise ValidationError('The question is outside this milestone day range.')
            if self.question.day.experience_band not in {
                self.milestone.experience_band, EXPERIENCE_GENERAL,
            }:
                raise ValidationError('The question targets a different experience band.')


class MilestoneAttempt(models.Model):
    """A student's submitted milestone exam."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_milestone_attempts')
    milestone = models.ForeignKey(MilestoneExam, on_delete=models.CASCADE, related_name='attempts')
    submitted_at = models.DateTimeField(auto_now_add=True)
    correct_marks = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    score_percent = models.FloatField(default=0)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [models.Index(fields=['user', 'milestone', '-submitted_at'])]

    def __str__(self):
        return f'{self.user} - {self.milestone} ({self.score_percent:.0f}%)'


class MilestoneAnswer(models.Model):
    """One answered question inside a milestone attempt."""

    attempt = models.ForeignKey(MilestoneAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ScenarioQuestion, on_delete=models.CASCADE, related_name='+')
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='unique_answer_per_milestone_attempt'),
        ]
