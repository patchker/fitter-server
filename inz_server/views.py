import json
from collections import defaultdict
from datetime import datetime, timedelta

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum, F
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from rest_framework import filters
from rest_framework import generics, viewsets, pagination
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.views import TokenObtainPairView

from inz_server.models import Dieta, Zamowienie, CustomUser, DietMeal, MealIngredient, Exercise2, MeasurementUnit, \
    EmailVerificationToken
from .models import BodyMeasurement
from .models import DietDay
from .models import Meal
from .models import TrainingSession
from .models import UserDiet
from .serializers import BodyMeasurementSerializer, OrderSerializer
from .serializers import CustomTokenObtainPairSerializer
from .serializers import ExerciseSerializer
from .serializers import TrainingSessionSerializer
from .serializers import UserDietSerializer, DietIngredientsSerializer, ExerciseSerializer2
from .serializers import UserSerializer, ZamowienieSerializer, UserSerializer2


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CustomUserPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'total_pages': self.page.paginator.num_pages,
            'total_items': self.page.paginator.count,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'results': data
        })


class UserWithOrdersListView(generics.ListAPIView):
    queryset = CustomUser.objects.annotate(order_count=Count('zamowienie')).filter(order_count__gt=0)
    serializer_class = UserSerializer2
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']
    pagination_class = CustomUserPagination

    def get_queryset(self):
        queryset = CustomUser.objects.annotate(order_count=Count('zamowienie')).filter(order_count__gt=0)

        order_status = self.request.query_params.get('orderStatus', None)
        if order_status:
            queryset = queryset.filter(zamowienie__status=order_status)

        return queryset


