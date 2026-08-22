# Summary

## Experiment

- **Date:** 2026-08-20
- **Configuration:** 4 models × 3 approaches × 17 tasks × 3 repetitions = 612 cells
- **Completed cells:** 609
- **Models:** llama3.1:8b (medium, 8B), llama3.2:3b (SLM, 3B), qwen2.5:3b (SLM, 3B), qwen2.5:7b (medium, 7B)
- **Approaches:** A (Raw SQL), B (Verticalized pack), C (Generic pack)
- **Scoring:** Rule-based per-task checks with fuzzy title matching (SequenceMatcher ≥ 0.72)
- **Excluded models:** gemma2:2b, phi3:mini (Ollama HTTP 400 "does not support tools")

---

## Accuracy

### By Model × Approach

| model | approach | n | mean_score | perfect | partial | failed | error_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| llama3.1:8b | A | 51 | 0.75 | 24 | 27 | 0 | 0.0 |
| llama3.1:8b | B | 51 | 0.966 | 45 | 6 | 0 | 0.0 |
| llama3.1:8b | C | 51 | 0.769 | 30 | 18 | 3 | 0.059 |
| llama3.2:3b | A | 51 | 0.583 | 6 | 45 | 0 | 0.0 |
| llama3.2:3b | B | 51 | 0.929 | 42 | 9 | 0 | 0.0 |
| llama3.2:3b | C | 51 | 0.419 | 0 | 48 | 3 | 0.0 |
| qwen2.5:3b | A | 48 | 0.684 | 17 | 29 | 2 | 0.0 |
| qwen2.5:3b | B | 51 | 0.902 | 42 | 6 | 3 | 0.0 |
| qwen2.5:3b | C | 51 | 0.602 | 14 | 31 | 6 | 0.0 |
| qwen2.5:7b | A | 51 | 0.647 | 20 | 26 | 5 | 0.059 |
| qwen2.5:7b | B | 51 | 0.958 | 45 | 6 | 0 | 0.0 |
| qwen2.5:7b | C | 51 | 0.631 | 19 | 25 | 7 | 0.0 |

### By Approach (aggregated)

| approach | n | mean_score | perfect | partial | failed |
| --- | --- | --- | --- | --- | --- |
| **B (Verticalized)** | 204 | 0.939 | 174 (85%) | 27 | 3 |
| A (Raw SQL) | 201 | 0.666 | 67 (33%) | 127 | 7 |
| C (Generic) | 204 | 0.605 | 63 (31%) | 122 | 19 |

### By Model (aggregated across approaches)

| model | n | mean_score |
| --- | --- | --- |
| llama3.1:8b | 153 | 0.828 |
| qwen2.5:7b | 153 | 0.745 |
| qwen2.5:3b | 150 | 0.73 |
| llama3.2:3b | 153 | 0.644 |

---

## Tokens

| model | approach | mean_prompt | mean_completion | mean_total | ctx_overhead |
| --- | --- | --- | --- | --- | --- |
| llama3.1:8b | A | 2589.3529411764707 | 143.8235294117647 | 2733.176470588235 | 2589.4 |
| llama3.1:8b | B | 2154.5882352941176 | 78.82352941176471 | 2233.4117647058824 | 2154.6 |
| llama3.1:8b | C | 2379.0588235294117 | 137.19607843137254 | 2516.2549019607845 | 2379.1 |
| llama3.2:3b | A | 3467.529411764706 | 235.58823529411765 | 3703.1176470588234 | 3467.5 |
| llama3.2:3b | B | 2173.529411764706 | 68.88235294117646 | 2242.4117647058824 | 2173.5 |
| llama3.2:3b | C | 1368.0 | 104.72549019607843 | 1472.7254901960785 | 1368.0 |
| qwen2.5:3b | A | 4126.166666666667 | 2060.2083333333335 | 6186.375 | 4126.2 |
| qwen2.5:3b | B | 3795.5686274509803 | 129.58823529411765 | 3925.156862745098 | 3795.6 |
| qwen2.5:3b | C | 3672.823529411765 | 143.09803921568627 | 3815.921568627451 | 3672.8 |
| qwen2.5:7b | A | 3014.450980392157 | 304.84313725490193 | 3319.294117647059 | 3014.5 |
| qwen2.5:7b | B | 3731.235294117647 | 90.23529411764706 | 3821.470588235294 | 3731.2 |
| qwen2.5:7b | C | 3659.529411764706 | 113.2156862745098 | 3772.7450980392155 | 3659.5 |

