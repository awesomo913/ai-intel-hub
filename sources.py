"""Curated catalog of 50+ AI news sources - RSS feeds and scrape targets."""

# Source credibility weights for scoring.
# Tier 1 (1.2x): Primary research sources
# Tier 2 (1.0x): Major tech news
# Tier 3 (0.8x): Aggregators and newsletters
SOURCE_WEIGHTS: dict[str, float] = {
    # Tier 1
    "arxiv.org": 1.2,
    "openai.com": 1.2,
    "deepmind.com": 1.2,
    "deepmind.google": 1.2,
    "anthropic.com": 1.2,
    "research.google": 1.2,
    "blog.google": 1.2,
    # Tier 2
    "techcrunch.com": 1.0,
    "venturebeat.com": 1.0,
    "theverge.com": 1.0,
    "arstechnica.com": 1.0,
    "wired.com": 1.0,
    "technologyreview.com": 1.0,
    "news.ycombinator.com": 1.0,
    "github.com": 1.0,
    "huggingface.co": 1.0,
    "paperswithcode.com": 1.0,
    "reddit.com": 1.0,
    # Tier 3
    "substack.com": 0.8,
    "beehiiv.com": 0.8,
    "newsletter": 0.8,
    "medium.com": 0.8,
    "towardsdatascience.com": 0.8,
    "producthunt.com": 0.8,
    "cbinsights.com": 0.8,
    "aibusiness.com": 0.8,
    "theneurondaily.com": 0.8,
}


def get_source_weight(url: str) -> float:
    """Return the credibility weight (0.8–1.2) for a given source URL."""
    if not url:
        return 1.0
    url_lower = url.lower()
    for domain, weight in SOURCE_WEIGHTS.items():
        if domain in url_lower:
            return weight
    return 1.0

