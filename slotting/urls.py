from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),

    path("table/<str:table_key>/", views.table_list, name="table_list"),
    path("table/<str:table_key>/add/", views.table_add, name="table_add"),
    path("table/<str:table_key>/edit/", views.table_edit, name="table_edit"),
    path("table/<str:table_key>/delete/", views.table_delete, name="table_delete"),

    path("run/<str:analysis_key>/", views.analysis_run, name="analysis_run"),
    path("run/<str:analysis_key>/export/", views.analysis_export, name="analysis_export"),

    path("warehouse-map/", views.warehouse_map_view, name="warehouse_map"),
    path("warehouse-map/export/", views.warehouse_map_export, name="warehouse_map_export"),
]
