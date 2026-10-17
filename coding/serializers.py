from rest_framework import serializers
from .models import Problem, Submission, UserProfile
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'total_solved', 'easy_solved', 'medium_solved', 'hard_solved']

class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = [
            'id', 'title', 'slug', 'description', 'difficulty', 
            'category', 'input_format', 'output_format', 'constraints',
            'sample_input', 'sample_output'
        ]

class SubmissionSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Submission
        fields = [
            'id', 'problem', 'user', 'code', 'language', 
            'status', 'execution_time', 'memory_used', 'submitted_at'
        ]

class CodeExecutionSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = serializers.CharField()
    input = serializers.CharField(required=False, allow_blank=True)
    expected_output = serializers.CharField(required=False, allow_blank=True)