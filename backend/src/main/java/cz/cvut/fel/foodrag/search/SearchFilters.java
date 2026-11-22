package cz.cvut.fel.foodrag.search;

import java.util.List;
import java.util.Map;

/**
 * Structured conditions of a search, applied by the database (not by the language model).
 * excludeAllergenTags: for example ["en:milk"].
 * maxPer100g / minPer100g: nutrition limits, for example {"sugars": 5.0}. A product without the value never passes.
 */
public record SearchFilters(List<String> excludeAllergenTags, TracesPolicy tracesPolicy,
                            Map<String, Double> maxPer100g, Map<String, Double> minPer100g) {
}
