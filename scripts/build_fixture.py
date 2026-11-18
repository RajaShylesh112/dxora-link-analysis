"""Create an explicitly illustrative UI report from a fictional HTML test fixture."""

import json
from pathlib import Path

from app.schemas import LinkResponse, Metadata, ModelOutput, Usage
from app.services.llm_service import validate_evidence
from app.services.website_extractor import observe_seo, parse_page

ROOT = Path(__file__).resolve().parents[1]


def build():
    source, _ = parse_page(
        "https://northstar.example/", (ROOT / "tests/fixtures/agency.html").read_text(), "S1", 22000
    )
    offerings = [
        (
            "Brand strategy",
            "We clarify positioning, brand identity and messaging for growing businesses.",
            "Early-stage businesses",
            "Founders refining an offering",
            "A clearer and more consistent brand story",
        ),
        (
            "Website design",
            "We design accessible, responsive websites that make complex offerings easy to understand.",
            "Professional services",
            "Teams improving their digital presence",
            "A more understandable and accessible customer experience",
        ),
        (
            "Web development",
            "We build reliable web applications and customer portals for small business teams.",
            "Business software",
            "Small teams needing customer-facing software",
            "A dedicated digital workflow for customers",
        ),
        (
            "E-commerce development",
            "We build online stores with straightforward product discovery and checkout experiences.",
            "Retail",
            "Retail businesses launching online stores",
            "Simpler product browsing and checkout",
        ),
        (
            "Search optimization",
            "We improve on-page content, website structure and metadata to support organic discovery.",
            "Cross-industry",
            "Businesses improving organic discovery",
            "Clearer content and metadata for search discovery",
        ),
    ]
    competitors = [
        {
            "name": "thoughtbot",
            "comparison": "A possible comparison for startup product design and development; validate fit against Northstar's project size and budgets.",
            "potential_strengths": [
                "Research whether its product development experience matches the buyer's needs."
            ],
            "potential_gaps": ["Compare engagement scope and suitability for smaller website projects."],
            "basis": "ai_suggestion",
            "verification_needed": True,
        },
        {
            "name": "ustwo",
            "comparison": "A possible reference for digital product design; competitive overlap needs independent validation.",
            "potential_strengths": ["Review its public product portfolio and design process."],
            "potential_gaps": ["Check whether the engagement model fits a small business launch."],
            "basis": "ai_suggestion",
            "verification_needed": True,
        },
        {
            "name": "Clay",
            "comparison": "A possible comparison for brand and digital experience projects; pricing and current service coverage are unverified.",
            "potential_strengths": ["Review brand identity and digital design case studies."],
            "potential_gaps": ["Validate the availability and suitability of ongoing small-team support."],
            "basis": "ai_suggestion",
            "verification_needed": True,
        },
    ]
    queries = [
        (
            "digital product studio for startups",
            ["Google"],
            "Service discovery",
            "Startup founders",
            "Connects the explicit startup audience with design and development.",
        ),
        (
            "small business website design team",
            ["Facebook"],
            "Business discovery",
            "Small business owners",
            "Matches the website design service and small-business positioning.",
        ),
        (
            "accessible website design inspiration",
            ["Instagram"],
            "Visual inspiration",
            "Brand and marketing teams",
            "Highlights the studio's stated accessible design focus.",
        ),
        (
            "customer portal development for small teams",
            ["LinkedIn"],
            "B2B solution research",
            "Operations leaders",
            "Matches the explicitly offered customer portal development.",
        ),
        (
            "startup brand positioning and web launch",
            ["X"],
            "Advice and service discovery",
            "Early-stage founders",
            "Connects positioning work with the startup launch journey.",
        ),
    ]
    data = {
        "brand": {
            "name": "Northstar Studio",
            "category": "Digital product design and development",
            "summary": "A fictional studio helping startups and small businesses with brand strategy, websites, web applications, online stores and search optimization.",
            "products_and_services": [name for name, *_ in offerings],
            "evidence": [
                {
                    "source_id": "S1",
                    "quote": "Northstar Studio helps startups and small businesses design, build and improve digital products.",
                }
            ],
        },
        "analysis": {
            "competitor_analysis": {
                "brand_overview": "Northstar combines research, design and development for early-stage teams. Its website describes a small senior team and five complementary offerings.",
                "competitors": competitors,
                "strengths": [
                    "Integrated brand, design and development offering is stated on the site.",
                    "The website explicitly focuses on startups and small businesses.",
                    "Accessible website design is an explicit service commitment.",
                ],
                "opportunities": [
                    "Publish project examples showing the problem, decisions and results.",
                    "Create focused landing pages for customer portals and e-commerce builds.",
                    "Clarify engagement scope and the handoff process for small teams.",
                ],
                "limitations": "Illustrative fixture. Competitors are suggestions only, with no independent competitor research, verified weaknesses, pricing or market-share claims.",
            },
            "target_search_queries": [
                {"query": q, "platforms": p, "intent": i, "target_audience": a, "business_relevance": r}
                for q, p, i, a, r in queries
            ],
            "seo_improvements": {
                "primary_keyword": "digital product studio for startups",
                "secondary_keywords": [
                    "small business website design",
                    "customer portal development",
                    "startup brand strategy",
                ],
                "long_tail_keywords": [
                    "accessible website design for small businesses",
                    "e-commerce development for growing retailers",
                    "brand positioning for an early-stage startup",
                ],
                "business_keywords": [
                    "digital product design",
                    "responsive websites",
                    "on-page search optimization",
                ],
                "recommended_title": "Digital Product Studio for Startups | Northstar Studio",
                "title_rationale": "Lead with the business category and stated customer group, then retain the brand name.",
                "meta_description": "Northstar Studio helps startups and small businesses clarify their brand, design accessible websites, and build digital products for their next stage.",
                "supporting_content": [
                    {
                        "title": "Customer portals for small business teams",
                        "content_type": "service_page",
                        "rationale": "Develop an explicitly offered service into a page with use cases, project scope and FAQs.",
                    },
                    {
                        "title": "What to prepare before a website project",
                        "content_type": "faq",
                        "rationale": "Help the stated small-business audience understand goals, assets and launch decisions.",
                    },
                ],
                "priority_actions": [
                    "Give each core service a dedicated, descriptive landing page.",
                    "Add relevant project case studies without inventing outcome metrics.",
                    "Review the meaning of each image before adding alt text; decorative images may remain empty.",
                ],
            },
            "top_services": [
                {
                    "name": name,
                    "description": description,
                    "target_industry": industry,
                    "target_customer": customer,
                    "main_benefit": benefit,
                    "basis": "observed",
                    "evidence": [{"source_id": "S1", "quote": description}],
                    "inference_reason": "",
                }
                for name, description, industry, customer, benefit in offerings
            ],
            "target_audience": {
                "primary_audience": [
                    "Startup founders planning a digital product",
                    "Small business owners improving their website",
                ],
                "secondary_audience": [
                    "Retailers preparing an online store",
                    "Marketing teams improving brand clarity",
                ],
                "industries": ["Professional services", "Retail", "Business software"],
                "business_types": ["Startups", "Small businesses"],
                "customer_profiles": [
                    "A founder coordinating a first product launch",
                    "A small team replacing a confusing website",
                ],
                "geographical_focus": None,
                "geographical_evidence": [],
                "customer_needs": [
                    "A coherent brand and launch story",
                    "A reliable customer-facing digital experience",
                    "Clearer organic discovery",
                ],
                "interests": [
                    "Product design",
                    "Accessible websites",
                    "Business growth through digital services",
                ],
                "marketing_segments": [
                    "Founders researching a product launch",
                    "Small teams evaluating a website redesign",
                    "Retailers comparing e-commerce implementation partners",
                ],
                "inference_notes": "Startups and small businesses are explicit in the fixture. Industry segments, customer profiles and interests are illustrative deductions, not measured demographic data. No location is stated.",
            },
        },
    }
    output = ModelOutput.model_validate(data)
    validate_evidence(output, [source])
    (ROOT / "tests/fixtures/model-output.json").write_text(json.dumps(output.model_dump(), indent=2) + "\n")
    report = LinkResponse(
        website=source.url,
        brand=output.brand,
        analysis=output.analysis,
        sources=[source],
        seo_observations=observe_seo([source]),
        metadata=Metadata(
            request_id="illustrative-fixture-not-live",
            generated_at="2026-11-18T00:00:00+00:00",
            elapsed_ms=0,
            provider="OpenRouter",
            model_requested="openrouter/free",
            model_used="illustrative-handcrafted-fixture",
            cached=False,
            cache_age_seconds=0,
            usage=Usage(input_tokens=None, output_tokens=None, reported_cost_usd=None),
            warnings=[
                "Handcrafted illustrative test fixture; no live website or LLM call.",
                "Competitor suggestions are not independently verified.",
                "Audience deductions are labeled; no search volume or ranking data is present.",
            ],
            competitor_research="ai_suggestions_not_independently_verified",
        ),
    )
    (ROOT / "app/static/sample-report.json").write_text(report.model_dump_json(indent=2) + "\n")
    print("Created clearly labeled illustrative fixture; all quotes match fictional website HTML.")


if __name__ == "__main__":
    build()
