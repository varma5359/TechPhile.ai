from django.contrib.auth.models import User  # Ensure this is imported correctly
from . import views
from django.contrib import admin
from .models import Category, Exam, InterviewFeedback, Question, Answer, ExamAttempt, UserAnswer, Applicant, Interviewer

from django.contrib import admin
from .models import Category, Exam, Question, Answer, ExamAttempt, UserAnswer
from django.utils.html import format_html

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    fields = ('answer_text', 'is_correct')
    ordering = ('id',)

class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ('order', 'set_number', 'category', 'title', 'level_display', 
                    'question_type_display', 'question_text_short', 'marks')
    list_display_links = ('title',)  # Make title clickable instead of order
    list_filter = ('category', 'exam', 'level', 'set_number', 'question_type')
    search_fields = ('question_text', 'title')
    list_editable = ('order', 'set_number', 'marks')  # Now all these are in list_display
    ordering = ('order', 'set_number')
    fieldsets = (
        ('Basic Info', {
            'fields': ('category', 'exam', 'title', 'order', 'set_number')
        }),
        ('Question Details', {
            'fields': ('question_text', 'question_type', 'level', 'marks', 'explanation')
        }),
    )

    def level_display(self, obj):
        return obj.get_level_display()
    level_display.short_description = 'Level'
    level_display.admin_order_field = 'level'

    def question_type_display(self, obj):
        return obj.get_question_type_display()
    question_type_display.short_description = 'Type'
    question_type_display.admin_order_field = 'question_type'

    def question_text_short(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    question_text_short.short_description = 'Question'
    
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_popular', 'is_new', 'question_count')
    list_filter = ('category', 'is_popular', 'is_new')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ()
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'question_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    readonly_fields = ('question', 'selected_answer', 'is_correct')
    extra = 0
    fields = ('question', 'selected_answer', 'is_correct')
    
    def has_add_permission(self, request, obj=None):
        return False

class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'started_at', 'completed_at', 'score', 'duration')
    list_filter = ('exam', 'user')
    inlines = [UserAnswerInline]
    readonly_fields = ('started_at', 'completed_at', 'score', 'user', 'exam')
    
    def duration(self, obj):
        if obj.completed_at:
            duration = obj.completed_at - obj.started_at
            minutes = duration.total_seconds() / 60
            return f"{minutes:.1f} mins"
        return "In progress"
    duration.short_description = 'Duration'

class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'answer_text_short', 'is_correct')
    list_filter = ('is_correct', 'question__category', 'question__level')
    search_fields = ('answer_text', 'question__question_text')
    list_editable = ('is_correct',)
    
    def question_short(self, obj):
        return obj.question.question_text[:50] + '...' if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Question'
    
    def answer_text_short(self, obj):
        return obj.answer_text[:50] + '...' if len(obj.answer_text) > 50 else obj.answer_text
    answer_text_short.short_description = 'Answer'

admin.site.register(Category, CategoryAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(ExamAttempt, ExamAttemptAdmin)


from django.contrib import admin
from .models import Applicant, Interviewer

from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from .models import Applicant
from .views import assign_interviewer
@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'email', 'phone', 'interview_date', 
        'interview_time', 'interview_type', 'difficulty', 
        'status', 'rating', 'evaluator_name', 'interviewer'
    )
    list_filter = (
        'status', 'interview_type', 'difficulty', 'experience',
        'qualification', 'heard_from', 'interview_date', 'interviewer'
    )
    search_fields = (
        'first_name', 'last_name', 'email', 'phone',
        'skills', 'additional_skills', 'evaluator_name'
    )
    list_editable = (
        'interview_date', 'interview_time', 'status', 'rating'
    )
    readonly_fields = ('interview_id', 'confirmed', 'reminder_sent')
    ordering = ('-interview_date', 'interview_time')
    actions = ['assign_interviewer_action']

    fieldsets = (
        ('Personal Info', {
            'fields': ('user', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('Education & Skills', {
            'fields': ('year_of_passout', 'qualification', 'experience', 
                      'skills', 'additional_skills')
        }),
        ('Interview Details', {
            'fields': ('interviewer', 'interview_date', 'interview_time', 
                      'interview_link', 'interview_type', 'difficulty')
        }),
        ('Status & Evaluation', {
            'fields': ('status', 'rating', 'evaluator_name', 'feedback',
                      'evaluator_notes', 'confirmed', 'reminder_sent', 
                      'interview_id')
        }),
        ('Misc', {
            'fields': ('heard_from', 'resume'),
            'classes': ('collapse',)
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'first_name'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/assign-interviewer/', 
                 self.admin_site.admin_view(views.assign_interviewer), 
                 name='{}_{}_assign_interviewer'.format(
                     self.model._meta.app_label,
                     self.model._meta.model_name
                 )),
        ]
        return custom_urls + urls
    
    def assign_interviewer_action(self, request, queryset):
        if queryset.count() == 1:
            return redirect('admin:%s_%s_assign_interviewer' % (
                self.model._meta.app_label,
                self.model._meta.model_name
            ), object_id=queryset.first().pk)
        self.message_user(request, "Please select exactly one applicant to assign an interviewer", level='error')
    assign_interviewer_action.short_description = "Assign interviewer to selected applicant"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(interviewer=request.user)

    def get_list_display(self, request):
        if request.user.is_superuser:
            return super().get_list_display(request)
        return (
            'full_name', 'email', 'interview_date', 
            'interview_time', 'status', 'rating'
        )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return self.readonly_fields + ('interviewer', 'interview_date', 'interview_time')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not obj.interviewer_id:
            obj.interviewer = request.user
        super().save_model(request, obj, form, change)
    
    def get_interviewer(self, obj):
        return obj.interviewer.name if obj.interviewer else "-"
    get_interviewer.short_description = 'Interviewer'


class InterviewerAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'max_interviews_per_day', 'is_active')
    search_fields = ('name', 'specialization')

admin.site.register(Interviewer, InterviewerAdmin)

class InterviewFeedbackAdmin(admin.ModelAdmin):
    list_display = ('interview', 'evaluator', 'overall_score', 'recommendation', 'created_at')
    list_filter = ('recommendation', 'evaluator')
    search_fields = ('interview__applicant__name', 'evaluator__username', 'feedback')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    def overall_score(self, obj):
        return obj.overall_score
    overall_score.short_description = 'Overall Score'

admin.site.register(InterviewFeedback, InterviewFeedbackAdmin)