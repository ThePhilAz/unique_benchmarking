from django.contrib import admin

# Register your models here.

from .models import Configuration, Experiment, GoldenAnswer, AssistantResponse

admin.site.register(Configuration)
admin.site.register(Experiment)
admin.site.register(GoldenAnswer)
admin.site.register(AssistantResponse)