class CustomPagination(PageNumberPagination):
    page_size = 10


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['uzytkownik__username', 'id']
    pagination_class = CustomPagination

    def get_queryset(self):
        order_status = self.request.query_params.get('orderStatus', None)
        queryset = Zamowienie.objects.all()

        if order_status:
            queryset = queryset.filter(status=order_status)
        return queryset


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ZamowienieViewSet(viewsets.ModelViewSet):
    queryset = Zamowienie.objects.all()
    serializer_class = ZamowienieSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    user = request.user
    dieta_id = request.data.get('dieta_id')
    duration_months = int(request.data.get('duration'))

    try:
        dieta = Dieta.objects.get(id=dieta_id)
    except Dieta.DoesNotExist:
        return Response({"error": "Dieta o podanym id nie istnieje."}, status=status.HTTP_400_BAD_REQUEST)

    data_rozpoczecia = datetime.now()
    data_zakonczenia = (datetime.now() + timedelta(days=30 * duration_months))

    zamowienie = Zamowienie.objects.create(uzytkownik=user, dieta=dieta, status='new',
                                           data_rozpoczecia=data_rozpoczecia, data_zakonczenia=data_zakonczenia,
                                           duration=duration_months)

    user_diet = UserDiet.objects.create(user=user, dieta=dieta, data_rozpoczecia=data_rozpoczecia,
                                        data_zakonczenia=data_zakonczenia)

    zamowienie.user_diet = user_diet
    zamowienie.save()

    if dieta_id != 1:
        for month in range(duration_months):
            for day in range(30):
                DietDay.objects.create(user_diet=user_diet, date=(data_rozpoczecia + timedelta(days=day + month * 30)))

    data = {
        "message": "Zamówienie zostało pomyślnie utworzone.",
        "zamowienie_id": zamowienie.id
    }

    return Response(data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders(request):
    user = request.user
    orders = Zamowienie.objects.filter(uzytkownik=user)
    serializer = ZamowienieSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def diet_plans_view(request):
    user_id = request.user.id
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

        order = Zamowienie.objects.filter(uzytkownik_id=user_id).latest('data_rozpoczecia')
        user_diet = UserDiet.objects.filter(user_id=user_id).latest('data_rozpoczecia')

        order_data = {
            'id': order.id,
            'start_date': order.data_rozpoczecia,
            'end_date': order.data_zakonczenia,
            'status': order.status,
            'dieta': order.dieta.id,
        }

        diet_days = DietDay.objects.filter(
            user_diet=user_diet,
            date__range=[start_date_obj, end_date_obj]
        ).prefetch_related('meals')

        def meal_data(diet_meal):
            meal = diet_meal.meal
            return {
                'id': meal.id,
                'name': meal.name,
                'quantity': diet_meal.quantity,
                'unit': diet_meal.unit,
                'uuid': diet_meal.uuid,
                'short_description': meal.short_description,
                'calories': meal.calories,
                'calories_per_100g': meal.calories_per_100g,
                "default_grams": meal.default_grams,
                'carbohydrates': meal.carbohydrates,
                'fats': meal.fats,
                'protein': meal.protein,
                'preparation_time': meal.preparation_time,
                'image_url': meal.image_url,
            }

        data = {
            'preferences_set': user_diet.preferences_set,
            'order_info': order_data,
            'days': []
        }

        for dd in diet_days:
            meals_by_type = defaultdict(list)
            diet_meals = DietMeal.objects.filter(diet_day=dd).select_related('meal')
            for dm in diet_meals:
                meal_type = dm.meal_type
                meals_by_type[meal_type].append(meal_data(dm))

            day_data = {
                'date': dd.date,
                'meals': {
                    'breakfast': meals_by_type['breakfast'],
                    'lunch': meals_by_type['lunch'],
                    'dinner': meals_by_type['dinner'],
                    'afternoon_snack': meals_by_type['afternoon_snack'],
                    'evening_snack': meals_by_type['evening_snack'],
                }
            }

            data['days'].append(day_data)

        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def diet_plans_view2(request):
    orderID = request.GET.get('orderID')
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    try:
        zamowienie = Zamowienie.objects.get(id=orderID)
        user_nick = zamowienie.uzytkownik
        user = CustomUser.objects.get(username=user_nick)
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        user_diet = zamowienie.user_diet
        diet_plan_details = {
            'username': user.username,
            'diet_id': user_diet.id,
            'diet_type': user_diet.diet_type,
            'diet_start_date': user_diet.data_rozpoczecia,
            'diet_end_date': user_diet.data_zakonczenia,
            'gluten_free': user_diet.gluten_free,
            'lactose_free': user_diet.lactose_free,
            'nut_free': user_diet.nut_free,
            'fish_free': user_diet.fish_free,
            'soy_free': user_diet.soy_free,
            'food_preferences_1': user_diet.get_preferences_by_value(2),
            'food_preferences_2': user_diet.get_preferences_by_value(0),
            'status': zamowienie.status,
            'calories': calculate_caloric_needs(user_diet),
        }

        diet_days = DietDay.objects.filter(
            user_diet=user_diet,
            date__range=[start_date_obj, end_date_obj]
        ).prefetch_related('meals')

        def meal_data(diet_meal):
            meal = diet_meal.meal
            return {
                'id': meal.id,
                'name': meal.name,
                'quantity': diet_meal.quantity,
                'unit': diet_meal.unit,
                'meal_type': diet_meal.meal_type,
                'short_description': meal.short_description,
                'calories': meal.calories,
                'calories_per_100g': meal.calories_per_100g,
                "default_grams": meal.default_grams,
                'carbohydrates': meal.carbohydrates,
                'fats': meal.fats,
                'protein': meal.protein,
                'preparation_time': meal.preparation_time,
                'image_url': meal.image_url,
                'uuid': diet_meal.uuid,
            }

        days_data = [{
            'date': dd.date,
            'meals': [meal_data(dm) for dm in DietMeal.objects.filter(diet_day=dd)]
        } for dd in diet_days]
        data = {
            'diet_plan': diet_plan_details,
            'days': days_data
        }

        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['POST'])
