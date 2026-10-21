---
name: "forge-1-12-new-item"
description: "Создать новый предмет мода Forge 1.12.2: класс предмета, регистрация через RegistryEvent, модель на клиенте, ключ перевода и список ресурсов. Используй, когда пользователь просит добавить в мод предмет, инструмент, еду или материал."
argument-hint: "<имя>"
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "item"]
orchestrates: []
example_prompt: "/forge-1-12-new-item copper_ingot"
---

Создай новый предмет мода по правилам `CLAUDE.md` профиля `forge-1-12-java`.

$ARGUMENTS

Если имя не указано — запроси его. Имя — registry name в нижнем регистре через `_`. Если не сказано, что предмет делает (материал, инструмент, еда, действие по правому клику), — уточни.

## Перед созданием

- Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`
- Найди `ModConstants`, `init/ModItems`, клиентский подписчик моделей и похожие предметы — следуй их стилю
- Проверь, нет ли уже предмета с таким registry name

## Что создать

1. Предмет:
   - простой материал без поведения — экземпляр `Item` в регистрации, отдельный класс не нужен
   - инструмент, броня, еда — от vanilla-класса (`ItemPickaxe`, `ItemArmor`, `ItemFood`) с `ToolMaterial`/`ArmorMaterial` через `EnumHelper`, параметры — константы
   - своё поведение — `item/Item<Name>.java`: `onItemRightClick` возвращает `ActionResult`, мир меняется под `!world.isRemote`, `ItemStack.EMPTY` вместо `null`, NBT стека читается через `hasTagCompound()` и `hasKey`
   - логика сложнее пары строк — в `domain/`
2. Регистрация в `init/ModItems` — `RegistryEvent.Register<Item>`, `setRegistryName`, `setUnlocalizedName` (в маппингах `stable_39` — `setTranslationKey`; бери то, что в проекте), `setCreativeTab`, `@ObjectHolder`
3. Модель — в клиентском `ModelRegistryEvent` через `ModelLoader.setCustomModelResourceLocation`
4. Ключ `item.<modid>.<имя>.name=<Название>` в `assets/<modid>/lang/en_us.lang` (и `ru_ru.lang`, если он есть)

## Ресурсы — не создавай

Модель и текстуру делает не этот профиль. В итоге перечисли:
- `assets/<modid>/models/item/<имя>.json`
- `assets/<modid>/textures/items/<имя>.png`

## После создания

1. Запусти `lint` профиля из `.aikit/profiles.json` в папке `root` (компиляция) и исправь ошибки
2. Покажи созданные и изменённые файлы и список ASSETS_NEEDED
3. Предложи 2-3 тестовых сценария и обновить документацию: `/forge-1-12-mod-docs предметы`
