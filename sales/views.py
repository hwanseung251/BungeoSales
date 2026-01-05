from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta, date
from collections import defaultdict
import pytz
from .models import Item, Ingredient, RecipeComponent, SalesDay, SalesCount, SalesEvent, TimerLog


@login_required
def today_sales(request):
    """오늘 판매 화면 (핵심)"""
    today = date.today()
    sales_day, created = SalesDay.objects.get_or_create(
        user=request.user,
        date=today
    )

    items = Item.objects.filter(user=request.user, is_active=True)
    items_with_counts = []

    for item in items:
        count, _ = SalesCount.objects.get_or_create(
            sales_day=sales_day,
            item=item
        )
        items_with_counts.append({
            'item': item,
            'count': count
        })

    context = {
        'sales_day': sales_day,
        'items_with_counts': items_with_counts,
        'total_qty': sales_day.get_total_qty(),
        'total_revenue': sales_day.get_total_revenue(),
        'total_cost': sales_day.get_total_material_cost(),
        'total_margin': sales_day.get_total_margin(),
    }

    return render(request, 'sales/today_sales.html', context)


@login_required
def add_sale(request, item_id, delta):
    """판매 추가 (AJAX) - 현재 페이지의 날짜에 기록"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    item = get_object_or_404(Item, id=item_id, user=request.user)

    # 요청에서 날짜 받기 (없으면 오늘)
    date_str = request.POST.get('date')
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = date.today()

    with transaction.atomic():
        sales_day, _ = SalesDay.objects.get_or_create(
            user=request.user,
            date=target_date
        )

        sales_count, _ = SalesCount.objects.get_or_create(
            sales_day=sales_day,
            item=item
        )

        sales_count.qty_units += delta
        sales_count.save()

        SalesEvent.objects.create(
            sales_day=sales_day,
            item=item,
            delta=delta
        )

    sales_day.refresh_from_db()

    return JsonResponse({
        'success': True,
        'item_qty': sales_count.qty_units,
        'item_revenue': float(sales_count.revenue),
        'item_margin': float(sales_count.margin),
        'total_qty': sales_day.get_total_qty(),
        'total_revenue': float(sales_day.get_total_revenue()),
        'total_cost': float(sales_day.get_total_material_cost()),
        'total_margin': float(sales_day.get_total_margin()),
    })


@login_required
def undo_sale(request, item_id, delta):
    """판매 취소 (UNDO) - 최근 이벤트를 되돌림"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    item = get_object_or_404(Item, id=item_id, user=request.user)

    # 요청에서 날짜 받기 (없으면 오늘)
    date_str = request.POST.get('date')
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = date.today()

    # delta는 양수로 들어옴 (예: 1, 3)
    with transaction.atomic():
        try:
            sales_day = SalesDay.objects.get(user=request.user, date=target_date)
            sales_count = SalesCount.objects.get(sales_day=sales_day, item=item)
        except (SalesDay.DoesNotExist, SalesCount.DoesNotExist):
            return JsonResponse({'error': '판매 데이터가 없습니다'}, status=400)

        if sales_count.qty_units < delta:
            return JsonResponse({'error': '판매 개수가 부족합니다'}, status=400)

        # 최근 이벤트부터 거꾸로 되돌림
        remaining = delta
        events = SalesEvent.objects.filter(
            sales_day=sales_day,
            item=item,
            delta__gt=0
        ).order_by('-created_at')

        for event in events:
            if remaining <= 0:
                break

            if event.delta <= remaining:
                remaining -= event.delta
                event.delete()
            else:
                event.delta -= remaining
                event.save()
                remaining = 0

        # 판매 개수 감소
        sales_count.qty_units -= delta
        sales_count.save()

    sales_day.refresh_from_db()

    return JsonResponse({
        'success': True,
        'item_qty': sales_count.qty_units,
        'item_revenue': float(sales_count.revenue),
        'item_margin': float(sales_count.margin),
        'total_qty': sales_day.get_total_qty(),
        'total_revenue': float(sales_day.get_total_revenue()),
        'total_cost': float(sales_day.get_total_material_cost()),
        'total_margin': float(sales_day.get_total_margin()),
    })


