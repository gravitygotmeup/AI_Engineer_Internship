# AI Intelligence Pipeline

A production-grade data pipeline that collects, processes, and structures AI ecosystem data from multiple sources including research papers, startups, products, news, and job listings.

---

## What This Does

This pipeline scrapes and processes data from:

- **Research Papers** (arXiv) with GitHub star counts
- **Startups** (Y Combinator directory)
- **AI Products** with pricing models
- **News Articles** (24-hour freshness guaranteed)
- **Job Listings** (24-hour freshness guaranteed)

The extracted data is structured into a consistent JSON schema and exported as CSV files for analysis.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: ACQUISITION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐     │
│  │  Papers   │  │ Startups  │  │ Products  │  │ News/Jobs │     │
│  │  Crawler  │  │  Crawler  │  │  Crawler  │  │  Crawler  │     │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘     │
│        └──────────────┼──────────────┼──────────────┘           │
│                       ▼                                         │
│              ┌──────────────────┐                               │
│              │   Async Workers  │                               │
│              │   (Concurrent)   │                               │
│              └────────┬─────────┘                               │
└───────────────────────┼─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 2: PROCESSING                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────┐         │
│  │           LLM Orchestrator (Fallback Chain)        │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │         │
│  │  │  Gemini  │→ │   Groq   │→ │ DeepSeek │          │         │
│  │  └──────────┘  └──────────┘  └──────────┘          │         │
│  │         (Retry + Rate Limit + Chunking)            │         │
│  └────────────────────────────────────────────────────┘         │
│                        ▼                                        │
│              ┌──────────────────┐                               │
│              │  Entity Resolver │                               │
│              │ (Fuzzy Matching) │                               │
│              └────────┬─────────┘                               │
└───────────────────────┼─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 3: STORAGE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ startups │  │ products │  │  papers  │  │  news/   │         │
│  │   .csv   │  │   .csv   │  │   .csv   │  │ jobs.csv │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                 │
│  Plus: entity_mapping.csv, summary.csv                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd ai_engineer_demo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Create a `.env` file with your API keys:

```env
# LLM API Keys
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
DEEPSEEK_API_KEY=your_deepseek_key

# Scraping Settings
MAX_CONCURRENT_REQUESTS=20
REQUEST_TIMEOUT=30
```

### Running the Pipeline

```bash
python scripts/run_pipeline.py
```

---

## 📊 Output

All results are saved in `data/output/`:

| File | Content | Records |
|------|---------|---------|
| `startups.csv` | Startup entities with canonical names | 1,000+ |
| `products.csv` | AI products with pricing models | 1,000+ |
| `papers.csv` | Research papers with GitHub stars | 1,000+ |
| `news.csv` | Fresh news (last 24 hours) | Varies |
| `jobs.csv` | Fresh job listings (last 24 hours) | Varies |
| `entity_mapping.csv` | Raw → Canonical name mapping | All mappings |

---

## 🔧 Key Components

### Crawlers

| Crawler | Source | Data |
|---------|--------|------|
| `paper_crawler.py` | arXiv API | Papers with GitHub stars |
| `startup_crawler.py` | Y Combinator | Startup names and descriptions |
| `product_crawler.py` | Product directories | Products with pricing |
| `news_crawler.py` | RSS/APIs | Fresh news articles |
| `job_crawler.py` | Job APIs | Fresh job listings |

### LLM Orchestration

The pipeline uses a fallback chain for reliability:
1. **Gemini Flash** - Primary model
2. **Groq Llama** - Fallback if Gemini fails
3. **DeepSeek** - Final fallback

Features:
- Intelligent chunking (prevents 413 errors)
- Rate limiting with exponential backoff
- Response caching
- Model usage tracking

### Entity Resolution

- 79+ seed entities loaded
- Fuzzy string matching
- Canonical name mapping
- Resolution logging for transparency

---

## Project Structure

```
ai_engineer_demo/
├── src/
│   ├── crawlers/          # Data collection
│   │   ├── base_crawler.py
│   │   ├── paper_crawler.py
│   │   ├── startup_crawler.py
│   │   ├── product_crawler.py
│   │   ├── news_crawler.py
│   │   └── job_crawler.py
│   ├── llm/               # LLM orchestration
│   │   ├── orchestrator.py
│   │   ├── chunking.py
│   │   ├── rate_limiter.py
│   │   └── models/
│   │       ├── gemini.py
│   │       ├── groq.py
│   │       └── deepseek.py
│   ├── resolvers/         # Entity resolution
│   │   └── entity_resolver.py
│   ├── storage/           # Output generation
│   │   └── output_generator.py
│   └── utils/             # Utilities
│       ├── anti_bot.py
│       ├── date_parser.py
│       └── logger.py
├── scripts/
│   └── run_pipeline.py
├── data/
│   ├── seed/              # Seed entities
│   └── output/            # Generated CSVs
└── requirements.txt
```

---

## Technology Stack

- **Python 3.9+** - Core language
- **asyncio + aiohttp** - Async HTTP requests
- **Playwright** - Browser automation for JS-heavy sites
- **BeautifulSoup4** - HTML parsing
- **Gemini/Groq/DeepSeek** - LLM extraction
- **FuzzyWuzzy** - Entity resolution
- **Pandas** - Data processing
- **Loguru** - Structured logging
- **Tenacity** - Retry logic

---

## Scaling

The architecture supports scaling to 500,000+ records by:

- **Horizontal Scaling** - Adding more workers
- **Sharding** - Splitting data by type
- **Caching** - Redis for speed
- **Message Queues** - Decoupling components
- **Database Sharding** - PostgreSQL partitions

See `architecture.pdf` for detailed scaling strategy.

---

## Contributing

This is a demo task submission. For questions or feedback, please open an issue.

---

## Acknowledgments

- arXiv for the research paper API
- Y Combinator for startup data
- Google, Groq, and DeepSeek for LLM APIs

---

*Built for the AI Engineer Demo Task - GraphOne / FrontierAtlas*
