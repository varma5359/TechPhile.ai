from django.contrib import admin
from .models import Topic, Problem, Dataset, Submissions, UserProgress, Leaderboard


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'created_at']
    list_editable = ['sort_order']
    ordering = ['sort_order', 'name']


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['title', 'topic', 'difficulty', 'points', 'is_active', 'created_at']
    list_filter = ['topic', 'difficulty', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['difficulty', 'points', 'is_active']
    ordering = ['topic', 'sort_order', 'title']


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'filename', 'file_size', 'is_public', 'uploaded_by', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'filename']
    readonly_fields = ['file_size', 'mime_type']


@admin.register(Submissions)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'status', 'score', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['user__username', 'problem__title']
    readonly_fields = ['submitted_at']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'status', 'best_score', 'attempts', 'completed_at']
    list_filter = ['status', 'completed_at']
    search_fields = ['user__username', 'problem__title']


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_score', 'problems_solved', 'rank', 'last_updated']
    ordering = ['rank']
    readonly_fields = ['last_updated']