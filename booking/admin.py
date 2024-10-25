from django.contrib import admin

from .models import (
    WeeklySession,
    WeeklySessionHistory,
    SessionRegistration,
    SessionRegistrationHistory,
    GlobalSetting,
)


admin.site.register(WeeklySession)
admin.site.register(WeeklySessionHistory)
admin.site.register(SessionRegistration)
admin.site.register(SessionRegistrationHistory)
admin.site.register(GlobalSetting)
