from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = 'exams'

urlpatterns = [
     path('dashboard/', views.student_dashboard, name='student_dashboard'),
     path('interviewer-dashboard/', login_required(views.interviewer_dashboard), name='interviewer_dashboard'),
    path('result/<int:attempt_id>/', views.exam_result, name='exam_result'),
    path('mock-exams/', views.exam_list, name='exam_list'),




    # Interview URLs
    path('mock-interview/', views.mock_interview_form, name='mock_interview_form'),
    path('interview/<int:pk>/', views.view_interview, name='view_interview'),
    path('interview/<int:pk>/edit/', views.edit_interview, name='edit_interview'),
    path('interview/<int:pk>/feedback/', views.interview_feedback, name='interview_feedback'),
    path('interview/<int:pk>/cancel/', views.cancel_interview, name='cancel_interview'),
    path('interview/<int:pk>/reschedule/', views.reschedule_interview, name='reschedule_interview'),
    path('interview/<uuid:interview_id>/join/', views.join_interview, name='join_interview'),
    
    


      path('admin/exams/applicant/<int:pk>/assign-interviewer/', 
         views.assign_interviewer, 
         name='assign_interviewer'),
    
    # Profile Settings URLs with login_required decorator
   path('settings/profile/', 
         login_required(views.profile_settings), 
         name='profile_settings'),
    
    path('settings/profile/update/', 
         login_required(views.update_profile), 
         name='update_profile'),
    path('settings/profile/career-preferences/',
         login_required(views.update_career_preferences),
         name='update_career_preferences'),
    
    path('settings/security/change-password/', 
         login_required(views.change_password), 
         name='change_password'),
    
    path('settings/notifications/', 
         login_required(views.update_notifications), 
         name='update_notifications'),
    
    path('settings/preferences/', 
         login_required(views.update_preferences), 
         name='update_preferences'),
    
    path('settings/sessions/<str:session_id>/terminate/',
         login_required(views.terminate_session), 
         name='terminate_session'),

    path('delete-photo/', views.delete_profile_photo, name='delete_profile_photo'),

    
    # API URLs
    # urls.py

    # Authentication
    path('api/auth/login/', views.api_login, name='api_login'),
    path('api/auth/signup/', views.api_signup, name='api_signup'),
    path('api/auth/logout/', views.api_logout, name='api_logout'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile
    path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    path('api/profile/password/', views.update_password, name='api_update_password'),
    
    # Exams
    path('api/exams/categories/', views.CategoryListAPIView.as_view(), name='api_category_list'),
    path('api/exams/', views.ExamListAPIView.as_view(), name='api_exam_list'),
    path('api/exams/<slug:exam_slug>/', views.ExamDetailAPIView.as_view(), name='api_exam_detail'),
    path('api/exams/<slug:exam_slug>/start/', views.StartExamAPIView.as_view(), name='api_start_exam'),
    path('api/exams/<slug:exam_slug>/<str:level>/set/<int:set_number>/question/<int:question_order>/', 
         views.ExamQuestionAPIView.as_view(), name='api_exam_question'),
    path('api/exams/attempts/<int:attempt_id>/result/', 
         views.ExamResultAPIView.as_view(), name='api_exam_result'),
    
    # Interviews
    path('api/interviews/', views.InterviewListCreateAPIView.as_view(), name='api_interview_list'),
    path('api/interviews/<int:pk>/', views.InterviewDetailAPIView.as_view(), name='api_interview_detail'),
    path('api/interviews/<int:pk>/feedback/', views.InterviewFeedbackAPIView.as_view(), name='api_interview_feedback'),
    path('api/interviews/<int:pk>/reschedule/', views.RescheduleInterviewAPIView.as_view(), name='api_reschedule_interview'),
    path('api/interviews/interviewers/', views.InterviewerListAPIView.as_view(), name='api_interviewer_list'),
    path('api/interviews/dashboard/', views.InterviewerDashboardAPIView.as_view(), name='api_interviewer_dashboard'),
    path('interview/<int:pk>/', views.view_interview, name='view_interview'),
    path('interview/<int:pk>/reschedule/', views.reschedule_interview, name='reschedule_interview'),
    # Dashboard
    path('api/dashboard/', views.api_student_dashboard, name='api_student_dashboard'),

    # mock exams
    path('api/browse-exams/', views.api_browse_exams, name='api_browse_exams'),
    path('api/how-it-works/', views.api_how_it_works, name='api_how_it_works'),
    path('api/all-categories/', views.api_all_categories, name='api_all_categories'),
    path('api/programming-exams/', views.api_programming_exams, name='api_programming_exams'),
    path('api/webpage-exams/', views.api_webpage_exams, name='api_webpage_exams'),

    # exam results
    path('api/exam-result/<int:attempt_id>/answers/', views.ExamResultAnswersAPIView.as_view()),
    path('api/exam-result/<int:attempt_id>/performance-by-type/', views.PerformanceByTypeAPIView.as_view()),
    path('api/bookmark-question/', views.BookmarkQuestionAPIView.as_view()),
    path('api/exam/<slug:exam_slug>/retake/', views.RetakeExamAPIView.as_view()),
  
  # study guide , your progress, and sample quesions buttons in exam detail page
    # Web views
    path('study-guide/', views.study_guide, name='study_guide'),
    path('user-analytics/', views.user_analytics, name='user_analytics'),
    path('sample-questions/<slug:exam_slug>/', views.sample_questions, name='sample_questions'),
    
    # API views (with api/ prefix)
    path('api/study-guide/', views.StudyGuideAPI.as_view(), name='study_guide_api') ,  
    path('api/user-progress/', views.UserProgressAPI.as_view(), name='api_user_progress'),
    path('api/sample-questions/<slug:exam_slug>/', views.SampleQuestionsAPI.as_view(), name='api_sample_questions'),

    # Existing exam URLs
    # Exam question with all parameters
 
    # Exam question URL pattern
    path('<slug:exam_slug>/<str:level>/<int:set_number>/<int:question_order>/',
         views.exam_question,
         name='exam_question'),
    
    # Exam detail view
    path('<slug:exam_slug>/',
         views.exam_detail,
         name='exam_detail'),
    
    # Exam result view
    path('attempt/<int:attempt_id>/',
         views.exam_result,
         name='exam_result'),

     # API URLs for mock interview form
    path('interviews/', views.InterviewScheduleView.as_view(), name='interview-schedule'),
    path('interviews/list/', views.InterviewListView.as_view(), name='interview-list'),
    path('interviews/<int:pk>/', views.InterviewDetailView.as_view(), name='interview-detail'),
    path('interviews/<int:pk>/feedback/', views.InterviewFeedbackView.as_view(), name='interview-feedback'),
    path('interviews/<int:pk>/cancel/', views.InterviewCancelView.as_view(), name='interview-cancel'),
    path('interviews/<int:pk>/reschedule/', views.InterviewRescheduleView.as_view(), name='interview-reschedule'),
    path('interviews/<uuid:interview_id>/join/', views.InterviewJoinView.as_view(), name='interview-join'),
    ]
