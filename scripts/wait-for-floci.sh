#!/usr/bin/env bash
# Blocks until Floci answers, so `terraform apply` does not race its start.
set -euo pipefail
curl -fsS --retry 60 --retry-delay 2 --retry-connrefused -o /dev/null localhost:4566/_floci/health
