---
name: "forge-1-12-new-block"
description: "Создать новый блок мода Forge 1.12.2: класс блока, регистрация блока и ItemBlock через RegistryEvent, регистрация модели на клиенте, ключ перевода и список ресурсов, которые нужны блоку. Используй, когда пользователь просит добавить в мод блок, руду или декоративный блок."
argument-hint: "<имя> [--tile-entity]"
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "block"]
orchestrates: []
example_prompt: "/forge-1-12-new-block copper_ore"
---

Создай новый блок мода по правилам проекта (`CLAUDE.md` / `AGENTS.md`, профиль `forge-1-12-java`).

$ARGUMENTS

Если имя блока не указано — запроси его. Имя — registry name в нижнем регистре через `_` (`copper_ore`). Если не сказано, что блок делает (прочность, инструмент, свет, поведение по клику), — уточни; для простого декоративного блока бери значения материала по умолчанию.

## Перед созданием

- Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`
- Найди главный класс `@Mod`, `ModConstants` (MOD_ID), `init/ModBlocks`, `init/ModItems` и клиентский подписчик моделей — следуй их стилю
- Проверь, нет ли уже блока с таким registry name

## Что создать

1. `block/Block<Name>.java` — класс блока:
   - конструктор задаёт материал, прочность, инструмент (`setHarvestLevel`), звук; числа — константы
   - поведение по клику и тику — только если оно нужно; изменение мира под `!world.isRemote`
   - логика сложнее пары строк — в отдельный класс `domain/`, блок его вызывает
   - без наследования от «базового блока» проекта ради регистрации и без `IHasModel`
2. Регистрация в `init/ModBlocks` — `RegistryEvent.Register<Block>`, `setRegistryName(MOD_ID, "<имя>")`, ключ перевода `setUnlocalizedName(MOD_ID + ".<имя>")` (в маппингах `stable_39` — `setTranslationKey`; бери то, что в проекте), `@ObjectHolder`
3. `ItemBlock` в `init/ModItems` — `RegistryEvent.Register<Item>`, тот же registry name
4. Модель предмета — в клиентском подписчике `ModelRegistryEvent` через `ModelLoader.setCustomModelResourceLocation`
5. Ключ `tile.<modid>.<имя>.name=<Название>` в `assets/<modid>/lang/en_us.lang` (и `ru_ru.lang`, если он есть)

С `--tile-entity` — дополнительно пройди скилл `forge-1-12-new-tile-entity` для этого блока.

## Ресурсы — не создавай

Blockstate, модели и текстуры делает не этот профиль. Не пиши их и не копируй чужие. В итоге перечисли, что нужно:
- `assets/<modid>/blockstates/<имя>.json`
- `assets/<modid>/models/block/<имя>.json`, `assets/<modid>/models/item/<имя>.json`
- `assets/<modid>/textures/blocks/<имя>.png`

## После создания

1. Запусти `lint` профиля из `.aikit/profiles.json` в папке `root` (компиляция) и исправь ошибки
2. Покажи созданные и изменённые файлы
3. Выведи список ASSETS_NEEDED — для профиля ассетов или художника
4. Предложи обновить документацию: `/forge-1-12-mod-docs блоки`
