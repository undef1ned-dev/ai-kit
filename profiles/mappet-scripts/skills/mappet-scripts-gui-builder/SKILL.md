---
name: mappet-scripts-gui-builder
description: "Создать или исправить экран Mappet EOC по существующим GUI проекта: жизненный цикл, callback, NBT, синхронизация и переходы. Используй для реализации или изменения игрового GUI."
argument-hint: "<экран или задача>"
---

Для задачи только про экран прочитай .aikit/profiles.json и запусти специалиста из specialists.gui.agent инструментом текущего runtime. В Claude Code используй Agent, в Antigravity — invoke_subagent с именем роли без префикса в TypeName, описанием ответственности в Role и задачей в Prompt. Передай оба GUI-скилла, если субагент не видит установленные инструкции. Если ты уже этот специалист, выполни инструкцию на месте. При смешанной фиче этот скилл использует специалист, которого запускает /implement-feature.

# Создание и исправление GUI Mappet Scripts

Прочитай правила профиля, исходный экран задачи, src/classes/utils/GuiUtils.ts, src/libs/Callback.ts и определения builder/context/компонентов в src/@types/mappet.d.ts. Используй mappet-scripts-gui-layout для геометрии. Пути разрешай от root профиля.

## Выбор рабочего образца

| Сценарий | Что изучать в src/gui/ |
| --- | --- |
| Личный экран, простые переходы и выбор | PlayerInfo.ts, GuidesList.ts, EffectsList.ts |
| Счёт, исключительный доступ, суммы, пагинация | bank/BankAccountInfo.ts, bank/BankAccountOperations.ts |
| Список → карточка с подтверждением | real-estate/RealEstateList.ts, real-estate/RealEstatePurchase.ts |
| Список/детали/права и поиск по составу | guild/GuildMembers.ts, manufactory/ManufactoryMembers.ts |
| Меню, формы и синхронизация открытых окон | council/CouncilMain.ts, council/CouncilTaxes.ts, council/CouncilElection.ts |
| Заказы, повторяющиеся строки и прокрутка | manufactory/ManufactoryOrdersList.ts, manufactory/ManufactoryOrder.ts, guild/GuildOrder.ts |
| Интерактивные предметы, таймер, общий/личный режим | CraftTable.ts, TradeTable.ts, DiceRoll.ts |
| Фазы боя, разные права, несколько участников | combat/CombatStart.ts, combat/CombatAttack.ts, combat/CombatDefense.ts, combat/CombatMain.ts; CombatGui в src/classes/Combat.ts |

## Порядок объявлений в файле

1. Для нового GUI выбери ближайший рабочий экран из того же семейства и выпиши его методы в порядке объявления. Начало обычно такое — поля, constructor, static handleMain, init. Дальше повтори порядок однотипных методов именно этого экрана. Например, в BankAccountOperations после init идут setupCallbacks → prepareData → buildUI, в CouncilTaxes — prepareData → setupCallbacks → buildUI, в EffectsList — prepareData → buildUI и сборщики секций → setupCallbacks.
2. Сохраняй соседство методов сборки экрана и его секций, затем располагай обработчики действий, закрытие и вспомогательные методы по образцу. Глобальный main оставляй после класса. При правке существующего GUI вставляй новый метод в соответствующую группу текущего файла.
3. Перед сдачей сравни порядок объявлений с образцом (или с исходным порядком при правке). Порядок вызовов в init проверяй отдельно.

## Жизненный цикл

1. Проследи, кто запускает глобальный main(c: IScriptEvent), какие EVars доступны, какие ошибки идут в Logger.reportScriptError и как закрывается экран. Сопоставь с ближайшим классом: конструктор и prepareData → handleMain/init → buildUI и setupCallbacks → openUI. Если вход или экран уже работают иначе, сохрани их поведение.
2. Выбери идентичность окна. Личный экран использует UUID игрока, общий ресурс — стабильный ID объекта и, если это предусмотрено сценарием, GuiUtils.isGuiUsed. Один guiId может группировать участников общего окна для обновления. Не добавляй исключительную блокировку в групповой экран. Свяжи guiId с наличием правильного UIContext, предусмотрев close/back, отказ открытия, смену экрана, выход игрока.
3. Для обычного окна используй локальный паттерн mappet.createUI(c, handler).background(), layout и отдельные build-методы секций. Связывай handler с глобальной функцией Callback, зарегистрированной в metadata. Клавишу бери из EKeyCodes и действие из EActions. Сверь место привязки с образцом: большинство модальных окон используют корневой layout, PlayerInfo использует другой keybind, боевые окна управляют закрытием по фазе.
4. У каждой интерактивной ветки trace от id компонента к new Callback(id, player.uuid).setFunction(...) и обработчику. Динамический id получай из того же EElements и стабильного ID объекта в builder и при регистрации. Учитывай повторное открытие и реестр Callback. Не переписывай механизм регистрации без отдельной задачи.
5. Читай ввод типизированными NBT-геттерами UIContext.getData() по тем же ID. При нажатии заново прочитай состояние и проверь право, ресурс, фазу, доступность, диапазон и актуальность. Если есть подтверждение, привяжи его к текущему объекту/значению и сбрасывай при изменении ввода. Сообщение и восстановление UI возьми из соседнего сценария.
6. Свои изменения компонентов внутри callback Mappet отправляет после handler. Для другого игрока или обновления из внешнего скрипта проверь открытый контекст и используй sendToPlayer либо GuiUtils.syncPlayersContext по образцу. Начисление, расход, броски и состояние остаются в соответствующей механике.
7. Для переходов проследи оба конца: c.setValue с EVars, EScriptIds и EScriptFunctions, планирование или выполнение по соседнему экрану, очистка стейта и возможность вернуться. Обнови плоский список Libraries и точный ID исполняемого файла. Если world-side metadata недоступны, перечисли изменения в результате.

Проверь по исходникам, что совпадают ID и типы, переходы сохраняют контекст, закрытие освобождает ресурс, а повторные или параллельные действия безопасны. Выполни команды профиля и перечисли оставшиеся проверки в Minecraft. Для общего окна опиши как минимум сценарий взаимодействия двух игроков.

## Справочник API

- [IMappetUIBuilder](https://mchorse.github.io/mappet/mchorse/mappet/api/scripts/user/mappet/IMappetUIBuilder.html)
- [IMappetUIContext](https://mchorse.github.io/mappet/mchorse/mappet/api/scripts/user/mappet/IMappetUIContext.html)
- [UIComponent](https://mchorse.github.io/mappet/mchorse/mappet/api/ui/components/UIComponent.html)
