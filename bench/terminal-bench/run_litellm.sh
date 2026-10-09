#!/usr/bin/env bash
cd ~/tb
exec ./proxyvenv/bin/litellm --config litellm-glm.yaml --host 172.17.0.1 --port 4000
