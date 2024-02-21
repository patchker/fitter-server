"""
URL configuration for inz_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import RegisterView, create_order, OrderListView
from .views import diet_plans_view, verify_token, UserWithOrdersListView, diet_plans_view2, \
    save_diet_day, DietPreferencesView, TrainingSessionView, UserProgressView, BodyMeasurementList, \
    BodyMeasurementDetail, TrainingsList, TrainingStart, MealAI, DietIngredientsView, search_exercises, get_user_roles, \
    CustomTokenObtainPairView, verify_email, resend_verification_email, change_password

router = DefaultRouter()
router.register(r'profile', views.UserViewSet)

urlpatterns = [
    path('works/fitter/api/admin/', admin.site.urls),
    path('works/fitter/api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('works/fitter/api/register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
    path('works/fitter/api/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('works/fitter/api/zamowienia/', create_order, name='create_order'),
    path('works/fitter/api/user_orders/', views.user_orders, name='user_orders'),
    path('works/fitter/api/diet-plans/', diet_plans_view, name='diet_plans'),
    path('works/fitter/api/dieteditor/', diet_plans_view2, name='diet_plans'),
    path('works/fitter/api/verify-token/', verify_token, name='verify_token'),
    path('works/fitter/api/meal/<int:meal_id>/', views.get_meal, name='get_meal'),
    path('works/fitter/api/search_meals/', views.search_meals, name='search_meals'),
    path('works/fitter/api/users/', OrderListView.as_view(), name='users-with-orders'),
    path('works/fitter/api/save_diet_data/', save_diet_day, name='save_diet_day'),
    path('works/fitter/api/diet-preferences/', DietPreferencesView.as_view(), name='diet-preferences'),
    path('works/fitter/api/training-session/', TrainingSessionView.as_view(), name='training-session'),
    path('works/fitter/api/user-progress/', UserProgressView.as_view(), name='user-progress'),
    path('works/fitter/api/measurements/', BodyMeasurementList.as_view(), name='body-measurements'),
    path('works/fitter/api/trainings/', TrainingsList.as_view(), name='body-measurements'),
    path('works/fitter/api/training-start/', TrainingStart.as_view(), name='body-measurements'),
    path('works/fitter/api/mealAI/', MealAI, name='mealAI'),
    path('works/fitter/api/mealAIResponse/', views.MealAIResponse, name='callback-view'),

    path('works/fitter/api/verify/<uuid:token>/', verify_email, name='verify-email'),
    path('works/fitter/api/resend-verification-email/', resend_verification_email, name='resend-verification-email'),

    path('works/fitter/api/measurements/<int:pk>/', BodyMeasurementDetail.as_view(), name='body-measurement-detail'),
    path('works/fitter/api/diet-ingredients/<str:start_date>/<str:end_date>/', DietIngredientsView.as_view(),
         name='diet-ingredients'),
    path('works/fitter/api/training-session/<int:training_id>/add-exercise', views.add_exercise_to_training_session,
         name='add_exercise_to_training_session'),
    path('works/fitter/api/exercises', search_exercises, name='search_exercises'),
    path('works/fitter/api/user-data/', get_user_roles, name='search_exercises'),
    path('works/fitter/api/change-password/', change_password, name='search_exercises'),

]
