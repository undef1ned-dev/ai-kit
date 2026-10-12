#!/usr/bin/env bash
# skills.sh — установка скиллов AIKit (<name>/SKILL.md) в .claude/skills/, общая для attach.sh и update.sh
#
# Подключается через source. Ожидает переменные CONFIG_ROOT, SCRIPT_DIR, PROFILE_LIST
# и функцию log_warn из вызывающего скрипта.
# После install_kit_skills в INSTALLED_SKILLS — имена установленных скиллов через пробел.

# Префикс профиля, которым прежние версии кита помечали конфликтующие команды: vue-nuxt→vue, python-fastapi→fastapi
legacy_profile_prefix() {
  echo "$1" | sed 's/python-//; s/-[a-z]*$//'
}

# Скопировать папку скилла под именем name и выставить name во frontmatter
install_skill() {
  local src="$1" dst_root="$2" name="$3"
  local dst="$dst_root/$name"
  rm -rf "$dst"
  cp -R "${src%/}" "$dst"
  local file="$dst/SKILL.md"

  # Runtime ищет скилл по name, а он должен совпадать с папкой
  awk -v name="$name" '!done && /^name:/ { print "name: \"" name "\""; done = 1; next } { print }' \
    "$file" > "$file.tmp" && mv "$file.tmp" "$file"
  INSTALLED_SKILLS="${INSTALLED_SKILLS:+$INSTALLED_SKILLS }$name"
}

# Установить скиллы base, профилей и паков в dst_root. Имена скиллов уникальны во всём ките (статическая проверка)
# Использование: install_kit_skills <dst_root> <packs>
install_kit_skills() {
  local dst_root="$1" packs="$2"
  local p pack dir
  INSTALLED_SKILLS=""
  mkdir -p "$dst_root"

  for dir in "$CONFIG_ROOT/base/skills"/*/; do
    if [[ -f "${dir}SKILL.md" ]]; then install_skill "$dir" "$dst_root" "$(basename "$dir")"; fi
  done

  for p in $PROFILE_LIST; do
    for dir in "$CONFIG_ROOT/profiles/$p/skills"/*/; do
      if [[ -f "${dir}SKILL.md" ]]; then install_skill "$dir" "$dst_root" "$(basename "$dir")"; fi
    done
  done

  for pack in $packs; do
    for dir in "$CONFIG_ROOT/packs/$pack/skills"/*/; do
      if [[ -f "${dir}SKILL.md" ]]; then install_skill "$dir" "$dst_root" "$(basename "$dir")"; fi
    done
  done
}

# Убрать скиллы прошлой установки и команды, которые ставили прежние версии кита в .claude/commands/
# Использование: remove_previous_kit_skills <claude_dir> <previous_skills>
remove_previous_kit_skills() {
  local claude_dir="$1" previous="$2"
  local name f prefix p

  for name in $previous; do
    if [[ "$name" != */* ]]; then rm -rf "${claude_dir:?}/skills/$name"; fi
  done

  [[ -d "$claude_dir/commands" ]] || return 0
  for f in "$CONFIG_ROOT"/base/skills/*/SKILL.md "$CONFIG_ROOT"/profiles/*/skills/*/SKILL.md "$CONFIG_ROOT"/packs/*/skills/*/SKILL.md; do
    [[ -f "$f" ]] || continue
    name="$(basename "$(dirname "$f")")"
    rm -f "$claude_dir/commands/$name.md"
    for p in "$CONFIG_ROOT"/profiles/*/; do
      prefix="$(legacy_profile_prefix "$(basename "$p")")"
      rm -f "$claude_dir/commands/$prefix-$name.md"
    done
  done
  rmdir "$claude_dir/commands" 2>/dev/null || true
}