@login_required
def calendar_view(request):
    """달력 화면 (월간)"""
    import json

    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    sales_days = SalesDay.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).prefetch_related('salescount_set__item')

    calendar_data = {}
    for sd in sales_days:
        calendar_data[sd.date.day] = {
            'revenue': float(sd.get_total_revenue()),
            'margin': float(sd.get_total_margin()),
            'qty': sd.get_total_qty()
        }

    context = {
        'year': year,
        'month': month,
        'calendar_data': json.dumps(calendar_data),
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'sales/calendar.html', context)


@login_required
def day_detail(request, year, month, day):
    """일자 상세 (판매 조절 + 분석)"""
    import json

    target_date = date(year, month, day)
    sales_day, created = SalesDay.objects.get_or_create(
        user=request.user,
        date=target_date
    )

    # 품목별 판매 데이터 구조화 (판매 조절 버튼용)
    items = Item.objects.filter(user=request.user, is_active=True)
    items_with_counts = []
    for item in items:
        count, _ = SalesCount.objects.get_or_create(
            sales_day=sales_day,
            item=item
        )
        items_with_counts.append({
            'item': item,
            'count': count
        })

    # 시간대별 판매 분포
    events = SalesEvent.objects.filter(sales_day=sales_day).select_related('item')
    korea_tz = pytz.timezone('Asia/Seoul')
    time_distribution = defaultdict(int)
    for event in events:
        if event.delta > 0:
            # UTC로 저장된 시간을 한국 시간으로 변환
            local_time = event.created_at.astimezone(korea_tz)
            hour = local_time.hour
            minute = (local_time.minute // 10) * 10
            time_key = f"{hour:02d}:{minute:02d}"
            time_distribution[time_key] += event.delta

    time_data = sorted(time_distribution.items())

    # 재료 소모량 계산
    sales_counts = SalesCount.objects.filter(sales_day=sales_day).select_related('item')
    ingredient_usage = defaultdict(lambda: {'grams': 0, 'cost': 0})
    for sc in sales_counts:
        for recipe in sc.item.recipecomponent_set.all():
            ing_name = recipe.ingredient.name
            total_grams = float(recipe.grams_per_unit) * sc.qty_units
            ingredient_usage[ing_name]['grams'] += total_grams
            ingredient_usage[ing_name]['cost'] += total_grams * float(recipe.ingredient.cost_per_gram)

    context = {
        'sales_day': sales_day,
        'items_with_counts': items_with_counts,
        'total_qty': sales_day.get_total_qty(),
        'total_revenue': sales_day.get_total_revenue(),
        'total_cost': sales_day.get_total_material_cost(),
        'total_margin': sales_day.get_total_margin(),
        'time_data': json.dumps(time_data),
        'ingredient_usage': dict(ingredient_usage),
    }

    return render(request, 'sales/day_detail.html', context)


@login_required
def dashboard(request):
    """기간 분석 대시보드"""
    period = request.GET.get('period', 'today')

    today = date.today()

    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'all':
        start_date = None
        end_date = None
    else:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date = today
            end_date = today

    sales_days_query = SalesDay.objects.filter(user=request.user)
    if start_date:
        sales_days_query = sales_days_query.filter(date__gte=start_date)
    if end_date:
        sales_days_query = sales_days_query.filter(date__lte=end_date)

    sales_days = sales_days_query.prefetch_related('salescount_set__item')

    total_revenue = sum(sd.get_total_revenue() for sd in sales_days)
    total_margin = sum(sd.get_total_margin() for sd in sales_days)
    total_cost = sum(sd.get_total_material_cost() for sd in sales_days)

    item_stats = defaultdict(lambda: {'qty': 0, 'revenue': 0})
    for sd in sales_days:
        for sc in sd.salescount_set.all():
            item_stats[sc.item.name]['qty'] += sc.qty_units
            item_stats[sc.item.name]['revenue'] += float(sc.revenue)

    events_query = SalesEvent.objects.filter(sales_day__in=sales_days, delta__gt=0)

    # 한국 시간대로 변환
    korea_tz = pytz.timezone('Asia/Seoul')
    time_distribution = defaultdict(int)
    for event in events_query:
        # UTC로 저장된 시간을 한국 시간으로 변환
        local_time = event.created_at.astimezone(korea_tz)
        hour = local_time.hour
        minute = (local_time.minute // 10) * 10
        time_key = f"{hour:02d}:{minute:02d}"
        time_distribution[time_key] += event.delta

    time_data = sorted(time_distribution.items())

    ingredient_usage = defaultdict(lambda: {'grams': 0, 'cost': 0})
    for sd in sales_days:
        for sc in sd.salescount_set.all():
            for recipe in sc.item.recipecomponent_set.all():
                ing_name = recipe.ingredient.name
                total_grams = float(recipe.grams_per_unit) * sc.qty_units
                ingredient_usage[ing_name]['grams'] += total_grams
                ingredient_usage[ing_name]['cost'] += total_grams * float(recipe.ingredient.cost_per_gram)

    import json

    context = {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_margin': total_margin,
        'total_cost': total_cost,
        'item_stats': json.dumps(dict(item_stats)),
        'time_data': json.dumps(time_data),
        'ingredient_usage': dict(ingredient_usage),
    }

    return render(request, 'sales/dashboard.html', context)


@login_required
def setup_items(request):
    """품목 설정"""
    if request.method == 'POST':
        name = request.POST.get('name')
        bundle_size = request.POST.get('bundle_size')
        bundle_price = request.POST.get('bundle_price')

        Item.objects.create(
            user=request.user,
            name=name,
            bundle_size=bundle_size,
            bundle_price=bundle_price
        )
        return redirect('setup_items')

    items = Item.objects.filter(user=request.user)
    return render(request, 'sales/setup_items.html', {'items': items})


@login_required
def setup_ingredients(request):
    """재료 설정"""
    if request.method == 'POST':
        name = request.POST.get('name')
        cost_per_gram = request.POST.get('cost_per_gram')

        Ingredient.objects.create(
            user=request.user,
            name=name,
            cost_per_gram=cost_per_gram
        )
        return redirect('setup_ingredients')

    ingredients = Ingredient.objects.filter(user=request.user)
    return render(request, 'sales/setup_ingredients.html', {'ingredients': ingredients})


@login_required
def setup_recipes(request):
    """레시피 설정"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        ingredient_id = request.POST.get('ingredient_id')
        grams_per_unit = request.POST.get('grams_per_unit')

        item = get_object_or_404(Item, id=item_id, user=request.user)
        ingredient = get_object_or_404(Ingredient, id=ingredient_id, user=request.user)

        RecipeComponent.objects.update_or_create(
            item=item,
            ingredient=ingredient,
            defaults={'grams_per_unit': grams_per_unit}
        )
        return redirect('setup_recipes')

    items = Item.objects.filter(user=request.user).prefetch_related('recipecomponent_set__ingredient')
    ingredients = Ingredient.objects.filter(user=request.user)

    return render(request, 'sales/setup_recipes.html', {
        'items': items,
        'ingredients': ingredients
    })


@login_required
def timer_view(request):
    """타이머 화면"""
    return render(request, 'sales/timer.html')


def login_view(request):
    """로그인"""
    from django.contrib.auth import authenticate, login

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            return render(request, 'sales/login.html', {'error': '아이디 또는 비밀번호가 잘못되었습니다.'})

    return render(request, 'sales/login.html')


def signup_view(request):
    """회원가입"""
    from django.contrib.auth.models import User
    from django.contrib.auth import login

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            return render(request, 'sales/signup.html', {'error': '비밀번호가 일치하지 않습니다.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'sales/signup.html', {'error': '이미 존재하는 아이디입니다.'})

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('/')

    return render(request, 'sales/signup.html')


def logout_view(request):
    """로그아웃"""
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')
