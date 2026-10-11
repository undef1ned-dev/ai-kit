# Python FastAPI Profile

Профиль для backend-разработки на FastAPI.
Расширяет базовые правила из base/CLAUDE.md.

---

## Стек

| Библиотека | Версия    | Назначение                               |
|---|-----------|------------------------------------------|
| Python | 3.12+     | язык                                     |
| FastAPI | 0.115+    | web-фреймворк                            |
| SQLAlchemy | 2.0 async | ORM (aiosqlite в dev, asyncpg в prod)    |
| Pydantic v2 + pydantic-settings | 2.11+     | схемы и настройки через .env             |
| Alembic | 1.18+     | миграции БД                              |
| python-jose[cryptography] | 3.3+      | JWT                                      |
| httpx | 0.28+     | async HTTP-клиент                        |
| LangGraph + langchain-openai | 1.0+      | мульти-агентная оркестрация (если нужна) |
| sse-starlette | 1.6+      | Server-Sent Events                       |
| pytest + pytest-asyncio | latest    | тесты                                    |
| ruff | latest    | линтер и форматтер                       |
| uvicorn[standard] | 0.32+     | ASGI-сервер                              |
| uv | latest    | управление зависимостями                 |

---

## Архитектура

### Структура проекта
```
backend/                                                                                                                                                                                                  
  ├── main.py              — FastAPI app: middleware, роутеры, lifespan                                                                                                                                     
  ├── .env                 — переменные окружения (не коммитить)                                                                                                                                            
  ├── pyproject.toml       — зависимости + конфиг pytest, ruff, mypy и др.                                                                                                                                  
  ├── uv.lock              — lock-файл зависимостей                                                                                                                                                         
  ├── alembic.ini          — конфигурация Alembic                                                                                                                                                           
  │                                                                                                                                                                                                         
  ├── core/                                                                                                                                                                                                 
  │   ├── config.py        — Pydantic BaseSettings (читает .env)                                                                                                                                            
  │   ├── database.py      — async SQLAlchemy engine, AsyncSession, get_session                                                                                                                             
  │   ├── jwt.py           — create_token / get_current_user                                                                                                                                                
  │   ├── <client>.py      — внешние HTTP-клиенты (gitlab_client и др.)                                                                                                                                     
  │   └── llm_factory.py   — фабрика LLM-моделей (если используется)                                                                                                                                        
  │                                                                                                                                                                                                         
  ├── models/                                                                                                                                                                                               
  │   └── <name>.py        — SQLAlchemy ORM-модели (один файл — одна сущность)                                                                                                                              
  │                                                                                                                                                                                                         
  ├── routers/                                                                                                                                                                                              
  │   └── <name>.py        — APIRouter: endpoint-функции
  ├── schemas/                                                                                                                                                                                                  
  │   └── <name>.py        — Pydantic-схемы (Request/Response)                                                                                                                                                     
  ├── services/                                                                                                                                                                                                 
  │   └── <name>.py        — бизнес-логика                                                                                                                                   
  │                                                                                                                                                                                                         
  ├── agents/              — LangGraph-агенты (если нужны)                                                                                                                                                  
  │   ├── state.py         — TypedDict состояние графа                                                                                                                                                      
  │   ├── graph.py         — компиляция LangGraph-графа                                                                                                                                                     
  │   ├── <name>_agent.py  — узлы графа                                                                                                                                                                     
  │   └── utils.py         — вспомогательные функции                                                                                                                                                        
  │                                                                                                                                                                                                         
  ├── migrations/                                                                                                                                                                                           
  │   ├── env.py           — Alembic environment (async)                                                                                                                                                    
  │   └── versions/        — файлы миграций (YYYYMMDDHHSS_rev_slug.py)                                                                                                                                      
  │                                                                                                                                                                                                         
  └── tests/                                                                                                                                                                                                
      ├── conftest.py      — фикстуры: session, client, auth_client                                                                                                                                         
      └── test_<name>.py   — тесты по роутерам                      
```

### Слои

```
HTTP Request
    │
    ▼
Router function         — Pydantic-валидация входа, вызов сервиса, возврат ответа
    │
    ▼  Depends(get_session), Depends(get_current_user)
    │
    ▼
Service (статичные async-методы)  — бизнес-логика, транзакции
    │
    ▼
SQLAlchemy ORM (select / add / delete)
    │
    ▼
Database (SQLite / PostgreSQL)
```

