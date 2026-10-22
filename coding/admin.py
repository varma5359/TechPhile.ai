# from django.contrib import admin
# from .models import Problem, Submission, UserProfile

# @admin.register(Problem)
# class ProblemAdmin(admin.ModelAdmin):
#     list_display = ['title', 'difficulty', 'category', 'created_at']
#     list_filter = ['difficulty', 'category']
#     search_fields = ['title', 'description']
#     prepopulated_fields = {'slug': ('title',)}

# @admin.register(Submission)
# class SubmissionAdmin(admin.ModelAdmin):
#     list_display = ['user', 'problem', 'language', 'status', 'submitted_at']
#     list_filter = ['status', 'language', 'submitted_at']
#     search_fields = ['user__username', 'problem__title']

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ['user', 'total_solved', 'ranking', 'created_at']
#     list_filter = ['created_at']
#     search_fields = ['user__username']




from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Problem, Submission, UserProfile
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q

# Custom filters for better filtering
class DifficultyFilter(admin.SimpleListFilter):
    title = 'Difficulty Level'
    parameter_name = 'difficulty'

    def lookups(self, request, model_admin):
        return Problem.DIFFICULTY_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(difficulty=self.value())
        return queryset

class SubmissionStatusFilter(admin.SimpleListFilter):
    title = 'Submission Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return Submission.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

@admin.register(Problem)
class ProblemAdmin(ModelAdmin):
    list_display = ['title', 'difficulty', 'category', 'created_at', 'submission_count', 'acceptance_rate']
    list_filter = [DifficultyFilter, 'category', 'created_at']
    search_fields = ['title', 'description', 'category']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'category', 'difficulty')
        }),
        ('Problem Details', {
            'fields': ('input_format', 'output_format', 'constraints')
        }),
        ('Test Cases', {
            'fields': ('sample_input', 'sample_output', 'expected_output')
        }),
        ('Limits', {
            'fields': ('time_limit', 'memory_limit')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
        ('Solutions', {
            'fields': [
                'python_solution',
                'javascript_solution',
                'java_solution',
                'cpp_solution',
                'c_solution'
            ],
            'classes': ['collapse']
        }),
    
    )
    
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            total_submissions=Count('submission'),
            accepted_submissions=Count('submission', filter=Q(submission__status='Accepted'))
        )
        return queryset
        
    
    def submission_count(self, obj):
        return obj.total_submissions
    submission_count.short_description = 'Submissions'
    submission_count.admin_order_field = 'total_submissions'
    
    def acceptance_rate(self, obj):
        if obj.total_submissions > 0:
            rate = (obj.accepted_submissions / obj.total_submissions) * 100
            return f"{rate:.1f}%"
        return "N/A"
    acceptance_rate.short_description = 'Acceptance Rate'

@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ['id', 'user_link', 'problem_link', 'language', 'status_badge', 'execution_time', 'memory_used', 'submitted_at']
    list_filter = [SubmissionStatusFilter, 'language', 'submitted_at']
    search_fields = ['user__username', 'problem__title', 'code']
    list_select_related = ['user', 'problem']
    readonly_fields = ['submitted_at']
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'problem')
        }),
        ('Submission Details', {
            'fields': ('code', 'language', 'status')
        }),
        ('Execution Metrics', {
            'fields': ('execution_time', 'memory_used')
        }),
        ('Metadata', {
            'fields': ('submitted_at',)
        }),
    )
    
    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def problem_link(self, obj):
        url = reverse("admin:judge_problem_change", args=[obj.problem.id])
        return format_html('<a href="{}">{}</a>', url, obj.problem.title)
    problem_link.short_description = 'Problem'
    problem_link.admin_order_field = 'problem__title'
    
    def status_badge(self, obj):
        color_map = {
            'Accepted': 'green',
            'Pending': 'orange',
            'Wrong Answer': 'red',
            'Runtime Error': 'purple',
            'Compilation Error': 'darkred',
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 5px; border-radius: 3px;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ['user_link', 'avatar_thumbnail', 'total_solved', 'easy_solved', 'medium_solved', 'hard_solved', 'ranking']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'avatar_preview']
    list_per_page = 20
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'avatar', 'avatar_preview')
        }),
        ('Problem Stats', {
            'fields': ('total_solved', 'easy_solved', 'medium_solved', 'hard_solved')
        }),
        ('Ranking', {
            'fields': ('ranking',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )
    
    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def avatar_thumbnail(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="30" height="30" style="border-radius: 50%;" />', obj.avatar.url)
        return "No Avatar"
    avatar_thumbnail.short_description = 'Avatar'
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="150" height="150" style="border-radius: 50%;" />', obj.avatar.url)
        return "No Avatar"
    avatar_preview.short_description = 'Avatar Preview'
