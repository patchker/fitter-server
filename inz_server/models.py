import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    street = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    zipCode = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.username


def default_expires_at():
    return timezone.now() + timedelta(minutes=15)


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(default=default_expires_at)

    verified = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return not self.verified and timezone.now() > self.expires_at


class Dieta(models.Model):
    nazwa = models.CharField(max_length=100)
    opis = models.TextField()
    cena = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nazwa


class Meal(models.Model):
    name = models.CharField(max_length=100)
    short_description = models.TextField(default='')
    long_description = models.TextField(default='')
    preparation_time = models.IntegerField(default=0)
    calories = models.IntegerField(default=0)
    calories_per_100g = models.IntegerField(default=0)
    default_grams = models.IntegerField(default=0)
    protein = models.IntegerField(default=0)
    fats = models.IntegerField(default=0)
    carbohydrates = models.IntegerField(default=0)
    image_url = models.CharField(max_length=500, blank=True, null=True)
    lactose = models.BooleanField(default=False)
    nut = models.BooleanField(default=False)
    soy = models.BooleanField(default=False)
    gluten = models.BooleanField(default=False)
    fish = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class MeasurementUnit(models.TextChoices):
    GRAMS = 'g', 'Grams'
    PIECES = 'szt', 'Sztuki'
    ML = 'ml', 'Milliliters'


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    measurement_unit = models.CharField(max_length=3, choices=MeasurementUnit.choices, default=MeasurementUnit.GRAMS)
    amount = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return self.name


class MealIngredient(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.ingredient.name} in {self.meal.name}"


class UserDiet(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    dieta = models.ForeignKey('Dieta', on_delete=models.CASCADE)
    data_rozpoczecia = models.DateTimeField(default=timezone.now)
    data_zakonczenia = models.DateTimeField(null=True, blank=True)
    diet_type = models.CharField(max_length=50, default='standard')
    meal_count = models.PositiveSmallIntegerField(default=3)
    gluten_free = models.BooleanField(default=False)
    lactose_free = models.BooleanField(default=False)
    nut_free = models.BooleanField(default=False)
    fish_free = models.BooleanField(default=False)
    soy_free = models.BooleanField(default=False)
    preferences_set = models.BooleanField(default=False)
    food_preferences = models.JSONField(default=dict)
    gender = models.CharField(max_length=50, default='male')
    age = models.IntegerField(default=0)
    weight = models.FloatField(default=0)
    height = models.IntegerField(default=0)
    activity_level = models.CharField(max_length=50, default='medium')

    def __str__(self):
        return f"{self.user.id}-{self.user.username} - {self.dieta.nazwa}"

    def get_preferences_by_value(self, value):
        return [pref for pref, status in self.food_preferences.items() if status == value]

    def set_preferences(self, diet_type, meal_count, preferences, gender, age, weight, height, activity_level):
        self.diet_type = diet_type
        self.meal_count = meal_count
        self.gluten_free = preferences.get('glutenFree', False)
        self.lactose_free = preferences.get('lactoseFree', False)
        self.nut_free = preferences.get('nutFree', False)
        self.fish_free = preferences.get('fishFree', False)
        self.soy_free = preferences.get('soyFree', False)
        self.preferences_set = True
        self.gender = gender
        self.age = age
        self.weight = weight
        self.height = height
        self.activity_level = activity_level
        self.save()


class DietMeal(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    diet_day = models.ForeignKey('DietDay', on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=3, choices=MeasurementUnit.choices, default=MeasurementUnit.GRAMS)

    def __str__(self):
        return f"{self.meal.name} - {self.meal_type} - {self.uuid}"


class DietDay(models.Model):
    user_diet = models.ForeignKey(UserDiet, on_delete=models.CASCADE)
    date = models.DateField()
    meals = models.ManyToManyField(Meal, through=DietMeal)

    def __str__(self):
        return f"{self.user_diet.user.username} - {self.date}"


class Zamowienie(models.Model):
    uzytkownik = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    dieta = models.ForeignKey('Dieta', on_delete=models.CASCADE, null=True, blank=True)
    user_diet = models.ForeignKey('UserDiet', on_delete=models.CASCADE, null=True, blank=True)
    duration = models.IntegerField(default=0)
    data_rozpoczecia = models.DateTimeField(default=timezone.now)
    data_zakonczenia = models.DateTimeField(default=timezone.now)
    STATUS_CHOICES = [
        ('new', 'New'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('aipending', '[AI] Pending'),
        ('aicompleted', '[AI] Completed'),
    ]
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Zamowienie {self.id} - Uzytkownik: {self.uzytkownik.username} - Dieta: {self.dieta.nazwa if self.dieta else 'Brak'}"

    def clean(self):
        super().clean()


class TrainingSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateTimeField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user}'s training session on {self.date}"


class Exercise(models.Model):
    training_session = models.ForeignKey(TrainingSession, related_name='exercises', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} in session {self.training_session.id}"


class ExerciseSeries(models.Model):
    exercise = models.ForeignKey(Exercise, related_name='series', on_delete=models.CASCADE)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    repetitions = models.IntegerField()

    def __str__(self):
        return f"{self.repetitions} reps of {self.weight}kg in {self.exercise.name}"


class BodyMeasurement(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateField()
    waist = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # Obwód pasa
    chest = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # Obwód klatki
    bicep = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # Obwód bicepsa
    thigh = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # Obwód uda

    def __str__(self):
        return f"Measurements for {self.user} on {self.date}"


class Exercise2(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
