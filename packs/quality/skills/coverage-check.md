---
name: "coverage-check"
description: Проверить покрытие тестами и выявить непокрытые критические модули. Запускает coverage, анализирует результат, предлагает тесты для самых важных пробелов.
version: "1.0.0"
profile: "pack:quality"
tags: ["quality", "testing", "coverage"]
orchestrates: ["quality-analyst"]
example_prompt: "/coverage-check"
---

Запусти агент `quality-analyst` для анализа покрытия тестами.

$ARGUMENTS

Агент должен:
1. Запустить тесты с coverage (pytest --cov или xcode coverage)
2. Определить модули с критически низким покрытием (<50%)
3. Для каждого непокрытого модуля — предложить конкретные тест-кейсы
4. Приоритизировать по бизнес-критичности (services > routers > models > utils)
