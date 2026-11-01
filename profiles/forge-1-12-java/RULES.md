# Forge 1.12.2 Java Profile

Профиль для Java-разработки модов Minecraft 1.12.2 на Forge: код мода, сборка Gradle, тесты, ревью и документация. Модели, текстуры, звуки и анимации в профиль
не входят — их ведёт отдельный профиль ассетов или художник; код только ссылается на ресурсы по ключам и перечисляет, какие ресурсы ему нужны. Расширяет базовые
правила команды.

---

## Стек

- **Java 8** — уровень языка 8: без `var`, `record`, switch-выражений, `List.of`, текстовых блоков
- **Minecraft 1.12.2**, **Forge 14.23.5.2860** (последняя сборка для 1.12.2)
- **ForgeGradle 3** (официальный MDK: `apply plugin: 'net.minecraftforge.gradle'`, зависимость `minecraft 'net.minecraftforge:forge:1.12.2-14.23.5.2860'`, блок
  `runs`) или **ForgeGradle 2.3** в старых проектах (`net.minecraftforge.gradle.forge`, блок `minecraft { version … }`); **Gradle 4.9** через wrapper
  (`./gradlew`); оба работают только на JDK 8
- **Маппинги MCP — из `build.gradle` проекта**, от них зависят имена методов: в MDK `snapshot_20171003-1.12` — `setUnlocalizedName`/`getUnlocalizedName`, в
  `stable_39` — `setTranslationKey`/`getTranslationKey`. Имена методов бери из маппингов и существующего кода проекта, не из примеров в интернете
- **JUnit 4** + **Mockito** — unit-тесты (JUnit 5 — только если в `build.gradle` уже есть `useJUnitPlatform()`, Gradle 4.6+)
- **Логирование** — `org.apache.logging.log4j.Logger` из `FMLPreInitializationEvent#getModLog()`
- **Checkstyle 8.45.1** — правила профиля в `config/checkstyle/checkstyle.xml` (последняя ветка Checkstyle на Java 8); подключает `forge-1-12-setup-checkstyle`

Команды профиля (`.aikit/profiles.json`): `install` — `./gradlew compileJava` (первая сборка готовит декомпилированный Minecraft; в ForgeGradle 2.3 исходники
для IDE дополнительно даёт `./gradlew setupDecompWorkspace`, в ForgeGradle 3 задачи `setupDecompWorkspace` нет), `lint` — `./gradlew compileJava check -x test`
(компиляция и, если подключён, Checkstyle — `forge-1-12-setup-checkstyle`; без него это только компиляция), `test`, `build` (jar в `build/libs/`), `run` —
`./gradlew runClient`.

---

## Архитектура

### Типичная структура проекта

```text
build.gradle
gradle.properties
src/main/java/com/example/examplemod/
  ExampleMod.java              — @Mod: modid, версия, события жизненного цикла, @SidedProxy
  ModConstants.java            — MOD_ID, NAME, VERSION, общие константы
  proxy/                       — CommonProxy, ClientProxy (только клиентская инициализация)
  init/                        — ModBlocks, ModItems, ModEntities, ModSounds: регистрация через RegistryEvent.Register и @ObjectHolder
  block/  item/  entity/       — игровые классы-адаптеры: тонкие, делегируют логику в domain/
  tileentity/                  — TileEntity: состояние блока, NBT, синхронизация
  capability/                  — интерфейсы capability, реализации, Storage, Provider
  inventory/                   — Container, GuiHandler (IGuiHandler)
  network/                     — ModNetwork (SimpleNetworkWrapper) и сообщения IMessage + IMessageHandler
  command/                     — команды CommandBase
  config/                      — ModConfig (@Config)
  event/                       — обработчики событий (@Mod.EventBusSubscriber)
  domain/                      — чистая логика мода без импортов net.minecraft: правила, расчёты, модели данных
  client/                      — рендереры, GUI, регистрация моделей (ModelRegistryEvent) — только Side.CLIENT
src/main/resources/
  mcmod.info
  assets/<modid>/lang/en_us.lang — ключи перевода, которые добавляет код
  assets/<modid>/...           — blockstates, models, textures, sounds: зона профиля ассетов
src/test/java/com/example/examplemod/
docs/                          — документация мода (forge-1-12-java-doc-writer)
```

### Слои

```text
@Mod и proxy → регистрация (init/) → игровые адаптеры (block/item/entity/tileentity/event/command) → domain (чистая Java)
Клиент: GUI/рендер → пакет на сервер → серверный обработчик (проверка) → domain → изменение мира → синхронизация клиенту
```

### Стороны (sides)

- **Логическая сторона** — `world.isRemote`: `true` — клиент, `false` — сервер. Любое изменение мира, инвентаря, NBT — только на логическом сервере.
- **Физическая сторона** — клиентский jar или выделенный сервер. Классы `net.minecraft.client.*` (`Minecraft`, `GuiScreen`, рендереры) есть только на клиенте:
  их трогают только из `ClientProxy`, `client/` и обработчиков с `@Mod.EventBusSubscriber(value = Side.CLIENT)`. Иначе выделенный сервер падает с
  `NoClassDefFoundError`.
