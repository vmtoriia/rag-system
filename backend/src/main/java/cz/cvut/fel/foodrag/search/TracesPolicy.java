package cz.cvut.fel.foodrag.search;

/**
 * What to do with products that may contain traces of an excluded allergen (status TRACES).
 * ALLOW: keep them. EXCLUDE: remove them too.
 */
public enum TracesPolicy {
    ALLOW,
    EXCLUDE
}
