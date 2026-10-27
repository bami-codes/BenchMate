#!/bin/sh
set -eu
BENCHMATE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export ARDUINO_DIRECTORIES_DATA="$BENCHMATE_ROOT/.arduino/data"
export ARDUINO_DIRECTORIES_DOWNLOADS="$BENCHMATE_ROOT/.arduino/downloads"
export ARDUINO_DIRECTORIES_USER="$BENCHMATE_ROOT/.arduino/user"
exec arduino-cli "$@"
