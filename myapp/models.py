from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teachers = models.ManyToManyField(User, related_name='courses', limit_choices_to={'groups__name': 'Teacher'})

    def __str__(self):
        return self.name

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Teacher'})
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    assignment_file = models.FileField(upload_to='assignments/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.course.name})"

class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.name}"

class StudentAssignmentSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Student'})
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    assignment_file = models.FileField(upload_to='submissions/')
    submission_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} submission for {self.assignment.title}"

class Test(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField(null=True, blank=True)
    is_generated = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    question_text = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200)
    option4 = models.CharField(max_length=200)
    correct_option = models.IntegerField(choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")])
    marks = models.IntegerField(default=1)
    qna_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.question_text

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField(choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")])

class TestSourceDocument(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'groups__name': 'Teacher'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to='test_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    qna_id = models.IntegerField(null=True, blank=True) 
    def __str__(self):
        return f"{self.title} ({self.course.name})"
class AITestSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    qna_id = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'qna_id')

    def __str__(self):
        return f"{self.student.username} - QnA {self.qna_id}"

class AIStudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    qna_id = models.IntegerField()
    question_text = models.TextField()

    # For MCQ-type questions
    selected_option = models.CharField(max_length=1, null=True, blank=True)  # 'a', 'b', 'c', 'd'
    correct_option = models.CharField(max_length=1, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    # For short-answer type
    descriptive_answer = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return f"{self.student.username} - QnA {self.qna_id} - {self.question_text[:30]}"
