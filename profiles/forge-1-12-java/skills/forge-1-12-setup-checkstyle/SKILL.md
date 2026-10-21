---
name: "forge-1-12-setup-checkstyle"
description: "Подключить Checkstyle к моду Forge 1.12.2: плагин checkstyle в build.gradle (Gradle 4.9, ForgeGradle 3 или 2.3), правила профиля в config/checkstyle/checkstyle.xml — именование, неиспользуемые импорты, длина методов и файлов, порядок модификаторов, магические числа, пустые catch, System.out. Используй, когда пользователь просит настроить Checkstyle или линтер Java-кода мода."
argument-hint: "[--report-only]"
disable-model-invocation: true
version: "1.0.0"
profile: "forge-1-12-java"
tags: ["forge-1-12-java", "minecraft", "forge", "checkstyle", "lint"]
orchestrates: []
example_prompt: "/forge-1-12-setup-checkstyle"
---

Подключи Checkstyle к моду по правилам профиля `forge-1-12-java`.

$ARGUMENTS

Папка мода — `root` профиля `forge-1-12-java` в `.aikit/profiles.json`; все пути ниже — от неё.

## Шаг 1 — Что уже есть

1. Прочитай `build.gradle`: есть ли `apply plugin: "checkstyle"` или `id "checkstyle"`
2. Есть ли `config/checkstyle/checkstyle.xml`
3. Уже настроено — покажи текущие настройки и спроси, заменить ли конфиг правилами профиля. Без согласия ничего не перезаписывай

## Шаг 2 — Конфиг

Скопируй `checkstyle.xml` из папки этого скилла (рядом с этим `SKILL.md`) в `config/checkstyle/checkstyle.xml` без изменений. Что в нём:
- ошибки (ломают `./gradlew check`): именование, `*`-импорты и неиспользуемые импорты, длина метода больше 80 строк и файла больше 1000, больше 7 параметров, порядок модификаторов, магические числа (кроме -1, 0, 1, 2, аннотаций и объявлений полей), пустые `catch`, `System.out` и `printStackTrace`, `if` без скобок, `equals` без `hashCode`, сравнение строк через `==`;
- предупреждения (не ломают сборку): публичные изменяемые поля (поля `@Config`, `@SidedProxy` и `@ObjectHolder` не считаются), утилитный класс без приватного конструктора, нет перевода строки в конце файла;
- стиль скобок не проверяется: в MDK Forge скобка на новой строке, команда выбирает сама.

Один случай можно подавить аннотацией `@SuppressWarnings("checkstyle:magicnumber")` с понятной причиной рядом.

## Шаг 3 — build.gradle

Добавь после строки, которая подключает ForgeGradle: `apply plugin: 'net.minecraftforge.gradle'` (ForgeGradle 3, официальный MDK) или `apply plugin: 'net.minecraftforge.gradle.forge'` (ForgeGradle 2.3):

```groovy
apply plugin: "checkstyle"

checkstyle {
    // 8.45.1 is the last Checkstyle line that runs on Java 8, which ForgeGradle for 1.12.2 requires
    toolVersion = "8.45.1"
    configFile = file("config/checkstyle/checkstyle.xml")
    ignoreFailures = false
}

tasks.withType(Checkstyle) {
    reports {
        xml.enabled = false
        html.enabled = true
    }
}
```

Синтаксис — Gradle 4.x: не используй `plugins { id "checkstyle" }` в одном файле с `buildscript` ForgeGradle и `required`/`outputLocation` из Gradle 7. С `--report-only` поставь `ignoreFailures = true` — нарушения видны в отчёте, но сборка не падает.

## Шаг 4 — Первый прогон

1. Выполни `./gradlew checkstyleMain checkstyleTest` в папке `root`
2. Нарушений нет — готово
3. Нарушения в существующем коде есть — покажи их число по правилам (отчёт — `build/reports/checkstyle/main.html`) и спроси пользователя:
   - исправить сейчас — отдельной задачей, файлы по одному, без изменения поведения;
   - временно `ignoreFailures = true`, пока долг не разобран (запиши это в `.aikit/memory/` через `/capture-memory`, если команда ведёт память);
   - ослабить конкретное правило в `config/checkstyle/checkstyle.xml` — только с согласия команды
   Код сам не исправляй и правила без согласия не ослабляй

## Шаг 5 — Команда lint

Команда `lint` профиля по умолчанию — `./gradlew compileJava check -x test`: без плагина это компиляция, с плагином `check` дополнительно запускает `checkstyleMain` и `checkstyleTest`. Если команда в `.aikit/profiles.json` другая (её меняли в проекте) — покажи пользователю, чтобы он решил, добавлять ли Checkstyle в неё.

## Итог

Покажи изменения `build.gradle`, путь конфига, результат первого прогона и что делает `lint` теперь. Коммит — по скиллу `git-commit`, только если пользователь попросит.
