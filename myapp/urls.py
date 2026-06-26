from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher/tests/', views.manage_tests, name='manage_tests'),
    path('teacher/tests/<int:test_id>/questions/', views.add_questions, name='add_questions'),
    path('student/tests/', views.view_tests, name='view_tests'),
    path('test/<int:test_id>/result/', views.test_result, name='test_result'),
    path('student/tests/<int:test_id>/solve/', views.solve_test, name='solve_test'),
    path('view-generated-test/<int:doc_id>/', views.view_generated_test, name='view_generated_test'),
    path('ai-test/<int:qna_id>/solve/', views.solve_ai_test, name='solve_ai_test'),
    path('ai-test/<int:qna_id>/result/', views.view_ai_test_result, name='view_ai_test_result'),
    path('run-evaluation/', views.run_descriptive_evaluation, name='run_evaluation'),


]
