package cz.cvut.fel.foodrag.api;

import java.util.List;

import cz.cvut.fel.foodrag.search.ProductHit;

/**
 * Answer of POST /api/search.
 * mode: which search was used ("vector" now; "hybrid" will be added with the filters).
 * latencyMs: how long the search took, in milliseconds (needed for the evaluation).
 */
public record SearchResponse(String question, String mode, int count, long latencyMs, List<ProductHit> products) {
}
