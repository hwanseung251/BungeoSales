from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, F
from django.utils import timezone


class Item(models.Model):
    """품목 (팥붕, 슈붕, 완붕 등)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="품목명")
    bundle_size = models.IntegerField(default=3, verbose_name="묶음 단위")
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="묶음 가격")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.bundle_size}개 {self.bundle_price}원)"

    @property
    def unit_price(self):
        """개당 단가"""
        return self.bundle_price / self.bundle_size

    def get_material_cost_per_unit(self):
        """1개당 재료비"""
        total_cost = 0
        for recipe in self.recipecomponent_set.all():
            total_cost += recipe.grams_per_unit * recipe.ingredient.cost_per_gram
        return total_cost

    def get_margin_per_unit(self):
        """1개당 순마진"""
        return self.unit_price - self.get_material_cost_per_unit()


class Ingredient(models.Model):
    """재료 (밀가루, 팥앙금, 슈크림, 호두 등)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="재료명")
    cost_per_gram = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="g당 단가")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.cost_per_gram}원/g)"


class RecipeComponent(models.Model):
    """레시피 구성 (품목별 재료 사용량)"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    grams_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="1개당 사용량(g)")

    class Meta:
        unique_together = ['item', 'ingredient']

    def __str__(self):
        return f"{self.item.name} - {self.ingredient.name}: {self.grams_per_unit}g"

    @property
    def cost_per_unit(self):
        """1개당 이 재료의 비용"""
        return self.grams_per_unit * self.ingredient.cost_per_gram


class SalesDay(models.Model):
    """판매일"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="판매일", default=timezone.now)
    memo = models.TextField(blank=True, verbose_name="메모")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    def get_total_revenue(self):
        """총 매출"""
        total = 0
        for count in self.salescount_set.all():
            total += count.qty_units * count.item.unit_price
        return total

    def get_total_material_cost(self):
        """총 재료비"""
        total = 0
        for count in self.salescount_set.all():
            total += count.qty_units * count.item.get_material_cost_per_unit()
        return total

    def get_total_margin(self):
        """총 순마진"""
        return self.get_total_revenue() - self.get_total_material_cost()

    def get_total_qty(self):
        """총 판매개수"""
        return self.salescount_set.aggregate(total=Sum('qty_units'))['total'] or 0


class SalesCount(models.Model):
    """일자-품목 집계"""
    sales_day = models.ForeignKey(SalesDay, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    qty_units = models.IntegerField(default=0, verbose_name="판매개수")

    class Meta:
        unique_together = ['sales_day', 'item']

    def __str__(self):
        return f"{self.sales_day.date} - {self.item.name}: {self.qty_units}개"

    @property
    def revenue(self):
        """매출"""
        return self.qty_units * self.item.unit_price

    @property
    def material_cost(self):
        """재료비"""
        return self.qty_units * self.item.get_material_cost_per_unit()

    @property
    def margin(self):
        """순마진"""
        return self.revenue - self.material_cost


class SalesEvent(models.Model):
    """카운팅 이벤트 로그 (시간대 분석용)"""
    sales_day = models.ForeignKey(SalesDay, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    delta = models.IntegerField(verbose_name="증감량")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="기록시간")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sales_day.date} {self.created_at.time()} - {self.item.name}: {self.delta:+d}"


class TimerLog(models.Model):
    """타이머 로그 (선택적)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    duration_seconds = models.IntegerField(verbose_name="시간(초)")
    timer_type = models.CharField(max_length=20, choices=[
        ('stopwatch', '스톱워치'),
        ('countdown', '카운트다운')
    ])
    started_at = models.DateTimeField(verbose_name="시작시간")
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="완료시간")
    memo = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.duration_seconds}초 ({self.timer_type})"