# Each source: (name, website_url, feed_url, category)
DEFAULT_SOURCES = [
    # === MAJOR AI NEWS (8) ===
    ("Hacker News - AI", "https://news.ycombinator.com", "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+machine+learning", "AI News"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/", "https://techcrunch.com/category/artificial-intelligence/feed/", "AI News"),
    ("The Verge", "https://www.theverge.com", "https://www.theverge.com/rss/index.xml", "AI News"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/", "https://venturebeat.com/category/ai/feed/", "AI News"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "AI News"),
    ("Ars Technica", "https://arstechnica.com/ai/", "https://feeds.arstechnica.com/arstechnica/technology-lab", "AI News"),
    ("Wired AI", "https://www.wired.com/tag/artificial-intelligence/", "https://www.wired.com/feed/tag/ai/latest/rss", "AI News"),
    ("The Information AI", "https://www.theinformation.com", "https://www.theinformation.com/feed", "AI News"),

    # === AI RESEARCH (7) ===
    ("ArXiv cs.AI", "https://arxiv.org/list/cs.AI/recent", "https://rss.arxiv.org/rss/cs.AI", "AI Research"),
    ("ArXiv cs.CL (NLP)", "https://arxiv.org/list/cs.CL/recent", "https://rss.arxiv.org/rss/cs.CL", "AI Research"),
    ("ArXiv cs.LG (ML)", "https://arxiv.org/list/cs.LG/recent", "https://rss.arxiv.org/rss/cs.LG", "AI Research"),
    ("Google AI Blog", "https://blog.google/technology/ai/", "https://blog.google/technology/ai/rss/", "AI Research"),
    ("DeepMind Blog", "https://deepmind.google/discover/blog/", "https://deepmind.google/blog/rss.xml", "AI Research"),
    ("Papers With Code", "https://paperswithcode.com/", "https://paperswithcode.com/latest", "AI Research"),
    ("Distill.pub", "https://distill.pub/", "https://distill.pub/rss.xml", "AI Research"),

    # === AI COMPANIES (7) ===
    ("OpenAI Blog", "https://openai.com/blog", "https://openai.com/blog/rss.xml", "AI Companies"),
    ("Hugging Face Blog", "https://huggingface.co/blog", "https://huggingface.co/blog/feed.xml", "AI Companies"),
    ("Microsoft AI Blog", "https://blogs.microsoft.com/ai/", "https://blogs.microsoft.com/ai/feed/", "AI Companies"),
    ("NVIDIA AI Blog", "https://blogs.nvidia.com/blog/category/deep-learning/", "https://blogs.nvidia.com/blog/category/deep-learning/feed/", "AI Companies"),
    ("Stability AI Blog", "https://stability.ai/news", "https://stability.ai/news/rss.xml", "AI Companies"),
    ("Cohere Blog", "https://cohere.com/blog", "https://cohere.com/blog/rss.xml", "AI Companies"),
    ("Mistral Blog", "https://mistral.ai/news/", "https://mistral.ai/feed.xml", "AI Companies"),

    # === AI TOOLS & DEV (5) ===
    ("GitHub Trending", "https://github.com/trending", "", "AI Tools"),
    ("LangChain Blog", "https://blog.langchain.dev/", "https://blog.langchain.dev/rss/", "AI Tools"),
    ("Vercel AI Blog", "https://vercel.com/blog", "https://vercel.com/atom", "AI Tools"),
    ("Replicate Blog", "https://replicate.com/blog", "https://replicate.com/blog/rss", "AI Tools"),
    ("Modal Blog", "https://modal.com/blog", "https://modal.com/blog/feed.xml", "AI Tools"),

    # === LOCAL AI / OPEN SOURCE (5) ===
    ("Reddit r/LocalLLaMA", "https://www.reddit.com/r/LocalLLaMA/", "https://www.reddit.com/r/LocalLLaMA/.rss", "Local AI"),
    ("Reddit r/selfhosted", "https://www.reddit.com/r/selfhosted/", "https://www.reddit.com/r/selfhosted/.rss", "Local AI"),
    ("Reddit r/StableDiffusion", "https://www.reddit.com/r/StableDiffusion/", "https://www.reddit.com/r/StableDiffusion/.rss", "Open Source AI"),
    ("Reddit r/opensource", "https://www.reddit.com/r/opensource/", "https://www.reddit.com/r/opensource/.rss", "Open Source AI"),
    ("Hugging Face Papers", "https://huggingface.co/papers", "https://huggingface.co/papers/rss", "Open Source AI"),

    # === AI AGENTS (4) ===
    ("Reddit r/AI_Agents", "https://www.reddit.com/r/AI_Agents/", "https://www.reddit.com/r/AI_Agents/.rss", "AI Agents"),
    ("Reddit r/AutoGPT", "https://www.reddit.com/r/AutoGPT/", "https://www.reddit.com/r/AutoGPT/.rss", "AI Agents"),
    ("Reddit r/LangChain", "https://www.reddit.com/r/LangChain/", "https://www.reddit.com/r/LangChain/.rss", "AI Agents"),
    ("Reddit r/CrewAI", "https://www.reddit.com/r/CrewAI/", "https://www.reddit.com/r/CrewAI/.rss", "AI Agents"),

    # === VIBE CODING (4) ===
    ("Reddit r/ChatGPTCoding", "https://www.reddit.com/r/ChatGPTCoding/", "https://www.reddit.com/r/ChatGPTCoding/.rss", "Vibe Coding"),
    ("Reddit r/ClaudeAI", "https://www.reddit.com/r/ClaudeAI/", "https://www.reddit.com/r/ClaudeAI/.rss", "Vibe Coding"),
    ("Reddit r/CursorAI", "https://www.reddit.com/r/cursor/", "https://www.reddit.com/r/cursor/.rss", "Vibe Coding"),
    ("Reddit r/CodingWithAI", "https://www.reddit.com/r/CodingWithAI/", "https://www.reddit.com/r/CodingWithAI/.rss", "Vibe Coding"),

    # === GENERAL AI REDDIT (5) ===
    ("Reddit r/MachineLearning", "https://www.reddit.com/r/MachineLearning/", "https://www.reddit.com/r/MachineLearning/.rss", "AI Research"),
    ("Reddit r/artificial", "https://www.reddit.com/r/artificial/", "https://www.reddit.com/r/artificial/.rss", "AI News"),
    ("Reddit r/singularity", "https://www.reddit.com/r/singularity/", "https://www.reddit.com/r/singularity/.rss", "Breakthroughs"),
    ("Reddit r/OpenAI", "https://www.reddit.com/r/OpenAI/", "https://www.reddit.com/r/OpenAI/.rss", "AI Companies"),
    ("Reddit r/ArtificialInteligence", "https://www.reddit.com/r/ArtificialInteligence/", "https://www.reddit.com/r/ArtificialInteligence/.rss", "AI News"),

    # === NEWSLETTERS & SUBSTACKS (6) ===
    ("Import AI", "https://importai.substack.com/", "https://importai.substack.com/feed", "AI Research"),
    ("AI Business", "https://aibusiness.com/", "https://aibusiness.com/rss.xml", "AI Business"),
    ("Towards Data Science", "https://towardsdatascience.com/", "https://towardsdatascience.com/feed", "AI Research"),
    ("Ahead of AI (Seb Raschka)", "https://magazine.sebastianraschka.com/", "https://magazine.sebastianraschka.com/feed", "AI Research"),
    ("The Neuron", "https://www.theneurondaily.com/", "https://www.theneurondaily.com/feed", "AI News"),
    ("Ben's Bites", "https://bensbites.beehiiv.com/", "https://bensbites.beehiiv.com/feed", "AI Business"),

    # === AI BUSINESS & FUNDING (3) ===
    ("CB Insights AI", "https://www.cbinsights.com/research/artificial-intelligence/", "https://www.cbinsights.com/rss/content/artificial-intelligence", "AI Business"),
    ("Y Combinator News", "https://news.ycombinator.com", "https://hnrss.org/newest?q=Show+HN+AI+OR+Launch+HN+AI", "AI Business"),
    ("Product Hunt AI", "https://www.producthunt.com/topics/artificial-intelligence", "https://www.producthunt.com/feed?category=artificial-intelligence", "AI Business"),
]


def get_default_sources() -> list[tuple[str, str, str, str]]:
    """Return list of (name, url, feed_url, category) tuples."""
    return DEFAULT_SOURCES
