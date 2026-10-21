---
name: "forge-1-12-new-tile-entity"
description: "Создать TileEntity для блока мода Forge 1.12.2: состояние, защитное чтение и запись NBT, синхронизация с клиентом, тик с троттлингом, инвентарь через capability. Используй, когда блоку нужно хранить данные, работать как машина или иметь инвентарь."
argument-hint: "<блок> [--tickable] [--inventory]"
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "tileentity"]
orchestrates: []
example_prompt: "/forge-1-12-new-tile-entity grinder --tickable --inventory"
---

Создай TileEntity по правилам проекта (`CLAUDE.md` / `AGENTS.md`, профиль `forge-1-12-java`).

$ARGUMENTS

Если не указан блок — запроси его. Если не сказано, какие данные хранит TileEntity, — уточни.

## Перед созданием

- Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`
- Найди класс блока и существующие TileEntity проекта — следуй их стилю
- Если блока ещё нет — сначала скилл `forge-1-12-new-block`

## Что создать

1. `tileentity/TileEntity<Name>.java`:
   - поля `private`, изменение только через методы, после изменения — `markDirty()`
   - `writeToNBT` и `readFromNBT`: ключи — константы, чтение через `hasKey(key, Constants.NBT.TAG_…)` со значением по умолчанию; новые ключи не ломают старые миры
   - синхронизация с клиентом, если клиенту нужны данные (рендер, GUI): `getUpdateTag`, `getUpdatePacket`, `onDataPacket`; `world.notifyBlockUpdate` — только при изменении
   - `--tickable`: `implements ITickable`; `if (world.isRemote) return;` для серверной логики, работа раз в N тиков (константа)
   - `--inventory`: `ItemStackHandler` и `hasCapability`/`getCapability` для `CapabilityItemHandler.ITEM_HANDLER_CAPABILITY`, без устаревшего `IInventory`; содержимое выпадает при разрушении блока (`breakBlock`)
   - логика машины (рецепты, прогресс, расчёты) — в `domain/`, TileEntity хранит состояние и вызывает её
2. В блоке — `hasTileEntity(IBlockState)` и `createTileEntity(World, IBlockState)`
3. Регистрация — `GameRegistry.registerTileEntity(TileEntity<Name>.class, new ResourceLocation(MOD_ID, "<имя>"))` в `RegistryEvent.Register<Block>` или в `preInit`, как принято в проекте

## После создания

1. Запусти `lint` профиля из `.aikit/profiles.json` в папке `root` и исправь ошибки
2. Покажи NBT-ключи и что синхронизируется с клиентом
3. Предложи тесты: логика domain и перевод NBT туда и обратно, в том числе без ключа — `/forge-1-12-add-tests`
