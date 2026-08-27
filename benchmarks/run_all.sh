#!/usr/bin/env bash
# Launch the AI CAPTCHA model benchmark across all agents, in parallel.
# Each agent runs in its own background process; results go to per_agent/*.json.
set -e
cd "$(dirname "$0")/.."
export AIC_SECRET_MODE=off
export AIC_TOKEN_SECRET="$(openssl rand -base64 48)"
export OPENCLAW_GATEWAY_TOKEN="$(grep OPENCLAW_GATEWAY_TOKEN ~/.openclaw/gateway.systemd.env | cut -d= -f2 | tr -d '"')"
mkdir -p benchmarks/per_agent benchmarks/logs
AGENTS="${AGENTS:-main coder analyst researcher designer user}"
for a in $AGENTS; do
  nohup .venv/bin/python -u benchmarks/model_benchmark.py run \
    --agent "$a" --trials "${TRIALS:-10}" --tiers easy,medium,hard \
    > "benchmarks/logs/$a.log" 2>&1 &
  echo "launched $a pid $!"
done
echo "all launched"
