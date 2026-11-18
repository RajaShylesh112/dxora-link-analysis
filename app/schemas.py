from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.url_guard import normalize_url


def informative_text(value: str) -> str:
    if not any(character.isalnum() for character in value):
        raise ValueError("Text must contain meaningful letters or digits")
    return value


Text = Annotated[str, Field(min_length=1, max_length=1500), AfterValidator(informative_text)]
Profile = Annotated[str, Field(min_length=15, max_length=1000), AfterValidator(informative_text)]
Short = Annotated[str, Field(min_length=1, max_length=300)]
Items = Annotated[list[Text], Field(max_length=12)]
Platforms = Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinkRequest(StrictModel):
    url: str = Field(min_length=1, max_length=2048, strict=True)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        return normalize_url(value)


class Evidence(StrictModel):
    source_id: str = Field(pattern=r"^S[1-5]$")
    quote: str = Field(min_length=10, max_length=500)


class Brand(StrictModel):
    name: Short
    category: Short
    summary: Text
    products_and_services: Items
    evidence: list[Evidence] = Field(min_length=1, max_length=5)


class Competitor(StrictModel):
    name: Short
    comparison: Text
    potential_strengths: Items
    potential_gaps: Items
    basis: Literal["ai_suggestion"]
    verification_needed: Literal[True]


class CompetitorAnalysis(StrictModel):
    brand_overview: Text
    competitors: list[Competitor] = Field(max_length=5)
    strengths: Items
    opportunities: Items
    limitations: Text


class SearchQuery(StrictModel):
    query: Short
    platforms: list[Platforms] = Field(min_length=1, max_length=5)
    intent: Short
    business_relevance: Text
    target_audience: Short


class SupportingContent(StrictModel):
    title: Short
    content_type: Literal["service_page", "industry_page", "faq", "blog", "location_page", "article"]
    rationale: Text


class SEOImprovements(StrictModel):
    primary_keyword: Short
    secondary_keywords: Items
    long_tail_keywords: Items
    business_keywords: Items
    recommended_title: str = Field(min_length=1, max_length=80)
    title_rationale: Text
    meta_description: str = Field(min_length=1, max_length=200)
    supporting_content: list[SupportingContent] = Field(min_length=1, max_length=8)
    priority_actions: Items


class Service(StrictModel):
    name: Short
    description: Text
    target_industry: Short
    target_customer: Short
    main_benefit: Text
    basis: Literal["observed", "inferred_recommendation"]
    evidence: list[Evidence] = Field(max_length=3)
    inference_reason: str = Field(max_length=1000)

    @model_validator(mode="after")
    def evidence_required(self):
        if self.basis == "observed" and not self.evidence:
            raise ValueError("Observed services require evidence")
        if self.basis == "inferred_recommendation" and not self.inference_reason.strip():
            raise ValueError("Inferred recommendations require a reason")
        return self


class Audience(StrictModel):
    primary_audience: Items
    secondary_audience: Items
    industries: Items
    business_types: Items
    customer_profiles: list[Profile] = Field(min_length=1, max_length=12)
    geographical_focus: str | None = Field(max_length=1000)
    geographical_evidence: list[Evidence] = Field(max_length=3)
    customer_needs: Items
    interests: Items
    marketing_segments: Items
    inference_notes: Text

    @model_validator(mode="after")
    def location_requires_evidence(self):
        if self.geographical_focus is not None and not self.geographical_evidence:
            raise ValueError("Geographical focus requires website evidence")
        return self


class Analysis(StrictModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEOImprovements
    top_services: list[Service] = Field(min_length=1, max_length=5)
    target_audience: Audience

    @model_validator(mode="after")
    def all_platforms_covered(self):
        queries = self.target_search_queries
        if {p for query in queries for p in query.platforms} != {
            "Google",
            "Facebook",
            "Instagram",
            "LinkedIn",
            "X",
        }:
            raise ValueError("Five queries must collectively cover all five platforms")
        if len({query.query.casefold() for query in queries}) != 5:
            raise ValueError("Search queries must be distinct")
        return self


class ModelOutput(StrictModel):
    brand: Brand
    analysis: Analysis


class Source(StrictModel):
    id: str
    url: str
    title: str
    meta_description: str
    h1: list[str]
    h2: list[str]
    text: str
    canonical: str | None
    image_count: int
    images_missing_alt: int
    word_count: int
    content_hash: str
    truncated: bool


class SEOObservation(StrictModel):
    source_id: str
    check: str
    observed: str
    recommendation: str


class Usage(StrictModel):
    input_tokens: int | None
    output_tokens: int | None
    reported_cost_usd: float | None


class Metadata(StrictModel):
    request_id: str
    generated_at: str
    elapsed_ms: int
    provider: Literal["OpenRouter"]
    model_requested: str
    model_used: str
    cached: bool
    cache_age_seconds: int
    usage: Usage
    warnings: list[str]
    competitor_research: Literal["ai_suggestions_not_independently_verified"]


class LinkResponse(StrictModel):
    success: Literal[True] = True
    website: str
    brand: Brand
    analysis: Analysis
    sources: list[Source]
    seo_observations: list[SEOObservation]
    metadata: Metadata


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    success: Literal[False] = False
    error: ErrorDetail