- `@SideOnly(Side.CLIENT)` — только на переопределениях клиентских методов vanilla, не способ «спрятать» свой код.
- Обработчик пакета работает в сетевом потоке: работа с миром — через `addScheduledTask` у `WorldServer` игрока (или `Minecraft` на клиенте).
- **Мод работает на выделенном сервере.** Клиент и сервер должны грузить один и тот же jar; исключение — мод, явно объявленный клиентским:
  `@Mod(clientSideOnly = true)` и никакой серверной логики (блоков, предметов, пакетов, сохранённых данных). Серверный мод без клиентской части —
  `acceptableRemoteVersions = "*"` только если клиенту он действительно не нужен.

### Динамическая экспертиза агентов

- `init/`, `@ObjectHolder`, `RegistryEvent` — режим регистрации: всё через события реестра, имена `modid:name` в нижнем регистре, `setRegistryName` + ключ
  перевода (`setUnlocalizedName` или `setTranslationKey` — по маппингам проекта)
- `block/**` — режим блока: `IBlockState` и свойства, `getMetaFromState`/`getStateFromMeta` (не больше 16 состояний в мете), `hasTileEntity`, коллизии,
  `onBlockActivated` меняет мир только на сервере
- `item/**` — режим предмета: `ItemStack.EMPTY` вместо `null`, NBT стека, `onItemRightClick` и `ActionResult`, стакаемость
- `tileentity/**` — режим TileEntity: `readFromNBT`/`writeToNBT`, `markDirty`, `getUpdatePacket`/`getUpdateTag`, `ITickable` с троттлингом, capability
- `entity/**` — режим сущности: `EntityDataManager`, AI-задачи, регистрация `EntityEntryBuilder`, спавн только на сервере
- `capability/**` — режим capability: интерфейс + реализация по умолчанию + `IStorage` + `ICapabilitySerializable`, копирование при `PlayerEvent.Clone`
- `network/**` — режим сети: сервер не доверяет клиенту, проверка всех полей, `addScheduledTask`, лимиты размеров
- `command/**` — режим команды: `getRequiredPermissionLevel`, разбор аргументов через `CommandBase.parse*`, `WrongUsageException`
- `config/**` — режим конфига: `@Config`, `@Config.RangeInt`/`RangeDouble`, `@Config.Comment`, `ConfigManager.sync` по `OnConfigChangedEvent`
- `client/**`, `ClientProxy` — режим клиента: только клиентские классы, регистрация моделей в `ModelRegistryEvent`, никакой логики игры
- `domain/**` — режим чистой логики: без `net.minecraft.*` и Forge, полностью покрыто unit-тестами
- `build.gradle`, `gradle.properties` — режим сборки: версии Forge и маппингов, `version`/`group`/`archivesBaseName`, зависимости `deobfCompile`, без лишних
  репозиториев

Агент не требует отдельного выбора «узкого специалиста»: режим очевиден по типу файлов.

---

## Правила кода

### ООП и качество

- **Одна ответственность.** Класс блока описывает блок, а не правила игры: расчёты, проверки, состояние машин — в `domain/` или сервисах, которые блок вызывает
- **Композиция вместо наследования.** Не строить иерархии `BlockBase → BlockMachineBase → …` ради регистрации; общее поведение — через вспомогательные классы,
  capability, интерфейсы
- **Инкапсуляция.** Поля `private`, доступ через методы; публичные статические изменяемые поля — только `@ObjectHolder`-ссылки и `@Config`
- **Неизменяемость** там, где возможно: `final`-поля, неизменяемые value-объекты, `Collections.unmodifiable*` наружу
- **Зависимости через конструктор**, а не через статические синглтоны; интерфейсы на границах (сервис, хранилище, отправка пакетов) — чтобы логику можно было
  протестировать
- **Явная обработка null:** `@Nullable`/`@Nonnull` (`javax.annotation`) на API, проверка перед использованием, `ItemStack.EMPTY` и `isEmpty()` вместо `null`
- **Без магических чисел:** именованные константы (`TICKS_PER_SECOND = 20`, `MAX_REACH_SQ = 64.0`), `enum` для вариантов
- Методы короткие, имена говорят, что делают; дублирование выносится

### Безопасность — сервер не доверяет клиенту

- Каждый пакет с клиента проверяется на сервере: игрок существует и жив, позиция загружена (`world.isBlockLoaded(pos)`), игрок рядом
  (`player.getDistanceSq(pos) <= MAX_REACH_SQ`), у него есть право на действие, открыт нужный `Container`
- Индексы слотов, количества, ординалы enum, длины строк и коллекций из пакета — с проверкой границ; лимит длины при чтении строк и списков
- Чтение NBT защитное: `hasKey` с типом, значения по умолчанию, ограничение размеров — битые данные мира не должны ронять сервер
- Мир меняется только в главном потоке сервера; никаких своих потоков, которые трогают мир
- Нет `Runtime.exec`, загрузки кода и классов по сети, HTTP-запросов из мода без явной настройки в конфиге; файлы — только в папке конфига или мира, путь не
  собирается из ввода игрока