### Token Efficiency by Approach

| approach | mean_total_tokens | vs_b | tokens_per_correct | seconds_per_correct |
| --- | --- | --- | --- | --- |
| **B (Verticalized)** | 3,056 | — | 3,582 | 5.2 |
| C (Generic) | 2,894 | -5.3% | 9,372 | 20.7 |
| A (Raw SQL) | 3,953 | +29.4% | 11,858 | 51.9 |

---

## Latency / steps

| model | approach | mean_latency_ms | mean_wall_ms | mean_steps | mean_tool_calls |
| --- | --- | --- | --- | --- | --- |
| llama3.1:8b | A | 7673.0 | 7673.3 | 2.1 | 1.1 |
| llama3.1:8b | B | 5889.7 | 5890.8 | 2.0 | 1.1 |
| llama3.1:8b | C | 9411.0 | 62355.0 | 2.5 | 2.2 |
| llama3.2:3b | A | 5828.8 | 5829.4 | 2.5 | 1.8 |
| llama3.2:3b | B | 2788.0 | 2788.4 | 2.0 | 1.1 |
| llama3.2:3b | C | 2780.2 | 2781.1 | 2.4 | 1.4 |
| qwen2.5:3b | A | 44303.3 | 44304.0 | 2.8 | 2.1 |
| qwen2.5:3b | B | 4094.4 | 4095.0 | 2.1 | 1.1 |
| qwen2.5:3b | C | 5482.7 | 5483.7 | 2.4 | 1.8 |
| qwen2.5:7b | A | 13023.0 | 65966.7 | 2.2 | 1.3 |
| qwen2.5:7b | B | 4958.1 | 4958.6 | 2.1 | 1.3 |
| qwen2.5:7b | C | 7936.9 | 7937.4 | 2.3 | 1.6 |

### Latency by Approach

| approach | mean_latency_ms | mean_steps | mean_tool_calls |
| --- | --- | --- | --- |
| **B (Verticalized)** | 4,433 | 2.1 | 1.1 |
| C (Generic) | 6,403 | 2.4 | 1.7 |
| A (Raw SQL) | 17,310 | 2.4 | 1.6 |

---

## Per-task mean score (all approaches, averaged across models)

| task | llama3.1:8b | llama3.2:3b | qwen2.5:3b | qwen2.5:7b |
| --- | --- | --- | --- | --- |
| avoid_on_loan | 0.83 (n=9) | 0.61 (n=9) | 0.72 (n=9) | 0.72 (n=9) |
| customer_workflow | 0.89 (n=9) | 0.81 (n=9) | 0.81 (n=9) | 0.53 (n=9) |
| film_details | 0.67 (n=9) | 0.67 (n=9) | 0.75 (n=9) | 0.50 (n=9) |
| find_customer | 1.00 (n=9) | 0.78 (n=9) | 1.00 (n=9) | 0.89 (n=9) |
| g_available | 1.00 (n=9) | 0.56 (n=9) | 0.85 (n=9) | 1.00 (n=9) |
| good_standing_recommend | 0.53 (n=9) | 0.61 (n=9) | 0.72 (n=9) | 0.67 (n=9) |
| not_found | 1.00 (n=9) | 0.78 (n=9) | 1.00 (n=9) | 1.00 (n=9) |
| not_rented | 0.72 (n=9) | 0.50 (n=9) | 0.28 (n=9) | 0.72 (n=9) |
| overdue_report | 0.89 (n=9) | 0.78 (n=9) | 0.59 (n=9) | 0.67 (n=9) |
| recommend_category | 0.83 (n=9) | 0.67 (n=9) | 0.78 (n=9) | 0.83 (n=9) |
| recommend_rating | 1.00 (n=9) | 0.83 (n=9) | 1.00 (n=9) | 1.00 (n=9) |
| rental_empty | 0.78 (n=9) | 0.56 (n=9) | 0.67 (n=9) | 0.67 (n=9) |
| rental_history | 0.56 (n=9) | 0.33 (n=9) | 0.59 (n=9) | 0.48 (n=9) |
| return_verify | 1.00 (n=9) | 0.61 (n=9) | 0.67 (n=9) | 0.67 (n=9) |
| service_case | 0.80 (n=9) | 0.58 (n=9) | 0.70 (n=6) | 0.58 (n=9) |
| store_availability | 0.75 (n=9) | 0.67 (n=9) | 0.56 (n=9) | 0.92 (n=9) |
| upsell_seen | 0.83 (n=9) | 0.61 (n=9) | 0.72 (n=9) | 0.83 (n=9) |

