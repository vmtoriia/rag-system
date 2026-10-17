# Architecture

The architecture is described with the **C4 model** (https://c4model.com), which shows a system at
increasing levels of detail, like zooming in on a map:

1. **System context**: the system as one box, and who or what it interacts with.
2. **Containers**: the separately running programs and data stores inside the system.
3. **Components**: the parts inside the most important container, the chat application.
4. **Code**: not drawn. At this level the source code itself is the documentation.

A runtime diagram (one conversation turn, step by step) completes the static views.

**Status in the diagrams:** solid border = implemented, dashed border = planned.

## Requirements that shape the design

The system is a research prototype, not a product. Its purpose is to measure how short-term and
long-term memory affect anaphora resolution and personalisation. This leads to four requirements:

- **Switchable memory.** Each memory type can be turned on and off, so the four experiment
  configurations (0 none, 1 short-term, 2 long-term, 3 both) differ in exactly one thing at a time.
- **Comparable runs.** All configurations run on the same test dialogues, data and models.
- **Traceable steps.** Every intermediate result (rewritten question, filters, retrieved products,
  prompt, answer) is recorded, so errors can be located and measured.
- **Free and local.** Everything runs on one laptop (16 GB RAM, 4 GB GPU) with open-source models.

## Level 1: System context

```mermaid
flowchart TB
    user["<b>User</b><br/><i>Person</i><br/>Asks about food products;<br/>has allergies, a diet, dislikes"]
    researcher["<b>Researcher</b><br/><i>Person</i><br/>Runs the test dialogues and<br/>evaluates the results"]
    system["<b>Food assistant with memory</b><br/><i>Software system</i><br/>Answers questions about products,<br/>remembers the conversation and the user profile"]
    off["<b>Open Food Facts</b><br/><i>External data source</i><br/>Product database export<br/>(downloaded once from Hugging Face)"]
    hf["<b>Hugging Face Hub</b><br/><i>External model source</i><br/>Embedding model download"]

    user -- "asks questions, states preferences" --> system
    researcher -- "runs experiments, reads results" --> system
    system -- "downloads product data (once)" --> off
    system -- "downloads the embedding model (once)" --> hf

    classDef person fill:#2f6b5a,stroke:#1d4a3d,color:#ffffff
    classDef sys fill:#3b6ea5,stroke:#24486e,color:#ffffff
    classDef ext fill:#8a8a85,stroke:#5e5e5a,color:#ffffff
    class user,researcher person
    class system sys
    class off,hf ext
```

The system talks to the outside world only during setup (two downloads). After that it works offline.

## Level 2: Containers

```mermaid
flowchart TB
    user["<b>User / Researcher</b><br/><i>Person</i>"]

    subgraph sys ["Food assistant with memory"]
        pipeline["<b>Data pipeline</b><br/><i>Python scripts 01-03b</i><br/>Selects, cleans and describes products"]
        files[("<b>Corpus files</b><br/><i>Parquet files in data/</i><br/>food.parquet → corpus.parquet")]
        indexer["<b>Indexer</b><br/><i>Python script 04</i><br/>Embeds doc_text, loads the database"]
        db[("<b>Database</b><br/><i>PostgreSQL + pgvector, Docker</i><br/>Products, embeddings, user profiles")]
        chat["<b>Chat application</b><br/><i>Python, command line</i><br/>RAG with short- and long-term memory"]
        llm["<b>Language model server</b><br/><i>Ollama, qwen2.5:3b</i><br/>Rewrites questions, writes answers"]
        runner["<b>Experiment runner</b><br/><i>Python</i><br/>Runs test dialogues in configs 0-3"]
        results[("<b>Results</b><br/><i>Files in results/</i><br/>Traces, scores")]
    end

    pipeline -- "writes" --> files
    indexer -- "reads" --> files
    indexer -- "writes products + vectors" --> db
    user -- "chats" --> chat
    user -- "starts" --> runner
    runner -- "sends test dialogues,<br/>chooses configuration" --> chat
    chat -- "hybrid search, profiles (SQL)" --> db
    chat -- "prompts (HTTP)" --> llm
    runner -- "writes" --> results

    classDef person fill:#2f6b5a,stroke:#1d4a3d,color:#ffffff
    classDef done fill:#3b6ea5,stroke:#24486e,color:#ffffff
    classDef planned fill:#dbe6f2,stroke:#3b6ea5,color:#1f1f1c,stroke-dasharray:6 4
    class user person
    class pipeline,files,llm done
    class indexer,db,chat,runner,results planned
```

| Container | Technology | Responsibility | Status |
|---|---|---|---|
| Data pipeline | Python, DuckDB | Steps 1-3b: select Czech products, filter, clean, build `doc_text` | Implemented |
| Corpus files | Parquet | Raw export and the final corpus (5,888 products) | Implemented |
| Indexer | Python, sentence-transformers | Step 4: turn `doc_text` into vectors, load the database | Prepared, not run |
| Database | PostgreSQL + pgvector in Docker | Products with allergen columns and vectors; user profiles | Planned |
| Chat application | Python | One conversation turn: memory, retrieval, prompt, answer | Planned |
| Language model server | Ollama, qwen2.5:3b | Text generation, running locally on the GPU | Installed and tested |
| Experiment runner | Python | Runs the same dialogues through configurations 0-3 | Planned |
| Results | Files (JSON/CSV) | Step-by-step traces and evaluation scores | Planned |

The embedding model (multilingual-e5-small) is not a separate container: it is a library loaded
inside the indexer and the chat application.

## Level 3: Components of the chat application

```mermaid
flowchart LR
    input(["User message"])
    output(["Answer"])

    subgraph chat ["Chat application"]
        stm["<b>Conversation memory</b><br/><i>short-term</i><br/>Recent turns,<br/>products shown"]
        profile["<b>Profile memory</b><br/><i>long-term</i><br/>Allergies, diet, dislikes<br/><i>stored in the database</i>"]
        rewriter["<b>Query rewriter</b><br/>Turns a follow-up into<br/>a standalone question<br/><i>uses the language model</i>"]
        filters["<b>Filter builder</b><br/>Profile → exact rules<br/>(exclude en:milk)"]
        retriever["<b>Retriever</b><br/>Filters, then ranks<br/>by meaning<br/><i>SQL query to the database</i>"]
        prompt["<b>Prompt builder</b><br/>Question + products<br/>+ answering rules"]
        generator["<b>Answer generator</b><br/><i>uses the language model</i>"]
    end

    input --> rewriter
    rewriter -- "question" --> retriever
    retriever -- "top products" --> prompt
    prompt --> generator
    generator --> output

    stm -. "conversation" .-> rewriter
    profile -. "profile" .-> filters
    filters -. "filters" .-> retriever
    generator -. "store turn" .-> stm

    classDef planned fill:#dbe6f2,stroke:#3b6ea5,color:#1f1f1c,stroke-dasharray:6 4
    classDef memory fill:#f6e3c6,stroke:#a3440f,color:#1f1f1c,stroke-dasharray:6 4
    classDef io fill:#ffffff,stroke:#8a8a85,color:#1f1f1c
    class rewriter,retriever,prompt,generator,filters planned
    class stm,profile memory
    class input,output io
```

The solid arrows are the main path that every message takes. The dotted arrows come from the two
memory types (orange), which are the subject of the experiment; the configuration (0-3) switches them
on or off. When short-term memory is off, the question goes to the retriever unchanged. When long-term memory is off, no profile filters
are applied. A trace logger (not drawn, to keep the diagram readable) records the input and output
of every component.

| Component | Responsibility | Used in configuration |
|---|---|---|
| Conversation memory | Keeps recent turns and the products already shown | 1, 3 |
| Query rewriter | Uses the conversation to turn a follow-up into a standalone question | 1, 3 |
| Profile memory | Stores and updates allergies, diet and dislikes across conversations | 2, 3 |
| Filter builder | Turns the profile into exact database conditions | 2, 3 |
| Retriever | Applies the filters, then ranks products by vector similarity | all |
| Prompt builder | Combines the question, the retrieved products and answering rules | all |
| Answer generator | Sends the prompt to the language model and returns the answer | all |
| Trace logger | Records the input and output of every step for evaluation | all |

## Runtime view: one conversation turn (configuration 3)

```mermaid
sequenceDiagram
    actor U as User
    participant C as Chat application
    participant M as Memory (short + long)
    participant L as Language model
    participant D as Database

    U->>C: "Is it gluten-free?"
    C->>M: get recent turns and profile
    M-->>C: last product: Alpro oat drink, profile: allergic to milk
    C->>L: rewrite the question using the conversation
    L-->>C: "Is Alpro oat drink gluten-free?"
    C->>D: search: exclude milk, rank by similarity
    D-->>C: top 5 products
    C->>L: question + products + rules
    L-->>C: answer
    C->>M: store this turn
    C-->>U: answer
```

## Key decisions

| Decision | Alternative considered | Reason |
|---|---|---|
| Python | Java with Spring AI | Main libraries for embeddings and evaluation are in Python; less code for a prototype |
| Local models (Ollama, multilingual-e5-small) | Paid cloud API | Free, reproducible, data stays local; small models are enough to compare memory configurations |
| One database for vectors, filters and profiles (PostgreSQL + pgvector) | Separate vector database and search engine | Exact allergen filters and similarity search in one SQL query; fewer moving parts |
| Exact similarity search, no approximate index | HNSW index | 5,888 products are searched in milliseconds; no approximation errors that would distort the evaluation |
| Strict filters for allergies, similarity only for ranking | Similarity search only | "No milk" must be a hard rule; similarity search alone can return milk products |
| Command-line chat | Web interface | The experiment does not need one; a web interface can be added later if required |
| Own code, no framework (LangChain etc.) | RAG framework | Every step stays visible and measurable, which the evaluation needs |
