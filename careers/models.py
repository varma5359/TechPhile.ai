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
        ordering = ['role', 'day_number']
        constraints = [
            models.UniqueConstraint(fields=['role', 'day_number'], name='unique_day_per_role'),
        ]

    def __str__(self):
        return f'{self.role.title} - Day {self.day_number}: {self.title}'

    def get_absolute_url(self):
        return reverse('careers:day_detail', args=[self.role.slug, self.day_number])

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


class MilestoneExam(models.Model):
    """A five-day milestone assessment for a role.

    It is separate from regular mock exams and covers ``start_day`` to
    ``end_day`` of the role's learning plan.
    """

    role = models.ForeignKey(CareerRole, on_delete=models.CASCADE, related_name='milestones')
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
        ordering = ['role', 'number']
        constraints = [
            models.UniqueConstraint(fields=['role', 'number'], name='unique_milestone_per_role'),
        ]

    def __str__(self):
        return f'{self.role.title} - Milestone {self.number} (days {self.start_day}-{self.end_day})'

    def clean(self):
        if self.start_day and self.end_day and self.end_day < self.start_day:
            raise ValidationError('End day cannot be before start day.')

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f'Milestone Exam {self.number}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('careers:milestone_detail', args=[self.role.slug, self.number])

    def covered_days(self):
        return self.role.days.filter(
            is_published=True, day_number__gte=self.start_day, day_number__lte=self.end_day)

    def get_questions(self):
        """Explicitly assigned questions, else the published pool for the day range."""
        assigned = [
            mq.question for mq in self.assigned_questions.select_related(
                'question__day', 'question__skill').prefetch_related('question__options')
            if mq.question.is_published
        ]
        if assigned:
            return assigned
        pool = ScenarioQuestion.objects.filter(
            is_published=True, day__role=self.role, day__is_published=True,
            day__day_number__gte=self.start_day, day__day_number__lte=self.end_day,
        ).select_related('day', 'skill').prefetch_related('options')
        return list(pool[:self.question_count])


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
        if self.milestone_id and self.question_id and self.question.day.role_id != self.milestone.role_id:
            raise ValidationError('The question belongs to a different role.')


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
