from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),  # 캘린더를 메인으로
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('add/<int:item_id>/<int:delta>/', views.add_sale, name='add_sale'),
    path('undo/<int:item_id>/<int:delta>/', views.undo_sale, name='undo_sale'),
    path('day/<int:year>/<int:month>/<int:day>/', views.day_detail, name='day_detail'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('setup/items/', views.setup_items, name='setup_items'),
    path('setup/ingredients/', views.setup_ingredients, name='setup_ingredients'),
    path('setup/recipes/', views.setup_recipes, name='setup_recipes'),
    path('timer/', views.timer_view, name='timer'),
]
