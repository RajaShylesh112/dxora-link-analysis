"""Translate handcrafted test fixtures to the provider's quote-reference wire format."""

from app.schemas import Evidence, ModelOutput


def reference_fixture(output: ModelOutput, catalog: dict[str, Evidence]) -> dict:
    lookup = {(item.source_id, item.quote): key for key, item in catalog.items()}

    def convert(value):
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            if set(value) == {"source_id", "quote"}:
                return {"quote_id": lookup[(value["source_id"], value["quote"])]}
            return {key: convert(item) for key, item in value.items()}
        return value

    result = convert(output.model_dump())
    result["analysis"]["target_search_queries"] = {
        platform: {key: value for key, value in query.items() if key != "platforms"}
        for query in result["analysis"]["target_search_queries"]
        for platform in query["platforms"]
    }
    return result
