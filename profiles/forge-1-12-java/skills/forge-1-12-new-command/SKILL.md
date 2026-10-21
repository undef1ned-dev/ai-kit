---
name: "forge-1-12-new-command"
description: "Создать серверную команду мода Forge 1.12.2 (CommandBase): уровень прав, разбор и проверка аргументов, автодополнение, ответ через ключи перевода, регистрация в FMLServerStartingEvent. Используй, когда моду нужна команда для игроков или администратора."
argument-hint: "<имя>"
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "command"]
orchestrates: []
example_prompt: "/forge-1-12-new-command examplemod reload — перезагрузить рецепты дробилки, только для операторов"
---

Создай серверную команду по правилам проекта (`CLAUDE.md` / `AGENTS.md`, профиль `forge-1-12-java`).

$ARGUMENTS

Если не указано имя, аргументы или кому доступна команда — уточни. По умолчанию команда только для операторов.

## Перед созданием

- Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`
- Найди `command/` и где мод обрабатывает `FMLServerStartingEvent` — следуй стилю проекта
- Несколько действий одного мода — подкоманды одной команды (`CommandTreeBase`), а не много команд верхнего уровня

## Что создать

1. `command/Command<Name>.java` — `extends CommandBase`:
   - `getName`, `getUsage` — ключ перевода `commands.<modid>.<имя>.usage`
   - `getRequiredPermissionLevel` — 2 и выше для всего, что меняет мир, инвентарь или данные других игроков; 0 — только для чтения своих данных
   - аргументы — через `parseInt`, `parseDouble`, `getPlayer`, `parseBlockPos` с границами; неверный ввод — `WrongUsageException` или `CommandException` с ключом перевода, не падение
   - `getTabCompletions` — подсказки аргументов
   - ответ — `TextComponentTranslation`, не захардкоженный текст
   - сама работа — в сервисе или domain, команда разбирает ввод и вызывает её
2. Регистрация — `event.registerServerCommand(new Command<Name>())` в обработчике `FMLServerStartingEvent` главного класса
3. Ключи `usage` и сообщений — в `assets/<modid>/lang/en_us.lang`

## После создания

1. Запусти `lint` профиля из `.aikit/profiles.json` в папке `root` и исправь ошибки
2. Покажи синтаксис команды, аргументы и уровень прав
3. Предложи тесты разбора аргументов и обновить документацию: `/forge-1-12-mod-docs команды`
