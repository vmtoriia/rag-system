package cz.cvut.fel.foodrag.search;

/**
 * One product found by a search.
 * similarity: how close the product is in meaning to the question (1 = same direction, higher = closer).
 */
public record ProductHit(String ean, String name, String brands, double similarity, String url) {
}
