from django.contrib import admin
from django import forms
from django.db.models import Count, Q
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    CareerRole, DayAttempt, DayProgress, LearningDay, MilestoneAttempt, MilestoneExam,
    MilestoneQuestion, QuestionOption, ScenarioQuestion, Skill,
)
from .choices import EXPERIENCE_GENERAL, LEVEL_BEGINNER


class ExperienceTargetAdminMixin:
    """Keep old admin submissions valid while defaulting new content to General."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['experience_band'].required = False
        self.fields['experience_band'].initial = EXPERIENCE_GENERAL
        self.fields['level'].required = False
        self.fields['level'].initial = LEVEL_BEGINNER

    def clean_experience_band(self):
        return self.cleaned_data.get('experience_band') or EXPERIENCE_GENERAL

    def clean_level(self):
        return self.cleaned_data.get('level') or LEVEL_BEGINNER


class LearningDayAdminForm(ExperienceTargetAdminMixin, forms.ModelForm):
    class Meta:
        model = LearningDay
        fields = '__all__'


class MilestoneExamAdminForm(ExperienceTargetAdminMixin, forms.ModelForm):
    class Meta:
        model = MilestoneExam
        fields = '__all__'


class LearningDayInline(TabularInline):
    model = LearningDay
    form = LearningDayAdminForm
    extra = 0
    fields = ('level', 'experience_band', 'day_number', 'title', 'is_published')
    show_change_link = True


class MilestoneInline(TabularInline):
    model = MilestoneExam
    form = MilestoneExamAdminForm
    extra = 0
    fields = ('level', 'experience_band', 'number', 'title', 'start_day', 'end_day', 'question_count', 'is_published')
    show_change_link = True


@admin.register(CareerRole)
class CareerRoleAdmin(ModelAdmin):
    list_display = (
        'title', 'duration_days', 'published_day_count', 'published_question_count',
        'unlock_policy', 'is_published', 'display_order',
    )
    list_filter = ('is_published', 'unlock_policy')
    list_editable = ('is_published', 'display_order')
    search_fields = ('title', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LearningDayInline, MilestoneInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            admin_published_day_count=Count(
                'days', filter=Q(is_published=True, days__is_published=True), distinct=True,
            ),
            admin_published_question_count=Count(
                'days__questions',
                filter=Q(
                    is_published=True,
                    days__is_published=True,
                    days__questions__is_published=True,
                ),
                distinct=True,
            ),
        )

    @admin.display(description='Published days', ordering='admin_published_day_count')
    def published_day_count(self, obj):
        return obj.admin_published_day_count

    @admin.display(description='Published questions', ordering='admin_published_question_count')
    def published_question_count(self, obj):
        return obj.admin_published_question_count


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ('name', 'published_question_count')
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            admin_published_question_count=Count(
                'questions',
                filter=Q(
                    questions__is_published=True,
                    questions__day__is_published=True,
                    questions__day__role__is_published=True,
                ),
            ),
        )

    @admin.display(description='Published questions', ordering='admin_published_question_count')
    def published_question_count(self, obj):
        return obj.admin_published_question_count


class QuestionOptionInline(TabularInline):
    model = QuestionOption
    extra = 4


@admin.register(LearningDay)
class LearningDayAdmin(ModelAdmin):
    form = LearningDayAdminForm
    list_display = (
        'role', 'level', 'experience_band', 'day_number', 'title', 'published_question_count',
        'difficulty_level', 'estimated_minutes', 'is_published',
    )
    list_filter = ('role', 'role__is_published', 'level', 'experience_band', 'is_published', 'difficulty_level')
    search_fields = ('title', 'topics', 'lesson_body')
    ordering = ('role', 'level', 'experience_band', 'day_number')
    list_select_related = ('role',)
    fieldsets = (
        ('Day identity', {
            'fields': ('role', 'level', 'experience_band', 'day_number', 'title', 'is_published'),
        }),
        ('Metadata', {
            'fields': ('difficulty_level', 'estimated_minutes'),
            'description': (
                'Shown in the lesson header as coloured badges. '
                '"Difficulty level" is free text, e.g. <em>Beginner</em> or <em>Intermediate</em>.'
            ),
        }),
        ('Objectives & topics', {
            'fields': ('objectives', 'topics'),
            'description': (
                'Enter one item per line. '
                'Objectives appear as a numbered checklist; topics populate the "Topics to prepare" panel.'
            ),
        }),
        ('Lesson notes — Introduction', {
            'fields': ('lesson_intro',),
            'description': (
                'A short paragraph (plain text) shown directly under the day title before any sections. '
                'Keep it to 2–3 sentences.'
            ),
        }),
        ('Lesson notes — Real-world scenario', {
            'fields': ('lesson_scenario',),
            'description': (
                'Markdown. Rendered in a highlighted aside box. '
                'Opens the lesson with a concrete business situation the student will resolve by the end.'
            ),
        }),
        ('Lesson notes — Main tutorial body', {
            'fields': ('lesson_body',),
            'classes': ('wide',),
            'description': (
                '<strong>Primary content area — write the full tutorial here.</strong><br>'
                'Use standard Markdown: <code>## Heading</code>, <code>### Sub-heading</code>, '
                '<code>**bold**</code>, <code>- lists</code>, fenced code blocks, '
                'pipe tables, and admonition blocks (<code>!!! note</code>, '
                '<code>!!! tip</code>, <code>!!! warning</code>, <code>!!! example</code>).<br>'
                'Custom diagram blocks are also supported:<br>'
                '<code>```flow</code> — vertical process flow diagram<br>'
                '<code>```tree</code> — decision-tree diagram'
            ),
        }),
        ('Lesson notes — Quick revision', {
            'fields': ('lesson_revision',),
            'description': (
                'Markdown. A summary section shown after the main body and before the practice questions. '
                'Use bullet points or a short table of key takeaways.'
            ),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            admin_published_question_count=Count(
                'questions',
                filter=Q(is_published=True, role__is_published=True, questions__is_published=True),
                distinct=True,
            ),
        )

    @admin.display(description='Published questions', ordering='admin_published_question_count')
    def published_question_count(self, obj):
        return obj.admin_published_question_count


@admin.register(ScenarioQuestion)
class ScenarioQuestionAdmin(ModelAdmin):
    list_display = ('__str__', 'day', 'skill', 'difficulty', 'question_type', 'is_published')
    list_filter = (
        'day__role', 'day__role__is_published', 'day__is_published', 'day__level',
        'day__experience_band', 'difficulty', 'question_type', 'skill', 'is_published',
    )
    search_fields = ('text', 'scenario', 'topic')
    autocomplete_fields = ('skill',)
    list_select_related = ('day__role', 'skill')
    inlines = [QuestionOptionInline]


class MilestoneQuestionInline(TabularInline):
    model = MilestoneQuestion
    extra = 0
    raw_id_fields = ('question',)

    class Form(forms.ModelForm):
        class Meta:
            model = MilestoneQuestion
            fields = '__all__'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            milestone = getattr(self.instance, 'milestone', None)
            if milestone and milestone.role_id:
                self.fields['question'].queryset = ScenarioQuestion.objects.filter(
                    day__role=milestone.role, day__level=milestone.level,
                    day__experience_band__in=[milestone.experience_band, EXPERIENCE_GENERAL])

    form = Form


@admin.register(MilestoneExam)
class MilestoneExamAdmin(ModelAdmin):
    form = MilestoneExamAdminForm
    list_display = ('__str__', 'role', 'level', 'experience_band', 'number', 'question_count', 'time_limit_minutes', 'is_published')
    list_filter = ('role', 'level', 'experience_band', 'is_published')
    search_fields = ('title', 'role__title')
    list_select_related = ('role',)
    inlines = [MilestoneQuestionInline]


class ReadOnlyAdmin(ModelAdmin):
    """Student progress and attempts are reviewed here, never edited."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DayProgress)
class DayProgressAdmin(ReadOnlyAdmin):
    list_display = ('user', 'day', 'notes_completed', 'status', 'best_score', 'last_score', 'attempts_count', 'notes_completed_at', 'last_attempt_at')
    list_filter = ('notes_completed', 'status', 'day__role')
    search_fields = ('user__username',)
    list_select_related = ('user', 'day__role')
    date_hierarchy = 'last_attempt_at'


@admin.register(DayAttempt)
class DayAttemptAdmin(ReadOnlyAdmin):
    list_display = ('user', 'day', 'score_percent', 'submitted_at')
    list_filter = ('day__role', 'submitted_at')
    search_fields = ('user__username',)
    list_select_related = ('user', 'day__role')
    date_hierarchy = 'submitted_at'


@admin.register(MilestoneAttempt)
class MilestoneAttemptAdmin(ReadOnlyAdmin):
    list_display = ('user', 'milestone', 'score_percent', 'submitted_at')
    list_filter = ('milestone__role', 'submitted_at')
    search_fields = ('user__username',)
    list_select_related = ('user', 'milestone__role')
    date_hierarchy = 'submitted_at'
