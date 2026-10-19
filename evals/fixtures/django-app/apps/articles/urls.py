from django.urls import path

from . import views

urlpatterns = [
    path("", views.article_list),
    path("search/", views.article_search),
    path("<int:article_id>/delete/", views.article_delete),
]
