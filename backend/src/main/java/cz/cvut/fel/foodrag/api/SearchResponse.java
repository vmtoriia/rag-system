package cz.cvut.fel.foodrag.api;

import java.util.List;

import cz.cvut.fel.foodrag.search.ProductHit;
import cz.cvut.fel.foodrag.search.SearchFilters;
import cz.cvut.fel.foodrag.search.SearchMode;

/**
 * Answer of POST /api/search.
 * filters: the filters that were used, so every result can be traced back to its conditions.
 * latencyMs: how long the search took, in milliseconds (needed for the evaluation).
 */
public record SearchResponse(String question, SearchMode mode, SearchFilters filters,
                             int count, long latencyMs, List<ProductHit> products) {
}