---

## SQLAlchemy Models

```python
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

class MyModel(Base):
    __tablename__ = "my_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    # Nullable-поле: Optional в типе + nullable=True явно
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # FK — всегда с index=True
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Relationship — с явным lazy чтобы не было случайных sync-запросов
    user: Mapped["User"] = relationship("User", lazy="raise")
```

### Правила
- Стиль SQLAlchemy 2.0: `Mapped[T]` + `mapped_column()`. Никаких `Column()`.
- FK всегда `index=True`
- `relationship()` всегда с `lazy="raise"` — это защита от случайного lazy loading. Грузить связи через `selectinload()` / `joinedload()` в запросе.
- Строки фиксированной длины — `String(N)`, произвольные — `Text`
- Миграции только через Alembic — **никогда вручную**

### Генерация миграции
```bash
alembic revision --autogenerate -m "краткое_описание_на_английском"
alembic upgrade head
```

---

## Pydantic Schemas

```python
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class MyModelCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None

class MyModelUpdate(BaseModel):
    # Все поля Optional — PATCH обновляет только то что передано
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    is_active: bool | None = None

class MyModelResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # обязательно для ORM-объектов
```

### Правила
- Отдельные классы `Create` / `Update` / `Response` — не смешивать
- `model_config = ConfigDict(from_attributes=True)` в каждой Response-схеме
- `Update`-схема: все поля `Optional` + `model_dump(exclude_unset=True)` при применении
- Никаких `from_orm()` — устарел в Pydantic v2, используется `model_validate(obj)`

---

## FastAPI Routers

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session
from core.jwt import get_current_user
from models.user import User
from .service import MyModelService
from .schemas import MyModelCreate, MyModelUpdate, MyModelResponse

router = APIRouter(prefix="/api/my-resource", tags=["my-resource"])


