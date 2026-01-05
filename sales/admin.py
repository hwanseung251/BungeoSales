from django.contrib import admin
from .models import Item, Ingredient, RecipeComponent, SalesDay, SalesCount, SalesEvent, TimerLog


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'bundle_size', 'bundle_price', 'unit_price', 'is_active', 'user']
    list_filter = ['is_active', 'user']
    search_fields = ['name']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'cost_per_gram', 'user']
    list_filter = ['user']
    search_fields = ['name']


@admin.register(RecipeComponent)
class RecipeComponentAdmin(admin.ModelAdmin):
    list_display = ['item', 'ingredient', 'grams_per_unit', 'cost_per_unit']
    list_filter = ['item', 'ingredient']


@admin.register(SalesDay)
class SalesDayAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'get_total_qty', 'get_total_revenue', 'get_total_margin']
    list_filter = ['user', 'date']
    date_hierarchy = 'date'


@admin.register(SalesCount)
class SalesCountAdmin(admin.ModelAdmin):
    list_display = ['sales_day', 'item', 'qty_units', 'revenue', 'material_cost', 'margin']
    list_filter = ['sales_day', 'item']


@admin.register(SalesEvent)
class SalesEventAdmin(admin.ModelAdmin):
    list_display = ['sales_day', 'item', 'delta', 'created_at']
    list_filter = ['sales_day', 'item', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(TimerLog)
class TimerLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'timer_type', 'duration_seconds', 'started_at', 'completed_at']
    list_filter = ['user', 'timer_type', 'completed_at']
