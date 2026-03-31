# Dify-Guardian-ETL

[![Dify Version](https://img.shields.io/badge/Dify-0.x%20%2F%201.x-blue)](https://dify.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Standard RAG pipelines are brittle.** In production, upstream data sources change—columns are renamed, data types drift, and "garbage" enters your vector store. 

**Dify-Agentic-Heal** is an intelligent "Gatekeeper" built for the Dify ecosystem. It uses Agentic Workflows to sense, reason, and repair data ingestion failures in real-time before they "poison" your Knowledge Base.

---

## 🚀 The Problem: The "Silent Fail"
Most RAG systems fail silently when:
1. **Schema Drift:** A CSV column `user_email` suddenly becomes `customer_contact`.
2. **Data Corruption:** Null values appear in critical "Context" fields.
3. **Format Mismatch:** Dates or currency formats shift, breaking the retrieval logic.

## 🧠 The Solution: The "Heal-Loop"
This project implements a 4-stage **Agentic ETL** workflow within Dify:

1. **Detection (Validator):** A Python Code Node (using `Great Expectations`) validates incoming data against a "Ground Truth" schema.
2. **Reasoning (Agent Node):** If validation fails, an LLM analyzes the error log and the "broken" data to propose a fix (e.g., "Map 'customer_contact' → 'user_email'").
3. **Transformation (Healer):** A second Code Node executes the repair using `Pandas`, sanitizing the data for the vector store.
4. **Verification (HITL):** Uses Dify’s **Human-in-the-loop** nodes to pause and request admin approval for significant structural changes.

---

## 🛠️ Architecture

```mermaid
graph TD
    A[Raw Data Source] --> B{Validator Node}
    B -- Valid --> C[Knowledge Base Upsert]
    B -- Invalid/Drift --> D[Agent Reasoning Node]
    D --> E[Human-in-the-Loop Review]
    E -- Approved --> F[Transformer Node]
    F --> C
    E -- Rejected --> G[Alert/Discard]