- Команды и действия администратора — с `getRequiredPermissionLevel` не ниже 2
- Секретов (токены, ключи API) в коде и конфигах в git нет
- Аудит серверного кода — специалист `security` профиля (`forge-1-12-java-security-auditor`): его зовёт `security-check`, а `implement-feature` — для фич с
  пакетами, командами, правами и данными игроков

### Производительность

- `ITickable#update` — не тяжелее необходимого: работа раз в N тиков (константа), ранний выход на клиенте, если логика серверная
- Синхронизация с клиентом — при изменении, а не каждый тик; `markDirty()` после изменения состояния TileEntity
- Не обходить все сущности и TileEntity мира в тике; не создавать `new Random()` в тике — `world.rand`

### Запрещено

- Регистрация в статических инициализаторах и `GameRegistry.register` вне `RegistryEvent.Register`
- Интерфейс `IHasModel` и регистрация модели из конструктора блока — модели регистрируются в `ModelRegistryEvent` на клиенте
- Клиентские классы (`Minecraft`, `GuiScreen`, `net.minecraft.client.*`) в общем коде
- `null` вместо `ItemStack.EMPTY`
- Mixin, coremod и ASM-трансформеры — только крайняя мера по согласованию с командой
- Рефлексия к приватным полям vanilla без `ObfuscationReflectionHelper` и SRG-имён (в собранном моде имена другие)
- `System.out` и `printStackTrace` — только логгер мода
- Пустой `catch` и перехват `Exception` с проглатыванием ошибки
- Захардкоженный текст интерфейса — только ключи перевода (`I18n` на клиенте, `TextComponentTranslation` с сервера)

---

## Именование

| Что                    | Правило                                                | Пример                                     |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------ |
| Пакет                  | `com.<org>.<modid>.<слой>`                             | `com.example.examplemod.block`             |
| modid, registry name   | нижний регистр, `_` между словами                      | `examplemod:copper_ore`                    |
| Класс блока / предмета | `Block<Name>`, `Item<Name>`                            | `BlockCopperOre`, `ItemWrench`             |
| TileEntity             | `TileEntity<Name>`                                     | `TileEntityGrinder`                        |
| Сущность               | `Entity<Name>`                                         | `EntityGolem`                              |
| Сообщение сети         | `<Action>Message` + вложенный `Handler`                | `SetModeMessage`, `SetModeMessage.Handler` |
| Регистрация            | `Mod<Kind>s`                                           | `ModBlocks`, `ModItems`                    |
| Capability             | `I<Name>`, `<Name>Impl`, `<Name>Provider`              | `IMana`, `ManaImpl`, `ManaProvider`        |
| Ключ перевода          | `tile.<modid>.<name>.name`, `item.<modid>.<name>.name` | `tile.examplemod.copper_ore.name`          |
| Константы              | `UPPER_SNAKE_CASE`                                     | `MAX_ENERGY`                               |
| Тест                   | `<Class>Test`                                          | `GrinderRecipesTest`                       |

---

## Тесты

- **Unit (JUnit 4 + Mockito)** — `domain/`, расчёты, рецепты, проверка полей пакетов, перевод NBT в value-объекты. Это основной слой тестов: логику выносят из
  игровых классов именно ради него
- **Код, которому нужен реестр** (блоки, предметы, `ItemStack`) — `Bootstrap.register()` один раз в `@BeforeClass`; таких тестов немного, они медленнее
- **В игре** — `./gradlew runClient` (и `runServer`, чтобы проверить выделенный сервер): сценарий проверки описывает тестировщик, проходит его `check-feature`
  или человек
- Тестировать поведение, а не устройство класса

```

---

## Документация мода

Документацию в `docs/` проекта ведёт агент `forge-1-12-java-doc-writer`, только на русском: обзор и оглавление, установка, блоки, предметы, сущности, команды, конфиг, сеть и API для других модов. Написать с нуля или обновить после фичи — `forge-1-12-mod-docs`; `implement-feature` с задачей только про документацию запускает пайплайн `docs` профиля.

---

## Доступные скиллы

- `forge-1-12-new-block` — новый блок: класс, регистрация блока и ItemBlock, ключ перевода, список нужных ресурсов
- `forge-1-12-new-item` — новый предмет: класс, регистрация, ключ перевода, список нужных ресурсов
- `forge-1-12-new-tile-entity` — TileEntity: NBT, синхронизация с клиентом, тик с троттлингом
- `forge-1-12-new-packet` — сетевое сообщение с серверной проверкой ввода
- `forge-1-12-new-config` — параметры конфига через `@Config` с диапазонами
- `forge-1-12-new-command` — серверная команда с уровнем прав
- `forge-1-12-add-tests` — unit-тесты для существующего кода мода
- `forge-1-12-mod-docs` — написать или обновить документацию мода в `docs/`
- `forge-1-12-setup-checkstyle` — подключить Checkstyle с правилами профиля к `build.gradle`

`security-check` вместе с общим аудитом зовёт специалиста `security` профиля — `forge-1-12-java-security-auditor`: пакеты, дюпы, права команд, доверие клиенту, потоки, NBT и работа на выделенном сервере.
```
