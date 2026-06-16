#!/bin/zsh
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/scripts/run_production.sh"