---

## Per-task mean score by approach

| task | A (SQL) | B (Verticalized) | C (Generic) | Δ(B−A) |
| --- | --- | --- | --- | --- |
| `recommend_category` | 0.500 | **1.000** | 0.833 | +50.0pp |
| `avoid_on_loan` | 0.500 | **1.000** | 0.667 | +50.0pp |
| `upsell_seen` | 0.500 | **1.000** | 0.750 | +50.0pp |
| `film_details` | 0.562 | **1.000** | 0.375 | +43.8pp |
| `customer_workflow` | 0.584 | **1.000** | 0.688 | +41.6pp |
| `rental_history` | 0.361 | **0.694** | 0.417 | +33.4pp |
| `store_availability` | 0.667 | **1.000** | 0.500 | +33.3pp |
| `good_standing_recommend` | 0.583 | **0.896** | 0.417 | +31.3pp |
| `g_available` | 0.722 | **1.000** | 0.833 | +27.8pp |
| `service_case` | 0.694 | **0.950** | 0.350 | +25.6pp |
| `not_rented` | 0.500 | **0.750** | 0.417 | +25.0pp |
| `return_verify` | 0.792 | **1.000** | 0.417 | +20.8pp |
| `find_customer` | 0.834 | **1.000** | 0.917 | +16.6pp |
| `overdue_report` | 0.861 | **1.000** | 0.334 | +13.9pp |
| `recommend_rating` | **1.000** | **1.000** | 0.875 | +0.0pp |
| `not_found` | **1.000** | **1.000** | 0.833 | +0.0pp |
| `rental_empty` | **0.667** | **0.667** | 0.667 | +0.0pp |

---

## Key Findings

1. **Verticalized (B) dominates on accuracy**: 93.9% mean score vs 66.6% (A) and 60.5% (C); 85% of B cells are fully correct vs 33% and 31%
2. **Cost per correct answer is the decisive efficiency metric**: per-cell token cost is comparable across designs (2,894–3,953 tokens), but per fully-correct cell B needs 3,582 tokens vs 9,372 (C) and 11,858 (A)
3. **B is also the fastest design**: 4,433 ms/cell vs 6,403 (C) and 17,310 (A)
4. **C (Generic) underperforms A (Raw SQL)** despite comparable per-cell token cost: a generic tool surface adds no measurable value over direct SQL access
5. **SLM scalability**: even the smallest model (llama3.2:3b) reaches 92.9% with B vs 58.3% with A; across models, B reduces cost per correct answer by 2.0–11.6× vs A
6. **Workflow tasks show the largest gap**: multi-step tasks (avoid_on_loan, customer_workflow, upsell_seen) show a 40–50pp advantage for B

## Limitations

- 3 cells missing: qwen2.5:3b service_case/A (stdio pipe hang during MCP server startup)
- gemma2:2b and phi3:mini excluded due to Ollama tool-calling incompatibility
- Rule-based scoring may miss valid phrasings not captured in regex patterns
- Fuzzy matching threshold (0.72) is a hyperparameter that could affect results
- Single database (Sakila) limits generalizability claims
