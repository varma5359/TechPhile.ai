from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class Topic(models.Model):
    """AI/ML Topics like Machine Learning, Deep Learning, etc."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Dataset(models.Model):
    """Datasets for ML problems like Titanic, Iris, etc."""
    name = models.CharField(max_length=100)
    filename = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to='datasets/',
        validators=[FileExtensionValidator(['csv', 'json', 'xlsx', 'zip', 'txt' ,'jpg', 'png'])],
    )
    file_size = models.BigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Problem(models.Model):
    """Coding problems for AI/ML topics."""
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    

    title = models.CharField(max_length=200)
    description = models.TextField()
    starter_code = models.TextField(blank=True)
    solution = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='problems')
    dataset = models.ForeignKey(Dataset, on_delete=models.SET_NULL, null=True, blank=True)
    points = models.IntegerField(default=100)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title
    @property
    def is_dataset_problem(self):
        return self.dataset is not None


class Submissions(models.Model):
    """User code submissions."""
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    output = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    execution_time = models.IntegerField(null=True, blank=True)  # in milliseconds
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title}"


class UserProgress(models.Model):
    """Track user progress on problems."""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('attempted', 'Attempted'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    best_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    attempts = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'problem']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.status})"


class Leaderboard(models.Model):
    """User leaderboard rankings."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    problems_solved = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_score']

    def __str__(self):
        return f"{self.user.username} - {self.total_score} points"