def verify_token(request):
    token = request.data.get('token')
    if token is None:
        return Response({'detail': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        UntypedToken(token)
    except (InvalidToken, TokenError) as e:
        return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({'detail': 'Token is valid'}, status=status.HTTP_200_OK)


def get_meal(request, meal_id):
    try:
        meal = Meal.objects.get(id=meal_id)
        meal_data = {
            'id': meal.id,
            'name': meal.name,
            'long_description': meal.long_description,
            'calories': meal.calories,
            'calories_per_100g': meal.calories_per_100g,
            "default_grams": meal.default_grams,
            'carbohydrates': meal.carbohydrates,
            'fats': meal.fats,
            'protein': meal.protein,
            'preparation_time': meal.preparation_time,
            'image_url': meal.image_url,
        }
        return JsonResponse(meal_data)
    except Meal.DoesNotExist:
        return JsonResponse({"error": "Meal not found"}, status=404)


@api_view(['GET'])
def search_meals(request):
    query = request.GET.get('query', '')

    meals = Meal.objects.filter(Q(name__icontains=query))[:10]

    meal_list = []
    for meal in meals:
        meal_data = {
            'id': meal.id,
            'name': meal.name,
            'long_description': meal.long_description,
            'calories': meal.calories,
            'grams': 100,
            'calories_per_100g': meal.calories_per_100g,
            "default_grams": meal.default_grams,
            'carbohydrates': meal.carbohydrates,
            'fats': meal.fats,
            'protein': meal.protein,
            'preparation_time': meal.preparation_time,
            'image_url': meal.image_url,
            'lactose_free': meal.lactose,
            'nut_free': meal.nut,
            'soy_free': meal.soy,
            'gluten_free': meal.gluten,
            'fish_free': meal.fish,
        }
        meal_list.append(meal_data)
    return JsonResponse(meal_list, safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_diet_day(request):
    orderID = request.data.get('orderID')

    zamowienie_status = request.data.get('status')

    try:
        zamowienie = Zamowienie.objects.get(id=orderID)
        user_nick = zamowienie.uzytkownik
        user = CustomUser.objects.get(username=user_nick)

        user_diet = zamowienie.user_diet
        zamowienie.status = zamowienie_status
        zamowienie.save()
        diet_data = request.data.get('diet_data')

        for day_data in diet_data:
            date_str = day_data.get('date')
            meals_data = day_data.get('meals')

            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            diet_day, created = DietDay.objects.get_or_create(
                user_diet=user_diet,
                date=date_obj,
            )

            sent_meals_uuids = {meal_data.get('uuid') for meal_data in meals_data if meal_data.get('uuid')}

            for meal_data in meals_data:
                meal_uuid = meal_data.get('uuid')
                meal_type = meal_data.get('meal_type')
                meal_id = meal_data.get('id')
                quantity = meal_data.get('grams') or 0
                unit = meal_data.get('unit', 'GRAMS')

                meal, _ = Meal.objects.get_or_create(id=meal_id)

                if meal_uuid:
                    diet_meal, created = DietMeal.objects.update_or_create(
                        uuid=meal_uuid,
                        defaults={
                            'diet_day': diet_day,
                            'meal_type': meal_type,
                            'meal': meal,
                            'quantity': quantity,
                            'unit': unit
                        }
                    )
                else:
                    diet_meal = DietMeal.objects.create(
                        diet_day=diet_day,
                        meal_type=meal_type,
                        meal=meal,
                        quantity=quantity,
                        unit=unit
                    )

            DietMeal.objects.filter(diet_day=diet_day).exclude(uuid__in=sent_meals_uuids).delete()

            diet_day.save()

        return Response({"message": "Diet days saved successfully."}, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DietPreferencesView(APIView):
    def post(self, request, format=None):
        diet_id = request.data.get('diet_id')
        orderID = request.data.get('orderID')

        if not diet_id:
            return Response(
                {'error': 'diet_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        dieta = get_object_or_404(Dieta, pk=diet_id)

        try:
            zamowienie = Zamowienie.objects.get(id=orderID)
            user_diet = zamowienie.user_diet
            created = False
        except ObjectDoesNotExist:
            user_diet, created = UserDiet.objects.get_or_create(
                user=user,
                dieta=dieta,
                defaults={
                    'diet_type': request.data.get('dietType', 'standard'),
                    'meal_count': request.data.get('mealCount', 3)
                }
            )

        dietary_restrictions = request.data.get('preferences', {})
        preferences_set = request.data.get('preferences_set', False)
        food_preferences = request.data.get('foodPreferences', {})

        meal_Count = request.data.get('mealCount', user_diet.meal_count)
        gender = request.data.get('gender', user_diet.gender)
        age = request.data.get('age', user_diet.age)
        weight = request.data.get('weight', user_diet.weight)
        height = request.data.get('height', user_diet.height)
        activity_level = request.data.get('activity_level', user_diet.activity_level)

        if not created:
            updated_data = request.data.copy()
            updated_data.update(dietary_restrictions)
            updated_data['preferences_set'] = preferences_set
            updated_data['food_preferences'] = food_preferences
            updated_data['meal_count'] = meal_Count
            updated_data['gender'] = gender
            updated_data['age'] = age
            updated_data['weight'] = weight
            updated_data['height'] = height
            updated_data['activity_level'] = activity_level

            serializer = UserDietSerializer(user_diet, data=updated_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                try:
                    zamowienie = Zamowienie.objects.get(id=orderID)
                    zamowienie.status = 'Pending'
                    zamowienie.save()
                    if dieta.id == 1:
                        MealAI(user_diet, zamowienie.duration)
                except Zamowienie.DoesNotExist:
                    pass
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserDietSerializer(user_diet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TrainingSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TrainingSessionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProgressView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Treningi z tego tygodnia
        trainings_this_week = TrainingSession.objects.filter(user=user, date__range=[week_start, week_end])
        num_trainings_this_week = trainings_this_week.count()

        # Ostatnie 3 treningi
        last_three_trainings = TrainingSession.objects.filter(user=user).order_by('-date')[:3]

        # Statystyki ogólne
        total_trainings = TrainingSession.objects.filter(user=user).count()

        # Serializacja danych
        training_sessions_serializer = TrainingSessionSerializer(last_three_trainings, many=True)
        body_measurements_serializer = BodyMeasurementSerializer(BodyMeasurement.objects.filter(user=user), many=True)

        return Response({
            'num_trainings_this_week': num_trainings_this_week,
            'last_three_trainings': training_sessions_serializer.data,
            'total_trainings': total_trainings,
            'body_measurements': body_measurements_serializer.data
        })


class BodyMeasurementList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        measurements = BodyMeasurement.objects.filter(user=request.user).order_by('date')
        serializer = BodyMeasurementSerializer(measurements, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        existing_measurement = BodyMeasurement.objects.filter(
            user=request.user,
            date=request.data.get('date')
        ).first()

        if existing_measurement:
            return Response(
                {'error': 'A measurement for this date already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BodyMeasurementSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BodyMeasurementDetail(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = BodyMeasurement.objects.all()
    serializer_class = BodyMeasurementSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class TrainingsList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        training_sessions = TrainingSession.objects.filter(user=request.user).order_by('date')
        serializer = TrainingSessionSerializer(training_sessions, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        existing_measurement = BodyMeasurement.objects.filter(
            user=request.user,
            date=request.data.get('date')
        ).first()

        if existing_measurement:
            return Response(
                {'error': 'A measurement for this date already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BodyMeasurementSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TrainingStart(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_date = timezone.now()
        training_session = TrainingSession.objects.create(user=request.user, date=current_date)
        serializer = TrainingSessionSerializer(training_session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def add_exercise_to_training_session(request, training_id):
    try:
        training_session = TrainingSession.objects.get(id=training_id)
    except TrainingSession.DoesNotExist:
        return Response({'error': 'Training session not found'}, status=status.HTTP_404_NOT_FOUND)

    exercise_data = request.data
    serializer = ExerciseSerializer(data=exercise_data)
    if serializer.is_valid():
        exercise = serializer.save(training_session=training_session)
        return Response(ExerciseSerializer(exercise).data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def MealAIResponse(request):

    data = request.data
    print("OTRZYMANO DANE Z FASTAPI")
    user_id = data.get('user_id')
    user_diet = data.get('user_diet')
    diet_plan = data.get('diet_plan')

    if not user_id or not diet_plan:
        return Response({"error": "Niekompletne dane."}, status=400)

    process_diet_plan(user_id, user_diet, diet_plan)

    return Response({"message": "Dane otrzymane i przetworzone"})


def process_diet_plan(user_id, user_diet, diet_plan):
    print("[PROCESSING]")

    new_diet = UserDiet.objects.get(id=user_diet)

    for day in diet_plan:
        date = day['date']
        total_calories = day['total_calories']
        diet_day = DietDay.objects.create(user_diet=new_diet, date=date)

        for meal_data in day['meals']:
            meal_name = meal_data['name']
            meal_query = Meal.objects.filter(name=meal_name)

            if meal_query.exists():
                meal = meal_query.first()

                quantity = meal_data['portions'] * 100
                meal_type = meal_data['meal_type']

                DietMeal.objects.create(
                    meal=meal,
                    diet_day=diet_day,
                    meal_type=meal_type,
                    quantity=quantity,
                    unit=MeasurementUnit.GRAMS
                )
            else:
                print(f"No meal found with name: {meal_name}")
    zamowienie = Zamowienie.objects.get(user_diet=new_diet)
    zamowienie.status = "Completed"
    zamowienie.save()


def calculate_caloric_needs(user_diet):
    gender = user_diet.gender
    age = user_diet.age
    weight = user_diet.weight
    height = user_diet.height
    activity_level = user_diet.activity_level

    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    if activity_level == 'low':
        calories = bmr * 1.375
    elif activity_level == 'medium':
        calories = bmr * 1.55
    elif activity_level == 'high':
        calories = bmr * 1.725
    else:
        calories = bmr * 1.9

    return round(calories)
def MealAI(user_diet, duration):
    fastapi_url = 'http://localhost:9000/generate-diet/'
    #fastapi_url = ' http://192.168.1.106:9000/generate-diet/'

    user_id= user_diet.user_id

    # Tworzenie listy alergenów do unikania
    allergens_to_avoid = []
    if user_diet.gluten_free:
        allergens_to_avoid.append('gluten')
    if user_diet.lactose_free:
        allergens_to_avoid.append('laktoza')
    if user_diet.nut_free:
        allergens_to_avoid.append('orzechy')
    if user_diet.fish_free:
        allergens_to_avoid.append('ryby')
    if user_diet.soy_free:
        allergens_to_avoid.append('soja')

    food_preferences = user_diet.food_preferences

    dish_to_ingredients = {
        "Owsianka": ["płatki owsiane"],
        "Jajecznica": ["jajka"],
        "Smoothie": ["jogurt"],
        "Tosty z awokado": ["awokado"],
        "Pierogi": ["farsz pierogowy"],
        "Pizza": ["ciasto na pizzę", "sos pomidorowy"],
        "Spaghetti": ["makaron spaghetti"],
        "Sushi": ["nori"],
        "Sałatka": ["mix sałat"],
        "Zupa pomidorowa": ["pomidory"],
        "Risotto": ["ryż"],
        "Wrapy": ["tortilla"],
        "Owoce": ["owoce"],
        "Orzechy": ["orzechy"],
        "Warzywne paluszki": [],
        "Domowe batoniki": ["płatki owsiane", "orzechy"],
        "Ciasto bananowe": ["banany"],
        "Mus czekoladowy": ["czekolada"],
        "Pudding chia": ["nasiona chia"],
        "Owocowe sorbety": []
    }

    not_preferred_ingredients = []
    for dish, preference in food_preferences.items():
        if preference == 0 and dish in dish_to_ingredients:
            not_preferred_ingredients.extend(dish_to_ingredients[dish])

    data_to_send = {
        "user": user_id,
        "name": user_diet.diet_type,
        "user_diet": user_diet.id,
        "duration": duration,
        "meals_per_day": user_diet.meal_count,
        "not_preferred_ingredients": not_preferred_ingredients,
        "allergens_to_avoid": allergens_to_avoid,
        "max_calories": calculate_caloric_needs(user_diet),
        "user_weight": user_diet.weight,
        "callback_url": "http://localhost:8000/works/fitter/api/mealAIResponse/"


    }

    #"callback_url": "http://192.168.1.106:8000/api/mealAIResponse/"
    #"callback_url": "http://localhost:8000/api/mealAIResponse/"
    # Przesyłanie danych z żądania Django do FastAPI
    try:
        response = requests.post(fastapi_url, json=data_to_send)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return Response({'error': str(e)}, status=500)

    # Przetwarzanie odpowiedzi z serwera FastAPI
    if response.status_code == 200:
        return Response(response.json())
    else:
        return Response({'error': 'Błąd serwera FastAPI'}, status=response.status_code)


class DietIngredientsView(APIView):
    def get(self, request, start_date, end_date):
        user = request.user
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        user_diets = UserDiet.objects.filter(user=user, data_rozpoczecia__lte=end_date,
                                             data_zakonczenia__gte=start_date)
        diet_days = DietDay.objects.filter(user_diet__in=user_diets, date__range=[start_date, end_date])
        diet_meals = DietMeal.objects.filter(diet_day__in=diet_days)

        ingredients = MealIngredient.objects.filter(meal__dietmeal__in=diet_meals).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_quantity=Sum(F('quantity') * F('meal__dietmeal__quantity') / 100)
        )

        serializer = DietIngredientsSerializer({'ingredients': ingredients})
        return Response(serializer.data)


@api_view(['GET'])
def search_exercises(request):
    query = request.GET.get('search', '')
    exercises = Exercise2.objects.filter(name__icontains=query)
    serializer = ExerciseSerializer2(exercises, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_roles(request):
    user = request.user
    if user.is_authenticated:
        roles = [group.name for group in user.groups.all()]
        user_data = {
            'username': user.username,
            'roles': roles,
            'email': user.email,
        }
        return Response(user_data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'User is not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)


def verify_email(request, token):
    try:
        token = EmailVerificationToken.objects.get(token=token)

        # Sprawdź, czy token był już użyty do weryfikacji
        if token.verified:
            return JsonResponse({"message": "E-mail został już zweryfikowany."}, status=200)

        # Sprawdź, czy token nie wygasł
        if token.is_expired:
            return JsonResponse({"message": "Link weryfikacyjny wygasł."}, status=400)

        # Ustaw flagę zweryfikowanego e-maila i zapisz token
        token.user.email_verified = True
        token.user.save()
        token.verified = True
        token.save()
        return JsonResponse({"message": "E-mail zweryfikowany."}, status=200)

    except EmailVerificationToken.DoesNotExist:
        return JsonResponse({"message": "Nieprawidłowy token."}, status=404)


@csrf_exempt
def resend_verification_email(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Nieprawidłowa metoda żądania."}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get('username')
        user = CustomUser.objects.filter(username=username).first()
        if user is None:
            return JsonResponse({"message": "Nie znaleziono użytkownika z tym nickiem."}, status=404)


    except json.JSONDecodeError:
        return HttpResponseBadRequest("Nieprawidłowe dane")

    existing_token = EmailVerificationToken.objects.filter(user=user, verified=False, expires_at__gt=now()).first()
    if existing_token:
        return JsonResponse({"message": "Link weryfikacyjny już został wysłany i jest nadal aktualny."}, status=400)

    EmailVerificationToken.objects.filter(user=user, verified=False).delete()

    token = EmailVerificationToken.objects.create(user=user)
    message_html = render_to_string('email_verification.html', {'token': token.token})

    send_mail(
        '[Fitter] Weryfikacja konta',
        f'',
        'fitterauth@gmail.com',
        [user.email],
        html_message=message_html,

        fail_silently=False,
    )
    return JsonResponse({"message": "Link weryfikacyjny został ponownie wysłany."}, status=200)


User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not user.check_password(old_password):
        return Response({'error': 'Niepoprawne stare hasło'}, status=400)

    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response({'error': str(e)}, status=400)

    user.set_password(new_password)
    user.save()
    return Response({'success': 'Hasło zmienione pomyślnie'})
