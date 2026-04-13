"""Monetization strategy generator based on detected AI trends."""

import logging
from datetime import datetime

from . import database as db
from .analyzer import get_trending_keywords, get_category_trends, get_hot_topics

logger = logging.getLogger(__name__)

# Strategy templates keyed by category
STRATEGY_TEMPLATES = {
    "AI Agents": [
        {
            "title": "Build Custom AI Agent Solutions",
            "description": "Develop and sell pre-built AI agent workflows for specific industries (real estate, legal, healthcare). Package as SaaS with monthly subscriptions. Leverage frameworks like LangGraph, CrewAI, or Claude's agent SDK to build multi-step automation that replaces manual processes. Target: $500-5000/mo per client.",
        },
        {
            "title": "AI Agent Consulting & Implementation",
            "description": "Offer consulting services to businesses wanting to adopt AI agents. Charge for architecture design, implementation, and ongoing maintenance. Focus on enterprises struggling to integrate agents into existing workflows. Revenue: $150-300/hr consulting + retainer.",
        },
        {
            "title": "AI Agent Marketplace / Templates",
            "description": "Create a marketplace of plug-and-play agent templates. Users pay per template or subscribe for access. Include agent configs for customer support, data analysis, content creation, code review. Model: freemium + premium templates.",
        },
    ],
    "Vibe Coding": [
        {
            "title": "Vibe Coding Course & Community",
            "description": "Create an online course teaching 'vibe coding' techniques - how to effectively use AI coding assistants (Cursor, Claude Code, Copilot) to 10x productivity. Sell course + community access. Revenue: $97-497 per student + $29/mo community.",
        },
        {
            "title": "AI-Powered Code Generation Service",
            "description": "Offer a service that generates full applications from specifications using AI coding tools. Target non-technical founders and small businesses. Charge per project ($2K-20K) or offer a subscription for ongoing development.",
        },
        {
            "title": "Custom Prompt Libraries for Developers",
            "description": "Curate and sell specialized prompt libraries optimized for different programming languages, frameworks, and use cases. Subscription model: $19-49/mo for access to constantly updated prompt collections.",
        },
    ],
    "Local AI": [
        {
            "title": "Local AI Setup & Deployment Service",
            "description": "Help businesses deploy private, on-premise AI solutions for data security compliance. Install and configure Ollama, vLLM, or custom setups. Charge for setup ($5K-25K) + monthly support retainer.",
        },
        {
            "title": "Privacy-First AI Products",
            "description": "Build desktop/mobile apps that run AI models locally (no cloud). Target privacy-conscious users in healthcare, legal, finance. Sell as one-time purchase ($49-199) or subscription.",
        },
        {
            "title": "Local AI Hardware Consulting",
            "description": "Advise businesses on hardware requirements for running AI locally. Recommend GPU configurations, build custom inference servers. Revenue: consulting fees + affiliate commissions on hardware.",
        },
    ],
    "AI Models": [
        {
            "title": "Fine-Tuned Model Service",
            "description": "Offer custom model fine-tuning as a service. Help businesses create specialized models for their domain (legal, medical, financial). Charge $5K-50K per fine-tuning project + hosting.",
        },
        {
            "title": "Model Evaluation & Benchmarking",
            "description": "Create a paid benchmarking service that helps businesses choose the right AI model for their use case. Compare models on their specific tasks and data. Charge per evaluation report.",
        },
        {
            "title": "AI Model Newsletter / Report",
            "description": "Publish a premium weekly report analyzing new model releases, benchmarks, and practical implications for businesses. Subscription: $29-99/mo for detailed analysis and recommendations.",
        },
    ],
    "Breakthroughs": [
        {
            "title": "Early Adopter Implementation Service",
            "description": "Position as the go-to service for rapidly implementing breakthrough AI technologies. When new capabilities emerge, be first to offer integration services. Premium pricing for speed: $10K-100K projects.",
        },
        {
            "title": "AI Trend Analysis Newsletter",
            "description": "Curate a premium newsletter that explains AI breakthroughs in business terms. Help executives understand which breakthroughs matter for their industry. Revenue: $49-199/mo subscription.",
        },
    ],
    "AI Business": [
        {
            "title": "AI Business Strategy Consulting",
            "description": "Help businesses develop their AI adoption roadmap. Assess current capabilities, identify high-impact opportunities, create implementation plan. Revenue: $5K-50K per engagement.",
        },
        {
            "title": "AI-Powered SaaS Product",
            "description": "Identify underserved niches where AI can solve specific problems. Build focused SaaS products. Target: specific industry verticals where AI adds clear value. Revenue: $29-299/mo subscriptions.",
        },
    ],
    "AI Tools": [
        {
            "title": "Developer Tools & Integrations",
            "description": "Build and sell tools that integrate popular AI frameworks. Create plugins, extensions, middleware that save developers time. Open core model: free base + paid premium features.",
        },
        {
            "title": "RAG-as-a-Service Platform",
            "description": "Build a managed RAG (Retrieval-Augmented Generation) platform for businesses. Handle document ingestion, embedding, retrieval, and generation. Charge based on usage/documents stored.",
        },
    ],
    "Open Source AI": [
        {
            "title": "Open Source + Enterprise Model",
            "description": "Build an open source AI tool that gains community adoption, then offer an enterprise version with support, SLA, and advanced features. Classic open core model.",
        },
        {
            "title": "Open Source AI Support & Training",
            "description": "Offer paid support, training, and deployment services for popular open source AI projects. Target enterprises adopting open models who need expert help.",
        },
    ],
}


