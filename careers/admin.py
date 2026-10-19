from django.contrib import admin

from .models import (
    CareerRole, DayAttempt, DayProgress, LearningDay, MilestoneAttempt, MilestoneExam,
    MilestoneQuestion, QuestionOption, ScenarioQuestion, Skill,
)


class LearningDayInline(admin.TabularInline):
    model = LearningDay
    extra = 0
    fields = ('day_number', 'title', 'is_published')
    show_change_link = True


class MilestoneInline(admin.TabularInline):
    model = MilestoneExam
    extra = 0
    fields = ('number', 'title', 'start_day', 'end_day', 'question_count', 'is_published')
    show_change_link = True


@admin.register(CareerRole)
class CareerRoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'duration_days', 'unlock_policy', 'is_published', 'display_order')
    list_filter = ('is_published', 'unlock_policy')
    list_editable = ('is_published', 'display_order')
    search_fields = ('title', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LearningDayInline, MilestoneInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4


@admin.register(LearningDay)
class LearningDayAdmin(admin.ModelAdmin):
    list_display = ('role', 'day_number', 'title', 'is_published')
    list_filter = ('role', 'is_published')
    search_fields = ('title', 'topics')
    ordering = ('role', 'day_number')


@admin.register(ScenarioQuestion)
class ScenarioQuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'day', 'skill', 'difficulty', 'question_type', 'is_published')
    list_filter = ('day__role', 'difficulty', 'question_type', 'skill', 'is_published')
    search_fields = ('text', 'scenario', 'topic')
    autocomplete_fields = ('skill',)
    list_select_related = ('day__role', 'skill')
    inlines = [QuestionOptionInline]


class MilestoneQuestionInline(admin.TabularInline):
    model = MilestoneQuestion
    extra = 0
    raw_id_fields = ('question',)


@admin.register(MilestoneExam)
class MilestoneExamAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'question_count', 'time_limit_minutes', 'is_published')
    list_filter = ('role', 'is_published')
    inlines = [MilestoneQuestionInline]


class ReadOnlyAdmin(admin.ModelAdmin):
    """Student progress and attempts are reviewed here, never edited."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DayProgress)
class DayProgressAdmin(ReadOnlyAdmin):
    list_display = ('user', 'day', 'status', 'best_score', 'last_score', 'attempts_count', 'last_attempt_at')
    list_filter = ('status', 'day__role')
    search_fields = ('user__username',)
    list_select_related = ('user', 'day__role')


@admin.register(DayAttempt)
class DayAttemptAdmin(ReadOnlyAdmin):
    list_display = ('user', 'day', 'score_percent', 'submitted_at')
    list_filter = ('day__role',)
    search_fields = ('user__username',)
    list_select_related = ('user', 'day__role')


@admin.register(MilestoneAttempt)
class MilestoneAttemptAdmin(ReadOnlyAdmin):
    list_display = ('user', 'milestone', 'score_percent', 'submitted_at')
    list_filter = ('milestone__role',)
    search_fields = ('user__username',)
    list_select_related = ('user', 'milestone__role')
