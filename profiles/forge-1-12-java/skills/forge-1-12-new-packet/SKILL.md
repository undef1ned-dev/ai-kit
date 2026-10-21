---
name: "forge-1-12-new-packet"
description: "Создать сетевое сообщение мода Forge 1.12.2 (IMessage + IMessageHandler в SimpleNetworkWrapper) с серверной проверкой каждого поля, лимитами размеров и работой с миром в главном потоке. Используй, когда клиенту нужно отправить действие на сервер или серверу — данные клиенту."
argument-hint: "<имя> [--to-client]"
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "network", "security"]
orchestrates: []
example_prompt: "/forge-1-12-new-packet set_grinder_mode"
---

Создай сетевое сообщение по правилам `CLAUDE.md` профиля `forge-1-12-java`.

$ARGUMENTS

Если не указано имя или не сказано, какие данные передаются и что делает получатель, — уточни. По умолчанию направление — клиент → сервер; `--to-client` — сервер → клиент.

## Перед созданием

- Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`
- Найди `network/ModNetwork` (канал `SimpleNetworkWrapper`) и существующие сообщения. Канала нет — создай `ModNetwork` с `NetworkRegistry.INSTANCE.newSimpleChannel(MOD_ID)` и регистрацией в `preInit`
- Дискриминаторы сообщений — по порядку, не переиспользуй занятые

## Что создать

1. `network/<Action>Message.java` — `IMessage` с пустым конструктором, `fromBytes`/`toBytes` в одном порядке полей; строки — `ByteBufUtils` с лимитом длины (константа)
2. Вложенный `Handler implements IMessageHandler<…, IMessage>`:
   - работа с миром — через `addScheduledTask` (`player.getServerWorld()` на сервере, `Minecraft.getMinecraft()` на клиенте), не в сетевом потоке
   - **клиент → сервер: сервер не доверяет ни одному полю**:
     - игрок — `ctx.getServerHandler().player`, а не id из пакета;
     - позиция — `world.isBlockLoaded(pos)` и `player.getDistanceSq(pos) <= MAX_REACH_SQ`;
     - индексы слотов, количества, ординалы enum — в границах;
     - у игрока открыт нужный `Container` и есть право на действие;
     - при нарушении — ничего не делать (и записать в лог на уровне debug), не бросать исключение;
   - проверку вынеси в отдельный метод или класс — её покрывают тесты
   - **сервер → клиент:** `Handler` регистрируется с `Side.CLIENT`, клиентский код — только внутри обработчика или в `client/`
3. Регистрация в `ModNetwork.registerMessage(Handler.class, Message.class, id, Side.SERVER | Side.CLIENT)`
4. Отправка — `ModNetwork.CHANNEL.sendToServer`, `sendTo(player)`, `sendToAllTracking` — там, где сообщение рождается

## После создания

1. Запусти `lint` профиля из `.aikit/profiles.json` в папке `root` и исправь ошибки
2. Покажи поля сообщения и список серверных проверок
3. Предложи тесты на отказ: чужая позиция, слишком далеко, индекс вне границ — `/forge-1-12-add-tests`
