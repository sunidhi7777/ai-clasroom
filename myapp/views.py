from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib import messages
from .forms import TestForm, QuestionForm
from .models import Course, Assignment, StudentCourseEnrollment, StudentAssignmentSubmission, Test, Question, StudentAnswer, TestSourceDocument
from .models import Test
from .forms import TestSourceDocumentForm
from .models import AITestSubmission, TestSourceDocument
from .models import AIStudentAnswer 

def home(request):
    return render(request, 'myapp/login.html')

def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.groups.filter(name='Admin').exists():
                return redirect('admin_dashboard')
            elif user.groups.filter(name='Teacher').exists():
                return redirect('teacher_dashboard')
            elif user.groups.filter(name='Student').exists():
                return redirect('student_dashboard')
            else:
                return render(request, 'myapp/login.html', {'error': 'No group assigned.'})
        else:
            return render(request, 'myapp/login.html', {'error': 'Invalid credentials'})
    return render(request, 'myapp/login.html')

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def manage_tests(request):
    if request.method == "POST":
        form = TestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_tests')
    else:
        form = TestForm()
    tests = Test.objects.filter(course__teachers=request.user)
    return render(request, 'teacher/manage_tests.html', {'form': form, 'tests': tests})

@login_required
def add_questions(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.test = test
            question.save()
            return redirect('add_questions', test_id=test_id)
    else:
        form = QuestionForm()
    questions = Question.objects.filter(test=test)
    return render(request, 'teacher/add_questions.html', {'form': form, 'questions': questions, 'test': test})

@login_required
def view_tests(request):
    courses = Course.objects.filter(studentcourseenrollment__student=request.user)
    tests = Test.objects.filter(course__in=courses)
    return render(request, 'myapp/student/view_tests.html', {'tests': tests})

@login_required
def test_result(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test)
    answers = StudentAnswer.objects.filter(student=request.user, question__in=questions)

    score = 0
    for answer in answers:
        if answer.selected_option == answer.question.correct_option:
            score += answer.question.marks

    context = {
        'test': test,
        'answers': answers,
        'score': score,
    }
    return render(request, 'myapp/student/test_result.html', context)

@login_required
def solve_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = Question.objects.filter(test=test)

    if StudentAnswer.objects.filter(student=request.user, question__in=questions).exists():
        # Already submitted, show score
        answers = StudentAnswer.objects.filter(student=request.user, question__in=questions)
        score = 0
        for ans in answers:
            if ans.selected_option == ans.question.correct_option:
                score += ans.question.marks
        return render(request, 'myapp/student/test_result.html', {
            'test': test,
            'answers': answers,
            'score': score,
        })

    if request.method == 'POST':
        for question in questions:
            selected_option = request.POST.get(f'question_{question.id}')
            if selected_option:
                StudentAnswer.objects.create(
                    student=request.user,
                    question=question,
                    selected_option=int(selected_option)
                )
        messages.success(request, "Test submitted successfully!")
        return redirect('student_dashboard')
    return render(request, 'myapp/student/solve_tests.html', {
        'test': test,
        'questions': questions,
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Course, Assignment, StudentCourseEnrollment, Test, Question

@login_required
def teacher_dashboard(request):
    if not request.user.groups.filter(name='Teacher').exists():
        return redirect('home')

    teacher_courses = request.user.courses.all()
    assignments = Assignment.objects.filter(course__in=teacher_courses, teacher=request.user)
    students_enrolled = [(course, StudentCourseEnrollment.objects.filter(course=course)) for course in teacher_courses]
    students = User.objects.filter(groups__name='Student')
    doc_form = TestSourceDocumentForm()
    doc_form.fields['course'].queryset = request.user.courses.all()
    test_docs = TestSourceDocument.objects.filter(teacher=request.user)

    if request.method == 'POST':

        # 1. Upload Assignment
        if 'upload_assignment' in request.POST:
            course_id = request.POST.get('course')
            title = request.POST.get('title')
            description = request.POST.get('description')
            due_date = request.POST.get('due_date')
            assignment_file = request.FILES.get('assignment_file')

            if course_id and title and description and due_date and assignment_file:
                try:
                    course = Course.objects.get(id=course_id)
                    Assignment.objects.create(
                        course=course,
                        teacher=request.user,
                        title=title,
                        description=description,
                        due_date=due_date,
                        assignment_file=assignment_file
                    )
                    messages.success(request, 'Assignment uploaded successfully!')
                except Exception as e:
                    messages.error(request, f"Error: {str(e)}")
            else:
                messages.error(request, "All fields are required.")
            return redirect('teacher_dashboard')

        # 2. Edit Assignment
        elif 'edit_assignment' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            try:
                assignment = Assignment.objects.get(id=assignment_id, teacher=request.user)
                assignment.title = request.POST.get('title')
                assignment.description = request.POST.get('description')
                assignment.due_date = request.POST.get('due_date')
                if request.FILES.get('assignment_file'):
                    assignment.assignment_file = request.FILES.get('assignment_file')
                assignment.save()
                messages.success(request, "Assignment updated successfully.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            return redirect('teacher_dashboard')

        # 3. Remove Student from Course
        elif 'remove_student' in request.POST:
            student_id = request.POST.get('student_id')
            course_id = request.POST.get('course_id')
            try:
                student = User.objects.get(id=student_id)
                course = Course.objects.get(id=course_id)
                enrollment = StudentCourseEnrollment.objects.filter(student=student, course=course).first()
                if enrollment:
                    enrollment.delete()
                    messages.success(request, f"{student.username} has been removed from {course.name}.")
                else:
                    messages.error(request, "This student is not enrolled in the selected course.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            return redirect('teacher_dashboard')

        # 4. Remove Assignment
        elif 'remove_assignment' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            assignment = Assignment.objects.filter(id=assignment_id, teacher=request.user).first()
            if assignment:
                assignment.delete()
                messages.success(request, "Assignment deleted successfully.")
            else:
                messages.error(request, "Assignment not found or you don't have permission to delete it.")
            return redirect('teacher_dashboard')

        # 5. Upload MCQ Test
        elif 'upload_test' in request.POST:
            title = request.POST.get('title')
            course_id = request.POST.get('course')
            question_count = request.POST.get('question_count')

            if not (title and course_id and question_count):
                messages.error(request, "Missing required fields.")
                return redirect('teacher_dashboard')

            try:
                question_count = int(question_count)
                course = Course.objects.get(id=course_id)
                if request.user not in course.teachers.all():
                    messages.error(request, "You're not assigned to this course.")
                    return redirect('teacher_dashboard')

                from datetime import date, timedelta
                test = Test.objects.create(
                    title=title,
                    description="MCQ Test",
                    due_date=date.today() + timedelta(days=7),
                    course=course
                )
                for i in range(1, question_count + 1):
                    q_text = request.POST.get(f'question{i}')
                    opt1 = request.POST.get(f'q{i}_option1')
                    opt2 = request.POST.get(f'q{i}_option2')
                    opt3 = request.POST.get(f'q{i}_option3')
                    opt4 = request.POST.get(f'q{i}_option4')
                    correct = request.POST.get(f'q{i}_correct')
                    if not all([q_text, opt1, opt2, opt3, opt4, correct]):
                        continue
                    Question.objects.create(
                        test=test,
                        question_text=q_text,
                        option1=opt1,
                        option2=opt2,
                        option3=opt3,
                        option4=opt4,
                        correct_option=int(correct)
                    )
                messages.success(request, "MCQ Test uploaded successfully!")
            except Exception as e:
                messages.error(request, f"Upload failed: {str(e)}")
            return redirect('teacher_dashboard')

        # 6. Delete MCQ Test
        elif 'delete_test' in request.POST:
            test_id = request.POST.get('test_id')
            try:
                test = Test.objects.get(id=test_id)
                if test.course in teacher_courses:
                    test.delete()
                    messages.success(request, "Test deleted successfully.")
                else:
                    messages.error(request, "You don't have permission to delete this test.")
            except Test.DoesNotExist:
                messages.error(request, "Test not found.")
            return redirect('teacher_dashboard')

        # 7. Upload .docx Test Source for LLM
        elif 'upload_test_doc' in request.POST:
            doc_form = TestSourceDocumentForm(request.POST, request.FILES)
            if doc_form.is_valid():
                test_doc = doc_form.save(commit=False)
                test_doc.teacher = request.user
                test_doc.save()

                try:
                    with open(test_doc.uploaded_file.path, "rb") as f:
                        res = requests.post("http://127.0.0.1:8001/generate-questions/", files={"file": f})
                    if res.status_code == 200:
                        test_doc.qna_id = res.json().get("saved_id")
                        test_doc.save()
                        messages.success(request, "Document uploaded & test generated!")
                    else:
                        messages.warning(request, "Uploaded, but test generation failed.")
                except Exception as e:
                    messages.error(request, f"Error sending to LLM: {e}")
            else:
                messages.error(request, "Form is invalid.")
            return redirect('teacher_dashboard')

        # 8. Delete uploaded .docx Test Source
        elif 'delete_test_doc' in request.POST:
            doc_id = request.POST.get('doc_id')
            try:
                doc = TestSourceDocument.objects.get(id=doc_id, teacher=request.user)
                doc.uploaded_file.delete()
                doc.delete()
                messages.success(request, "Document deleted successfully.")
            except TestSourceDocument.DoesNotExist:
                messages.error(request, "Document not found or unauthorized.")
            return redirect('teacher_dashboard')

    # 9. Assign student to course (via GET)
    if request.method == 'GET' and 'assign_student' in request.GET:
        student_id = request.GET.get('student_id')
        course_id = request.GET.get('course_id')
        try:
            student = User.objects.get(id=student_id)
            course = Course.objects.get(id=course_id)
            if not StudentCourseEnrollment.objects.filter(student=student, course=course).exists():
                StudentCourseEnrollment.objects.create(student=student, course=course)
                messages.success(request, f"{student.username} assigned to {course.name}.")
            else:
                messages.warning(request, f"{student.username} is already enrolled in {course.name}.")
        except Exception as e:
            messages.error(request, str(e))
        return redirect('teacher_dashboard')

    # 10. Fetch MCQ Tests
    tests = Test.objects.filter(course__teachers=request.user)

    return render(request, 'myapp/teacher_dashboard.html', {
        'teacher_courses': teacher_courses,
        'assignments': assignments,
        'students_enrolled': students_enrolled,
        'students': students,
        'tests': tests,
        'doc_form': doc_form,
        'test_docs': test_docs
    })

@login_required
def student_dashboard(request):
    if not request.user.groups.filter(name='Student').exists():
        return redirect('home')

    # Get courses the student is enrolled in
    student_courses = Course.objects.filter(studentcourseenrollment__student=request.user)

    # Assignments & submissions
    assignments = Assignment.objects.filter(course__in=student_courses)
    submitted_assignments_ids = StudentAssignmentSubmission.objects.filter(
        student=request.user,
        assignment__in=assignments
    ).values_list('assignment_id', flat=True)

    # Manual tests and grouping by course
    tests = Test.objects.filter(course__in=student_courses)

    # Student has submitted which manual tests? (match on question.test foreign key)
    submitted_test_question_ids = StudentAnswer.objects.filter(
        student=request.user
    ).values_list('question__id', flat=True)

    submitted_test_ids = Question.objects.filter(
        id__in=submitted_test_question_ids,
        test__in=tests
    ).values_list('test__id', flat=True).distinct()
    # Get AI-generated tests
    ai_tests = TestSourceDocument.objects.filter(course__in=student_courses).exclude(qna_id__isnull=True)

    # Get submitted AI test qna_ids
    submitted_ai_test_ids = AITestSubmission.objects.filter(
        student=request.user
    ).values_list('qna_id', flat=True)

    tests_by_course = {}
    for course in student_courses:
        course_tests = tests.filter(course=course)
        tests_by_course[course] = course_tests

    ai_tests = TestSourceDocument.objects.filter(course__in=student_courses).exclude(qna_id=None)

    ai_qna_ids = ai_tests.values_list('qna_id', flat=True)

    # Get submitted AI test qna_ids from AITestSubmission model
    submitted_ai_test_ids = AITestSubmission.objects.filter(
        student=request.user
    ).values_list('qna_id', flat=True)

    # Ensure type matches
    submitted_ai_test_ids = list(map(int, submitted_ai_test_ids))

    # Handle assignment upload or unsubmit
    if request.method == 'POST':
        if 'upload_assignment' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            uploaded_file = request.FILES.get('assignment_file')
            if assignment_id and uploaded_file:
                try:
                    assignment = Assignment.objects.get(id=assignment_id)
                    if not StudentCourseEnrollment.objects.filter(student=request.user, course=assignment.course).exists():
                        messages.error(request, "You are not enrolled in the course for this assignment.")
                        return redirect('student_dashboard')
                    if assignment.id in submitted_assignments_ids:
                        messages.warning(request, "You have already submitted this assignment.")
                        return redirect('student_dashboard')
                    StudentAssignmentSubmission.objects.create(
                        student=request.user,
                        assignment=assignment,
                        assignment_file=uploaded_file
                    )
                    messages.success(request, "Assignment submitted successfully!")
                except Assignment.DoesNotExist:
                    messages.error(request, "Assignment not found.")
                except Exception as e:
                    messages.error(request, f"Error uploading assignment: {str(e)}")
                return redirect('student_dashboard')

        elif 'unsubmit_assignment' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    submission = StudentAssignmentSubmission.objects.get(
                        student=request.user,
                        assignment_id=assignment_id
                    )
                    submission.delete()
                    messages.success(request, "Submission removed successfully. You can upload again.")
                except StudentAssignmentSubmission.DoesNotExist:
                    messages.error(request, "Submission not found.")
                except Exception as e:
                    messages.error(request, f"Error removing submission: {str(e)}")
            return redirect('student_dashboard')
    return render(request, 'myapp/student_dashboard.html', {
        'student_courses': student_courses,
        'assignments': assignments,
        'submitted_assignments_ids': submitted_assignments_ids,
        'tests_by_course': tests_by_course,
        'submitted_test_ids': submitted_test_ids,
        'ai_tests': ai_tests,
        'submitted_ai_test_ids': submitted_ai_test_ids,
    })

@login_required
def admin_dashboard(request):
    courses = Course.objects.all()
    teachers = User.objects.filter(groups__name='Teacher')

    if request.method == 'POST':
        if 'add_course' in request.POST:
            course_name = request.POST['course_name']
            if course_name:
                Course.objects.create(name=course_name, description='N/A')
                messages.success(request, "Course added successfully!")
                return redirect('admin_dashboard')

        elif 'assign_teacher' in request.POST:
            teacher_id = request.POST['teacher']
            course_id = request.POST['course']
            try:
                teacher = User.objects.get(id=teacher_id)
                course = Course.objects.get(id=course_id)
                if teacher in course.teachers.all():
                    messages.error(request, "Teacher is already assigned to this course.")
                else:
                    course.teachers.add(teacher)
                    messages.success(request, "Teacher assigned successfully!")
            except User.DoesNotExist:
                messages.error(request, "Teacher not found.")
            except Course.DoesNotExist:
                messages.error(request, "Course not found.")
            return redirect('admin_dashboard')

        elif 'remove_teacher' in request.POST:
            teacher_id = request.POST['teacher_id']
            course_id = request.POST['course_id']
            try:
                teacher = User.objects.get(id=teacher_id)
                course = Course.objects.get(id=course_id)
                course.teachers.remove(teacher)
                messages.success(request, "Teacher removed from course.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
            return redirect('admin_dashboard')

        elif 'delete_course' in request.POST:
            course_id = request.POST.get('delete_course_id')
            Course.objects.filter(id=course_id).delete()
            messages.success(request, "Course deleted.")
            return redirect('admin_dashboard')

    return render(request, 'myapp/admin_dashboard.html', {
        'courses': courses,
        'teachers': teachers,
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import requests

@login_required
def view_generated_test(request, doc_id):
    if not request.user.groups.filter(name='Teacher').exists():
        return redirect('home')

    doc = get_object_or_404(TestSourceDocument, id=doc_id, teacher=request.user)

    try:
        # Send .docx file to FastAPI to generate questions
        with open(doc.uploaded_file.path, 'rb') as f:
            response = requests.post(
                'http://127.0.0.1:8001/generate-questions/',
                files={'file': (doc.uploaded_file.name, f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            )

        if response.status_code != 200:
            messages.error(request, "LLM API error.")
            return redirect('teacher_dashboard')

        result = response.json()
        qna_id = result.get("saved_id")

        # ✅ Save qna_id to the TestSourceDocument instance
        doc.qna_id = qna_id
        doc.save()

        # Get questions from FastAPI by qna_id
        q_response = requests.get(f"http://127.0.0.1:8001/questions/{qna_id}")
        if q_response.status_code != 200:
            messages.error(request, "Failed to fetch questions.")
            return redirect('teacher_dashboard')

        questions = q_response.json()
        mcqs = [q for q in questions if q["type"] == "mcq"]
        long_answers = [q for q in questions if q["type"] == "short"]

        # Fix key mismatch: map 'answer_text' to 'answer' so template works
        '''for q in long_answers:
            q["answer"] = q.pop("answer_text", "")'''
        for q in long_answers:
            if "answer" not in q:
             q["answer"] = q.pop("answer_text", "")

        return render(request, 'myapp/view_generated_test.html', {
            'doc': doc,
            'mcqs': mcqs,
            'long_answers': long_answers
        })

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('teacher_dashboard')

@login_required
def solve_ai_test(request, qna_id):
    if not request.user.groups.filter(name='Student').exists():
        return redirect('home')

    if AITestSubmission.objects.filter(student=request.user, qna_id=qna_id).exists():
        messages.warning(request, "You've already submitted this test.")
        return redirect('student_dashboard')

    response = requests.get(f"http://127.0.0.1:8001/questions/{qna_id}")
    if response.status_code != 200:
        messages.error(request, "Failed to fetch test questions.")
        return redirect('student_dashboard')

    questions = response.json()

    if request.method == 'POST':
        AITestSubmission.objects.create(student=request.user, qna_id=qna_id)

        for index, q in enumerate(questions):
            qtype = q.get("type")
            question_text = q.get("question", "")
            correct_option = (q.get("correct_option") or "").lower()


            input_name = f"q_{index}"  # same as in template

            if qtype == "mcq":
                selected = request.POST.get(input_name, "")
                selected = selected.lower() if selected else ""
                is_correct = selected == correct_option

                AIStudentAnswer.objects.create(
                    student=request.user,
                    qna_id=qna_id,
                    question_text=question_text,
                    selected_option=selected,
                    correct_option=correct_option,
                    is_correct=is_correct
                )
            elif qtype == "short":
                descriptive_answer = request.POST.get(input_name, "").strip()
                print(f"[DEBUG] Input Name: {input_name} | Answer: '{descriptive_answer}'")

                if descriptive_answer:
                    print(f"[DEBUG] Saving descriptive answer for Q: {question_text}")
                    AIStudentAnswer.objects.create(
                        student=request.user,
                        qna_id=qna_id,
                        question_text=question_text,
                        descriptive_answer=descriptive_answer
                    )
                else:
                    print(f"[DEBUG] Empty input for: {input_name}")
        messages.success(request, "Test submitted successfully!")
        return redirect('student_dashboard')

    return render(request, 'myapp/solve_ai_test.html', {
        'questions': questions,
        'qna_id': qna_id,
    })


@login_required
def view_ai_test_result(request, qna_id):
    if not request.user.groups.filter(name='Student').exists():
        return redirect('home')

    if not AITestSubmission.objects.filter(student=request.user, qna_id=qna_id).exists():
        messages.error(request, "You haven't submitted this test.")
        return redirect('student_dashboard')

    answers = AIStudentAnswer.objects.filter(student=request.user, qna_id=qna_id)
    mcqs = answers.filter(selected_option__isnull=False)
    descriptive = answers.exclude(descriptive_answer__isnull=True).exclude(descriptive_answer__exact='')
    
    try:
        res = requests.get(f"http://127.0.0.1:8001/questions/{qna_id}")
        questions = res.json()
        qna_map = {q['question']: q.get('answer', q.get('answer_text', '')) for q in questions if q['type'] == 'short'}
    except:
        qna_map = {}

    for ans in descriptive:
        if ans.score is None and ans.feedback is None:
            expected = qna_map.get(ans.question_text, "")
            if expected:
                score, feedback = evaluate_descriptive_answer(ans.question_text, expected, ans.descriptive_answer)
                ans.score = score
                ans.feedback = feedback
                ans.save()

    score = sum(1 for ans in mcqs if ans.is_correct)

    return render(request, 'myapp/view_ai_test_result.html', {
        'qna_id': qna_id,
        'mcqs': mcqs,
        'descriptive': descriptive,
        'score': score,
        'total': mcqs.count(),
    })
    
def evaluate_descriptive_answer(question, expected, student):
    try:
        res = requests.post(
            "http://127.0.0.1:8001/evaluate-answer/",
            json={"prompt": question, "expected": expected, "student": student}
        )
        if res.status_code == 200:
            data = res.json()
            return data.get("score", 0.0), data.get("feedback", "")
        else:
            return 0.0, "LLM Evaluation Failed"
    except Exception as e:
        return 0.0, f"Error: {str(e)}"

from .models import AIStudentAnswer
import requests
from django.http import JsonResponse

def run_descriptive_evaluation(request):
    # Only fetch descriptive answers that haven't been scored yet
    answers = AIStudentAnswer.objects.filter(
        descriptive_answer__isnull=False,
        score__isnull=True
    )

    for ans in answers:
        qna_id = ans.qna_id
        question_text = ans.question_text

        try:
            # Fetch model answer via FastAPI
            q_response = requests.get(f"http://127.0.0.1:8001/questions/{qna_id}")
            if q_response.status_code != 200:
                continue

            questions = q_response.json()
            match = next((q for q in questions if q["type"] == "short" and q["question"] == question_text), None)
            if not match:
                continue

            model_answer = match.get("answer") or match.get("answer_text", "")
            student_answer = ans.descriptive_answer

            # Evaluate using your existing function
            score, feedback = evaluate_descriptive_answer(question_text, model_answer, student_answer)

            # Save result
            ans.score = score
            ans.feedback = feedback
            ans.save()

        except Exception as e:
            print(f"Error evaluating answer: {e}")
            continue

    return JsonResponse({"status": "Evaluation complete"})

