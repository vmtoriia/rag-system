package cz.cvut.fel.foodrag.api;

import java.util.List;
import java.util.Map;

import cz.cvut.fel.foodrag.search.EuAllergens;
import cz.cvut.fel.foodrag.search.Nutrients;
import cz.cvut.fel.foodrag.search.SearchFilters;
import cz.cvut.fel.foodrag.search.SearchMode;
import cz.cvut.fel.foodrag.search.TracesPolicy;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

/**
 * Body of POST /api/search, for example:
 * {"question": "ovesný nápoj", "k": 5, "mode": "HYBRID", "excludeAllergens": ["milk"], "tracesPolicy": "ALLOW",
 *  "maxPer100g": {"sugars": 5}, "minPer100g": {"proteins": 1}}
 *
 * Only "question" is required. Defaults: k = 5, mode = HYBRID, no excluded allergens,
 * tracesPolicy = EXCLUDE (the stricter choice, used when the user does not say otherwise), no nutrition limits.
 */
public record SearchRequest(
        @NotBlank String question,
        @Min(1) @Max(50) Integer k,
        SearchMode mode,
        List<String> excludeAllergens,
        TracesPolicy tracesPolicy,
        Map<String, Double> maxPer100g,
        Map<String, Double> minPer100g) {

    public int kOrDefault() {
        return k == null ? 5 : k;
    }

    public SearchMode modeOrDefault() {
        return mode == null ? SearchMode.HYBRID : mode;
    }

    /** Throws IllegalArgumentException for an unknown allergen or nutrient name, or a negative limit. */
    public SearchFilters filters() {
        List<String> tags = excludeAllergens == null
                ? List.of()
                : excludeAllergens.stream().map(EuAllergens::toTag).distinct().toList();
        return new SearchFilters(
                tags,
                tracesPolicy == null ? TracesPolicy.EXCLUDE : tracesPolicy,
                Nutrients.validate(maxPer100g),
                Nutrients.validate(minPer100g));
    }
}
