# Principal Development Guide

The Principal identity publishes tasks, defines acceptance, reviews results, and scores contractors.

## Required Capabilities

- `publish_task`
- `review_task`
- `score_contractor`

## Responsibilities

- Compute `delegation_score`.
- Set `acceptance_level`.
- Provide actionable rejection feedback.
- Review only tasks published by the same principal identity.

## Boundary

A Principal must not submit contractor results or close tasks directly. Closing is performed by the board after an approved review.