def generate_strategies_from_trends() -> list[dict]:
    """Analyze current trends and generate relevant monetization strategies."""
    category_trends = get_category_trends(days=14)
    hot_topics = get_hot_topics(days=7)
    trending_kw = get_trending_keywords(days=7, top_n=10)

    generated = []
    existing = {s["title"] for s in db.get_strategies()}

    # Generate strategies for top trending categories
    sorted_cats = sorted(category_trends.items(), key=lambda x: x[1], reverse=True)

    for category, count in sorted_cats[:5]:
        templates = STRATEGY_TEMPLATES.get(category, [])
        for template in templates:
            if template["title"] in existing:
                continue

            # Customize description with trend data
            trend_basis = f"Based on {count} articles in '{category}' category over the past 14 days."
            if hot_topics:
                top_topic = hot_topics[0]["title"][:80]
                trend_basis += f" Hot topic: '{top_topic}'."
            if trending_kw:
                top_kw = ", ".join(kw for kw, _ in trending_kw[:5])
                trend_basis += f" Trending keywords: {top_kw}."

            strategy_id = db.insert_strategy(
                title=template["title"],
                description=template["description"],
                category=category,
                trend_basis=trend_basis,
            )
            generated.append({
                "id": strategy_id,
                "title": template["title"],
                "category": category,
                "trend_basis": trend_basis,
            })

    logger.info("Generated %d new strategies", len(generated))
    return generated


def get_strategy_summary() -> str:
    """Generate a text summary of current strategies."""
    strategies = db.get_strategies()
    if not strategies:
        return "No strategies generated yet. Fetch articles first to generate trend-based strategies."

    lines = ["# AI Intel Hub - Monetization Strategies\n"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"Total strategies: {len(strategies)}\n")

    by_cat = {}
    for s in strategies:
        cat = s.get("category", "General")
        by_cat.setdefault(cat, []).append(s)

    for cat, strats in sorted(by_cat.items()):
        lines.append(f"\n## {cat}\n")
        for s in strats:
            stars = "+" * s.get("rating", 0) if s.get("rating") else ""
            lines.append(f"### {s['title']} {stars}")
            lines.append(f"{s['description']}\n")
            if s.get("trend_basis"):
                lines.append(f"*Trend basis: {s['trend_basis']}*\n")

    return "\n".join(lines)
