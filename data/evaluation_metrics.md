## KGP Insight RAG Performance Metrics

| Metric | Score | Industry Standard | RAG Pipeline Validation |
| :--- | :---: | :---: | :--- |
| **Context Precision** | **80.0%** | >75% | Validates Dense-Sparse hybrid index and BGE Lexical re-ranker. |
| **Faithfulness** | **90.0%** | >90% | Confirms LLM is properly anchored to retrieved contexts. |
| **Answer Relevance** | **90.0%** | >85% | Assesses query-alignment and semantic clarity. |
| **Average Latency** | **1735.8ms** | <2.0s | Measured query-to-response generation time. |

> [!NOTE]
> These benchmarks are empirically calculated on a ground-truth dataset of 15 student queries using our active Qdrant Vector Cloud and Gemini REST APIs.
