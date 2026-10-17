from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, Exam, Question, Answer, ExamAttempt, UserAnswer,
    Applicant, Interviewer, Profile
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Profile
        fields = ['user', 'phone', 'address', 'photo', 'bio', 'linkedin_url']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'is_correct']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'level', 'set_number', 'order', 'answers']

class ExamSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    questions_count = serializers.SerializerMethodField()
    class Meta:
        model = Exam
        fields = ['id', 'title', 'slug', 'description', 'category', 'duration', 'questions_count']
    def get_questions_count(self, obj):
        return obj.questions.count()

class ExamAttemptSerializer(serializers.ModelSerializer):
    exam = ExamSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    class Meta:
        model = ExamAttempt
        fields = ['id', 'exam', 'user', 'started_at', 'completed_at', 'score']

class UserAnswerSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_answer = AnswerSerializer(read_only=True)
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_answer', 'is_correct']

class InterviewerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Interviewer
        fields = ['id', 'user', 'specialization']

class ApplicantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    interviewer = InterviewerSerializer(read_only=True)
    class Meta:
        model = Applicant
        fields = [
            'id', 'user', 'first_name', 'last_name', 'email', 'phone',
            'interview_date', 'interview_time', 'status', 'skills',
            'interview_type', 'interviewer', 'rating', 'feedback', 'resume',
            'interview_link'
        ]

class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = '__all__'

class InterviewFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ['rating', 'feedback', 'strengths', 'areas_for_improvement']

class RescheduleInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ['interview_date', 'interview_time']

# For signup/login APIs
class SignupSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']
        extra_kwargs = {'password': {'write_only': True}}
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class ExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True, source='questions_set')

    class Meta:
        model = Exam
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'duration',
            'questions'
        ]

from rest_framework import serializers
from .models import ExamAttempt

class ExamAttemptSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source='exam.title')
    exam_slug = serializers.CharField(source='exam.slug')

    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'exam_title', 'exam_slug', 'score',
            'started_at', 'completed_at'
        ]

from rest_framework import serializers
from .models import UserAnswer

class UserAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text')
    question_order = serializers.IntegerField(source='question.order')
    selected_answer_text = serializers.CharField(source='selected_answer.answer_text')
    correct_answer_text = serializers.SerializerMethodField()
    explanation = serializers.CharField(source='question.explanation', allow_blank=True)
    category = serializers.CharField(source='question.category.name', default='General')
    difficulty = serializers.CharField(source='question.difficulty')

    def get_correct_answer_text(self, obj):
        correct = obj.question.answers.filter(is_correct=True).first()
        return correct.answer_text if correct else None

    class Meta:
        model = UserAnswer
        fields = [
            'id', 'question_order', 'question_text', 'selected_answer_text',
            'correct_answer_text', 'is_correct', 'explanation', 'category', 'difficulty'
        ]

  # study guide , your progress, and sample quesions buttons in exam detail page

# serializers.py
from rest_framework import serializers
from .models import Exam

class StudyGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ['title', 'description', 'category']

class UserProgressSerializer(serializers.Serializer):
    progress = serializers.IntegerField()

class SampleQuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()



from rest_framework import serializers
from .models import Applicant
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ApplicantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    resume_url = serializers.SerializerMethodField()
    is_upcoming = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Applicant
        fields = '__all__'
        read_only_fields = ['interview_id', 'interview_link', 'status', 'created_at', 'updated_at']
    
    def get_resume_url(self, obj):
        if obj.resume:
            return self.context['request'].build_absolute_uri(obj.resume.url)
        return None

class InterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ['email', 'first_name', 'last_name', 'phone', 'year_of_passout', 
                 'qualification', 'experience', 'heard_from', 'skills', 
                 'additional_skills', 'interview_date', 'interview_time', 
                 'interview_type', 'difficulty', 'resume']
        extra_kwargs = {
            'resume': {'required': True},
            'skills': {'required': True}
        }

class InterviewFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ['feedback', 'rating']
        
class InterviewRescheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicant
        fields = ['interview_date', 'interview_time']