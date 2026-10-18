# Week 2 demonstration: under five minutes

Rehearse once to warm the local models. Run `python -m streamlit run app.py`, open http://localhost:8501 and select Bank of America as the base bank. Close credential tabs before recording. Keep the final experiment report and original source documents available in separate windows.

The screen contains the base-bank selector, question, answer and one-line source links. Experiment reports remain outside the analyst interface.

| Time | Show | Explain |
|---|---|---|
| 0:00-0:20 | App title, available banks and periods | Five banks, six official documents, frozen Q2 2025 with selected Q2 2024 comparisons. These are historical figures. |
| 0:20-1:10 | Ask: Compare consumer banking revenue in Q2 2025. | The base bank is the denominator; four peers are included automatically. Open a source link and verify its reported amount, segment and basis. Capital One Consumer Banking is separate from Credit Card and is unadjusted for acquisition effects. |
| 1:10-1:40 | Ask: Compare consumer revenue with Wells Fargo in Q2 2025. | Naming a peer narrows the comparison. A single-bank lookup such as What was Wells Fargo consumer revenue in Q2 2025? remains a lookup even with another base selected. |
| 1:40-2:20 | Ask: Compare consumer operating leverage across peers from Q2 2024 to Q2 2025. | The table uses Python-validated growth calculations and source-reviewed inputs. Preserve the bank-specific reporting bases and the Capital One scope/acquisition caveat. |
| 2:20-2:50 | Ask: What does Bank of America management say drove consumer revenue changes in Q2 2025? | This explanation exercises the configured LangChain/Nebius generation path. The final provider check cited higher NII and passed source review. Open the supporting disclosure. Do not present evidence-only output as model generation. |
| 2:50-3:10 | Ask: Compare consumer revenue in Q2 2026. | The requested quarter is outside the frozen corpus; no amount is invented. |
| 3:10-4:15 | Open reports/five-bank-retrieval/REPORT.md | Compare fixed/semantic with and without reranking. Raw recall is 98.9% for A/B and 97.8% for C/D; audited equivalents yield complete evidence on 18 narrow cases. Explain the retained initial Citi failures, pre-reviewed BofA/JPM alternatives, and unchanged saved rankings. This is development evidence, not general 100% answer accuracy. Equal recall on this table-heavy set does not demonstrate a semantic/reranking advantage. |
| 4:15-4:50 | Show workflow.py and the metric/coverage documentation | LangGraph scope -> retrieval -> calculation -> answer; LangChain documents, embeddings, retriever and generation chain. Explain source review, AI coding assistance, 100 tests, the 58-metric catalog and the 28-family coverage limits. |

Stop before five minutes. Use actual outputs and measured reports. Do not claim the proposed 95% faithfulness or 15-second warm p95 targets were established. If a live request fails, show the limitation and resolve it before presenting a successful demonstration.

After recording, add the video, Google Doc and GitHub links to docs/SUBMISSION_DRAFT.md and complete the handout submission form. The local source zip is artifacts/week2-ir-assistant.zip.
