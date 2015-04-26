from django.contrib import admin
from crowdfunding.models import Project, Pledge, ProjectImage, ProjectUpdate
# Register your models here.


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    fields = ('image', 'show_thumbnail')
    readonly_fields = ('show_thumbnail',)


class ProjectUpdate(admin.TabularInline):
    model = ProjectUpdate
    fields = ('author', 'update')


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'goal', 'days_remaining')
    inlines = (ProjectImageInline, ProjectUpdate,)
    search_fields = ('title',)


admin.site.register(Project, ProjectAdmin)
admin.site.register(Pledge)