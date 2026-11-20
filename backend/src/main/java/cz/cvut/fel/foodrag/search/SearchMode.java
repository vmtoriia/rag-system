package cz.cvut.fel.foodrag.search;

/**
 * VECTOR: products ranked only by similarity in meaning.
 * HYBRID: the same ranking, but only among products that pass the filters (allergens, later nutrition limits).
 */
public enum SearchMode {
    VECTOR,
    HYBRID
}
