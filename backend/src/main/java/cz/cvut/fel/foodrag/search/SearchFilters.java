package cz.cvut.fel.foodrag.search;

import java.util.List;

/**
 * Structured conditions of a search, applied by the database (not by the language model).
 * excludeAllergenTags: for example ["en:milk"].
 */
public record SearchFilters(List<String> excludeAllergenTags, TracesPolicy tracesPolicy) {
}
