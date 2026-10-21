#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "${0//\\//}")/../../lib/setup-project.sh" forge-1-12-java forge-1-12-mod
