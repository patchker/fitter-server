from django.contrib import admin
from inz_server.models import Zamowienie, Dieta, CustomUser, DietDay, Meal, UserDiet, DietMeal, Ingredient, \
    MealIngredient, TrainingSession, ExerciseSeries, Exercise, BodyMeasurement, Exercise2, EmailVerificationToken

admin.site.register(Zamowienie)
admin.site.register(CustomUser)
admin.site.register(Dieta)
admin.site.register(DietDay)
admin.site.register(Meal)
admin.site.register(UserDiet)
admin.site.register(DietMeal)
admin.site.register(Ingredient)
admin.site.register(MealIngredient)
admin.site.register(TrainingSession)
admin.site.register(ExerciseSeries)
admin.site.register(Exercise)
admin.site.register(BodyMeasurement)
admin.site.register(Exercise2)
admin.site.register(EmailVerificationToken)
