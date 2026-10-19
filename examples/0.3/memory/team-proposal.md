---
title: Deploys freeze on Fridays after 14:00 UTC
updated: "2026-10-17T15:02:10Z"
recorded_at: "2026-10-17T15:02:10Z"
id: "ab-knowledge-412"
type: procedural
importance: 0.8
partition: platform
derived_from: [memory/fact/9131, memory/fact/9140]
relations:
  - { rel: refines, target: procedures/release-checklist }
source:
  origin: consolidation
  basis: inferred
  principal: "service:compression"
review:
  state: proposed
  generated: { by: "service:compression", at: "2026-10-17T15:02:10Z" }
x_agent_brain:
  search_keys: [deploy, freeze, friday]
---
Do not start a production deploy on Friday after 14:00 UTC. Hotfixes need a
curator's approval in the release channel first.
