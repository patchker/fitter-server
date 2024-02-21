from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from inz_server.models import Zamowienie, Dieta, BodyMeasurement, Ingredient, Exercise2
from .models import EmailVerificationToken
from .models import TrainingSession, Exercise, ExerciseSeries
from .models import UserDiet


class CustomAuthenticationFailed(AuthenticationFailed):
    default_detail = "Nie znaleziono aktywnego konta z podanymi danymi uwierzytelniającymi."


class EmailNotVerified(AuthenticationFailed):
    default_detail = "E-mail niezweryfikowany"


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Czy dane uwierzytelniające są prawidłowe
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise CustomAuthenticationFailed()

        # Czy e-mail jest zweryfikowany
        try:
            verification_token = EmailVerificationToken.objects.get(user=self.user, verified=True)
        except EmailVerificationToken.DoesNotExist:
            raise EmailNotVerified()

        # Jeśli e-mail nie jest zweryfikowany, wyrzuć wyjątek EmailNotVerified
        if not verification_token.verified:
            raise EmailNotVerified()



        user_groups = self.user.groups.all()
        data['roles'] = [group.name for group in user_groups]
        data['isVerified'] = verification_token.verified

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'street', 'city', 'zipCode', 'country']
        extra_kwargs = {'password': {'write_only': True}}

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

    def validate_password(self, value):
        # Długość hasła
        min_length = 8
        if len(value) < min_length:
            raise serializers.ValidationError(f"Hasło musi mieć przynajmniej {min_length} znaków.")
        return value

    def validate(self, data):
        # Zgodność haseł
        request = self.context.get('request')
        if request and 'confirm_password' in request.data:
            confirm_password = request.data['confirm_password']
            if data['password'] != confirm_password:
                raise serializers.ValidationError("Hasła nie są zgodne.")
        return data

    def validate_username(self, value):
        # Sprawdź, czy użytkownik z takim username już istnieje.
        if self.instance:

            if CustomUser.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("Użytkownik z takim loginem już istnieje.")
        else:
            if CustomUser.objects.filter(username=value).exists():
                raise serializers.ValidationError("Użytkownik z takim loginem już istnieje.")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)

        token = EmailVerificationToken.objects.create(user=user)
        message_html = render_to_string('email_verification.html', {'token': token.token})

        send_mail(
            '[Fitter] Weryfikacja konta',
            f'',
            'twojemail@email.com',
            [user.email],
            html_message=message_html,

            fail_silently=False,
        )
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class DietaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dieta
        fields = '__all__'


class ZamowienieSerializer(serializers.ModelSerializer):
    dieta = DietaSerializer()

    class Meta:
        model = Zamowienie
        fields = '__all__'
class OrderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='uzytkownik.username', read_only=True)

    class Meta:
        model = Zamowienie
        fields = ['id', 'dieta', 'duration', 'data_rozpoczecia', 'data_zakonczenia', 'status', 'uzytkownik', 'user_diet', 'username']


from rest_framework import serializers
from .models import CustomUser, Zamowienie


class ZamowienieSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Zamowienie
        fields = '__all__'


class UserSerializer2(serializers.ModelSerializer):
    zamowienia = ZamowienieSerializer2(source='zamowienie_set', many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'street',
                  'city', 'zipCode', 'country', 'zamowienia')


class UserDietSerializer(serializers.ModelSerializer):
    diet_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserDiet
        fields = [
            'id', 'user', 'diet_id', 'data_rozpoczecia', 'data_zakonczenia',
            'diet_type', 'meal_count', 'gluten_free', 'lactose_free',
            'nut_free', 'fish_free', 'soy_free', 'preferences_set', 'food_preferences', 'gender', 'age', 'weight', 'height', 'activity_level'
        ]
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        diet_id = validated_data.pop('diet_id')
        dieta = get_object_or_404(Dieta, pk=diet_id)
        validated_data['dieta'] = dieta
        return UserDiet.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.diet_type = validated_data.get('diet_type', instance.diet_type)
        instance.preferences_set = validated_data.get('preferences_set', instance.preferences_set)
        instance.food_preferences = validated_data.get('food_preferences', instance.food_preferences)
        instance.gluten_free = validated_data.get('gluten_free', instance.gluten_free)
        instance.lactose_free = validated_data.get('lactose_free', instance.lactose_free)
        instance.nut_free = validated_data.get('nut_free', instance.nut_free)
        instance.fish_free = validated_data.get('fish_free', instance.fish_free)
        instance.soy_free = validated_data.get('soy_free', instance.soy_free)
        instance.meal_count = validated_data.get('meal_count', instance.meal_count)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.age = validated_data.get('age', instance.age)
        instance.weight = validated_data.get('weight', instance.weight)
        instance.height = validated_data.get('height', instance.height)
        instance.activity_level = validated_data.get('activity_level', instance.activity_level)

        if 'diet_id' in validated_data:
            dieta = get_object_or_404(Dieta, pk=validated_data['diet_id'])
            instance.dieta = dieta
        instance.save()
        return instance


class ExerciseSeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseSeries
        fields = ['weight', 'repetitions']


class ExerciseSerializer(serializers.ModelSerializer):
    series = ExerciseSeriesSerializer(many=True)

    class Meta:
        model = Exercise
        fields = ['name', 'series']

    def create(self, validated_data):
        series_data = validated_data.pop('series')
        exercise = Exercise.objects.create(**validated_data)
        for series_datum in series_data:
            ExerciseSeries.objects.create(exercise=exercise, **series_datum)
        return exercise


class TrainingSessionSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True)

    class Meta:
        model = TrainingSession
        fields = ['id', 'date', 'notes', 'exercises']

    def create(self, validated_data):
        user = self.context['request'].user
        exercises_data = validated_data.pop('exercises')
        training_session = TrainingSession.objects.create(user=user, **validated_data)

        for exercise_data in exercises_data:
            series_data = exercise_data.pop('series')
            exercise = Exercise.objects.create(training_session=training_session, **exercise_data)
            for series in series_data:
                ExerciseSeries.objects.create(exercise=exercise, **series)

        return training_session

    def update(self, instance, validated_data):
        return instance


class CustomDecimalField(serializers.DecimalField):
    def to_representation(self, value):
        value = super().to_representation(value)
        return value.rstrip('0').rstrip('.') if '.' in value else value


class BodyMeasurementSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    waist = CustomDecimalField(max_digits=5, decimal_places=2, required=False)
    chest = CustomDecimalField(max_digits=5, decimal_places=2, required=False)
    bicep = CustomDecimalField(max_digits=5, decimal_places=2, required=False)
    thigh = CustomDecimalField(max_digits=5, decimal_places=2, required=False)

    class Meta:
        model = BodyMeasurement
        fields = ['id', 'user', 'date', 'waist', 'chest', 'bicep', 'thigh']

    def create(self, validated_data):
        user = self.context['request'].user
        return BodyMeasurement.objects.create(user=user, **validated_data)


class IngredientAmountSerializer(serializers.Serializer):
    ingredient__name = serializers.CharField(max_length=100)
    total_quantity = serializers.DecimalField(max_digits=6, decimal_places=2)
    ingredient__measurement_unit = serializers.CharField(max_length=3)

    class Meta:
        model = Ingredient
        fields = ['name', 'total_quantity', 'measurement_unit']


class DietIngredientsSerializer(serializers.Serializer):
    ingredients = IngredientAmountSerializer(many=True)


class ExerciseSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Exercise2
        fields = ['name', 'description']
