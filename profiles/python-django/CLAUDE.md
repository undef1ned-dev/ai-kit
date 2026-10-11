# Python Django Profile

Профиль для backend-разработки на Django.
Расширяет базовые правила из base/CLAUDE.md.

---

## Стек

- **Python 3.12+**
- **Django 5.x** — основной фреймворк
- **Django Admin** — административный интерфейс (ключевой компонент, не afterthought)
- **Django REST Framework (DRF)** — REST API
- **django-filter** — фильтрация в API и Admin
- **pytest-django + factory_boy** — тесты
- **uv** — управление зависимостями
- **Celery + Redis** — фоновые задачи (если нужны)
- **django-environ** — настройки через .env

---

## Архитектура

### Структура проекта
```
app/                     — source root приложения
    manage.py
    pyproject.toml
    uv.lock
    
    config/
      settings/
        base.py          — общие настройки
        celery.py        — настройки конкретного сервиса
      urls.py            — подключение роутеров всех приложений
      celery.py          — если используется Celery
    
    apps/
      <app_name>/
        admin.py         — Django Admin конфигурация (ВАЖНО)
        models.py        — модели (или models/)
        views.py         — DRF ViewSets / APIView (или views/)
        serializers.py   — DRF сериализаторы (или serializers/)
        services.py      — бизнес-логика (или services/)
        filters.py       — django-filter классы
        urls.py          — роуты приложения
        tasks.py         — Celery-задачи (если нужны)
        tests/
          test_models.py
          test_services.py
          test_api.py
          factories.py   — factory_boy фабрики
```

### Слои и ответственность
```
URL → ViewSet → Serializer (валидация)
             → Service (бизнес-логика)
             → Model/QuerySet (данные)
Admin → ModelAdmin → Service (переиспользуем ту же логику)
```

---

## Django Модели — правила

### В коде должна быть определена абстрактная модель с датой создания и изменения
```python
class CommonTimeStampedModel(models.Model):
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        abstract = True
```

### Модели должны наследоваться от CommonTimeStampedModel для добавления временных меток
```python
class MyModel(models.Model, CommonTimeStampedModel):
    # у каждого поля должно быть verbose_name на русском языке
    name = models.CharField("Название", max_length=50)
    # нельзя указывать null=True для необязательных текстовых полей для избежания "двух null"
    description = models.TextField("Описание", blank=True)
    # для FK обязательно указывать on_delete и related_name
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="my_models")
    
    # Для каждой модели указывай verbose_name и verbose_name_plural
    class Meta:
        verbose_name = "Модель"
        verbose_name_plural = "Модели"
    
    # Для каждой модели необходимо указывать метод __str__
    def __str__(self):
        return self.name
```
### Файлы миграций запрещено создавать вручную, их необходимо генерировать только с помощью команды
```bash
python manage.py makemigrations
```


## Django Admin — ключевые правила

Admin — это полноценный инструмент, а не заглушка.

### В каждом ModelAdmin должен быть набор настроек
```python
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "user", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "user__email")
    readonly_fields = ("created_at", "updated_at", "id")
    list_select_related = ("user",)         # избегай N+1
    list_per_page = 50
    ordering = ("-created_at",)
```

### Кастомные действия
```python
@admin.action(description="Активировать выбранные")
def activate_items(modeladmin, request, queryset):
    count = queryset.update(is_active=True)
    modeladmin.message_user(request, f"Активировано: {count}", messages.SUCCESS)

    
@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    actions = (activate_items,)
```

### Inline для связанных объектов
```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price", "created_at"]
    can_delete = False

    
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
```

### Fieldsets для организации формы
```python
fieldsets = [
    ("Основное", {"fields": ("name", "status")}),
    ("Контакты", {"fields": ("email", "phone")}),
    ("Служебное", {
        "fields": ("created_at", "updated_at"),
        "classes": ("collapse",),
    }),
]
```

### Кастомные поля в list_display
```python
@admin.display(description="Полное имя", ordering="last_name")
def full_name(self, obj):
    return f"{obj.last_name} {obj.first_name}"
```

---

## Django ORM — правила

```python
# Используй select_related/prefetch_related, когда используются связанные объекты
User.objects.select_related("profile").filter(is_active=True)
Order.objects.prefetch_related("items").all()

# F() и Q() вместо Python-вычислений
from django.db.models import F, Q
Product.objects.filter(Q(stock__gt=0) | Q(allow_backorder=True))
Product.objects.update(price=F("price") * 1.1)

# Только нужные поля
User.objects.only("id", "email", "name")
User.objects.values("id", "email")  # для API без ORM-объектов

# Никогда не делай в цикле запросы к БД
# ❌ for user in users: user.orders.count()
# ✅ annotate + aggregate
```

---

## DRF — правила

```python
# Предпочтительнее использовать просто APIView
class MyListView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        queryset = MyModel.objects.all()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = MySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

# Сериализаторы 
# — предпочтительнее использовать просто Serializer
# — явные поля, не fields = "__all__" или exclude = (id,)
class MySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField()
    content = serializers.CharField()
```

---

## Правила кода

### Обязательно
- Код должен быть поддерживаемым и расширяемым
- Type hints везде
- Докстринги и комментарии к коду должны быть на русском языке
- Service-слой для бизнес-логики (не в views, не в models)
- `select_related` / `prefetch_related` - везде где необходимо получать данные связанных сущностей
- Кастомные менеджеры для сложных QuerySet
- `django-environ` для настроек, никакого хардкода
- Миграции в отдельных коммитах от кода
- `factory_boy` для тестовых данных
- импорты должны быть абсолютными и начинаться с apps: `from apps. ... import ...`

### Запрещено
- Бизнес-логика в views или serializers
- `fields = "__all__"` в сериализаторах
- Сигналы (signals) для бизнес-логики — только для инфраструктурных задач
- Сырые SQL-запросы без `connection.execute` и параметризации
- `filter()` в цикле (вызовет N+1 запросов)

---

## Тесты

```python
# conftest.py
import pytest
from django.test import Client

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def auth_client(api_client, user_factory):
    user = user_factory()
    api_client.force_authenticate(user=user)
    return api_client, user

# factories.py
import factory
from factory.django import DjangoModelFactory

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    is_active = True

# test_api.py
@pytest.mark.django_db
def test_list_users(auth_client):
    client, user = auth_client
    UserFactory.create_batch(3)
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert len(response.data["results"]) >= 3
```

---

## Доступные скиллы

- `/new-app` — создать новое Django-приложение со всей структурой
- `/setup-admin` — настроить расширенный ModelAdmin для существующей модели
- `/implement-feature` — реализовать фичу через цепочку агентов
