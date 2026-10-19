#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "${0//\\//}")/../../lib/setup-project.sh" vue-nuxt nuxt-app