@router.get("/", response_model=list[MyModelResponse])
async def list_items(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[MyModelResponse]:
    return await MyModelService.list(session)


@router.post("/", response_model=MyModelResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: MyModelCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MyModelResponse:
    return await MyModelService.create(session, data, user_id=current_user.id)


@router.get("/{item_id}", response_model=MyModelResponse)
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> MyModelResponse:
    return await MyModelService.get_or_404(session, item_id)


@router.patch("/{item_id}", response_model=MyModelResponse)
async def update_item(
    item_id: int,
    data: MyModelUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> MyModelResponse:
    item = await MyModelService.get_or_404(session, item_id)
    return await MyModelService.update(session, item, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> None:
    item = await MyModelService.get_or_404(session, item_id)
    await MyModelService.delete(session, item)
```

### Правила
- `response_model` обязателен для каждого endpoint
- `status_code` явный: 201 для создания, 204 для удаления
- `Depends(get_current_user)` — там где нужна аутентификация
- Router-функция = валидация + вызов сервиса + возврат. Никакой бизнес-логики.

---

## Service Layer

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from models.my_model import MyModel
from .schemas import MyModelCreate, MyModelUpdate


class MyModelService:
    
    def __init__(self, session: AsyncSession):                                                                                                                                                            
        self.session = session

    async def list(self) -> list[MyModel]:
        result = await self.session.execute(
            select(MyModel)
            .options(selectinload(MyModel.user))  # если нужны связанные объекты
            .order_by(MyModel.id.desc())
        )
        return list(result.scalars().all())

    async def get_or_404(self, item_id: int) -> MyModel:
        result = await self.session.execute(select(MyModel).where(MyModel.id == item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return item

    async def create(self, data: MyModelCreate, user_id: int) -> MyModel:
        item = MyModel(**data.model_dump(), user_id=user_id)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update(self, item: MyModel, data: MyModelUpdate) -> MyModel:
        # exclude_unset=True — обновляем только переданные поля (PATCH-семантика)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: MyModel) -> None:
        await self.session.delete(item)
        await self.session.commit()
```

---

## SQLAlchemy ORM — правила

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# Один объект — scalar_one_or_none()
item = (await session.execute(
    select(MyModel).where(MyModel.id == item_id)
)).scalar_one_or_none()

# Список — scalars().all()
items = (await session.execute(
    select(MyModel)
    .where(MyModel.is_active.is_(True))
    .options(selectinload(MyModel.items))   # загружаем связанные — не lazy
    .order_by(MyModel.created_at.desc())
)).scalars().all()

# Bulk update
from sqlalchemy import update
await session.execute(
    update(MyModel).where(MyModel.status == "old").values(status="new")
)
await session.commit()
```

### Запрещено
- `session.query()` — устаревший стиль, только `select()`
- Обращение к `relationship`-полям без явного `selectinload`/`joinedload` в запросе (с `lazy="raise"` упадёт сразу — это хорошо)
- Запросы в цикле (N+1) — использовать `selectinload` / `joinedload`
- Sync SQLAlchemy в async-контексте

---

## Конфигурация

```python
# core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_url: str = "http://localhost:3000"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str
    jwt_expire_hours: int = 24

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- Все секреты только через `.env` — никакого хардкода
- `extra = "ignore"` — не падать при неизвестных переменных окружения
- Единственный инстанс `settings` на уровне модуля

---

## SSE Streaming

```python
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_session

router = APIRouter()

@router.get("/{run_id}/logs/stream")
async def stream_logs(run_id: int, session: AsyncSession = Depends(get_session)):
    async def generator():
        last_index = 0
        while True:
            logs = await LogService.get_since(session, run_id, last_index)
            for log in logs:
                yield {"data": json.dumps(log)}
                last_index += 1
            if await RunService.is_finished(session, run_id):
                yield {"data": json.dumps({"type": "done"})}
                break
            await asyncio.sleep(0.5)

    return EventSourceResponse(generator())
```

---

## LangGraph Агенты (если используются)

```python
# agents/state.py
from typing import TypedDict, Annotated
from operator import add

class LogEntry(TypedDict):
    ts: str      # ISO timestamp
    agent: str   # имя узла
    level: str   # info | warn | error | success
    message: str

def _merge_lists(a: list, b: list) -> list:
    return a + b

class AgentState(TypedDict):
    run_id: int
    diff: str
    files_changed: list[str]
    # Аккумулируемые поля — reducer обязателен для параллельных веток
    generated_items: Annotated[list[dict], _merge_lists]
    log_lines: Annotated[list[LogEntry], add]
    status: str        # pending | running | completed | failed
    error: str | None


# agents/my_agent.py
from datetime import datetime, timezone
from core.llm_factory import get_llm
from .state import AgentState, LogEntry

async def my_agent_node(state: AgentState) -> dict:
    """Описание узла."""
    llm = get_llm("unit")  # всегда через фабрику, не напрямую

    log: list[LogEntry] = [
        {"ts": datetime.now(timezone.utc).isoformat(), "agent": "my_agent",
         "level": "info", "message": "Начинаю обработку"}
    ]
    try:
        response = await llm.ainvoke([{"role": "user", "content": state["diff"]}])
        log.append({"ts": datetime.now(timezone.utc).isoformat(), "agent": "my_agent",
                    "level": "success", "message": "Завершено"})
        return {"generated_items": [{"content": response.content}], "log_lines": log}
    except Exception as e:
        log.append({"ts": datetime.now(timezone.utc).isoformat(), "agent": "my_agent",
                    "level": "error", "message": str(e)})
        return {"status": "failed", "error": str(e), "log_lines": log}


# agents/graph.py
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from .state import AgentState

def route_from_orchestrator(state: AgentState):
    sends = [Send("my_agent", {**state, "current_file": f}) for f in state["files_changed"]]
    return sends if sends else END

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("my_agent", my_agent_node)
    graph.add_conditional_edges("orchestrator", route_from_orchestrator, ["my_agent", END])
    graph.add_edge("my_agent", END)
    graph.set_entry_point("orchestrator")
    return graph.compile()
```

### Запуск из FastAPI (правильный паттерн)

```python
# ВАЖНО: передавать session из Depends нельзя — она закрывается сразу после
# завершения HTTP-запроса, до окончания background task.
# Background task должен создавать собственную сессию.

from core.database import async_session_factory  # фабрика сессий

async def run_agent_graph(run_id: int) -> None:
    """Фоновая задача создаёт свою сессию независимо от request-scope."""
    async with async_session_factory() as session:
        initial_state = {"run_id": run_id, "status": "running", ...}
        async for chunk in _graph.astream(initial_state):
            await RunService.update_from_chunk(session, run_id, chunk)

@router.post("/{run_id}/start")
async def start_run(run_id: int, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(run_agent_graph, run_id)
    return {"status": "started"}
```

### Правила агентов
- State — только `TypedDict`, аккумулируемые поля с `Annotated` + reducer
- Каждый узел возвращает `dict` только с изменёнными ключами
- Параллельные ветки через `Send()` в conditional edge
- LLM только через фабрику `get_llm()`, не `ChatOpenAI()` напрямую
- Граф компилируется один раз при старте приложения

---

## Правила кода

### Обязательно
- `async/await` везде — никаких sync IO в async-контексте
- Type hints: параметры, возвращаемые значения, поля моделей
- Комментарии и докстринги на русском языке
- Service-слой для бизнес-логики — не в роутерах, не в моделях
- `Depends()` для session и current_user
- `model_dump(exclude_unset=True)` при PATCH

### Запрещено
- Бизнес-логика в router-функциях
- Sync SQLAlchemy в async-контексте
- Хардкод секретов
- `session.query()` — только `select()`
- `from_orm()` — устарел в Pydantic v2
- Передача request-scope сессии БД в BackgroundTasks

---

## Тесты

```python
# pyproject.toml

[tool.pytest.ini_options]
asyncio_mode = "auto"

# tests/conftest.py
  
    import pytest_asyncio
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from main import app
    from core.database import get_session, Base
    from core.jwt import create_token
    from models.user import User

    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    
    @pytest_asyncio.fixture
    async def session():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
          yield s
        await engine.dispose()
    
    
    @pytest_asyncio.fixture
        async def client(session: AsyncSession):
        async def override_session():
          yield session
        
        app.dependency_overrides[get_session] = override_session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
          yield c
        app.dependency_overrides.clear()
    
    
    @pytest_asyncio.fixture
        async def auth_client(client: AsyncClient, session: AsyncSession):
        user = User(gitlab_id=42, username="tester", name="Tester", email="tester@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_token({"sub": str(user.id)})
        client.headers["Authorization"] = f"Bearer {token}"
        return client, user
    
# tests/test_my_resource.py
    from httpx import AsyncClient
    
    
    async def test_list_requires_auth(client: AsyncClient):
        response = await client.get("/api/my-resource/")
        assert response.status_code == 401
    
    
    async def test_list_returns_200(auth_client):
        client, user = auth_client
        response = await client.get("/api/my-resource/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    
    async def test_create_returns_201(auth_client):
        client, user = auth_client
        response = await client.post("/api/my-resource/", json={"name": "Новый объект"})
        assert response.status_code == 201
        assert response.json()["name"] == "Новый объект"
    
    
    async def test_create_validates_required_fields(auth_client):
        client, user = auth_client
        response = await client.post("/api/my-resource/", json={})
        assert response.status_code == 422
    
    
    async def test_get_returns_404_for_missing(auth_client):
        client, user = auth_client
        response = await client.get("/api/my-resource/99999")
        assert response.status_code == 404
    
    
    async def test_patch_updates_partial(auth_client):
        client, user = auth_client
        create_resp = await client.post("/api/my-resource/", json={"name": "Исходный"})
        item_id = create_resp.json()["id"]
        patch_resp = await client.patch(f"/api/my-resource/{item_id}", json={"name": "Обновлённый"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["name"] == "Обновлённый"
    
    
    async def test_delete_returns_204(auth_client):
        client, user = auth_client
        create_resp = await client.post("/api/my-resource/", json={"name": "На удаление"})
        item_id = create_resp.json()["id"]
        assert (await client.delete(f"/api/my-resource/{item_id}")).status_code == 204
        assert (await client.get(f"/api/my-resource/{item_id}")).status_code == 404
```

### Правила тестов
- `pytest-asyncio` + `AsyncClient` с `ASGITransport` — не реальный сервер
- `get_session` переопределяется через `override_session` — генератор, не лямбда (иначе сессия не передаётся корректно)
- `Base` импортируется из `core.database` и используется для создания схемы in-memory
- In-memory SQLite — изолирована для каждой тестовой сессии
- Не добавлять `session` как отдельный параметр в тест если уже используется через `auth_client` — это создаст вторую независимую сессию

---

## Доступные скиллы

- `/new-router` — создать новый FastAPI роутер с CRUD и схемами
- `/add-migration` — сгенерировать и применить Alembic-миграцию
- `/implement-feature` — реализовать фичу через цепочку агентов
