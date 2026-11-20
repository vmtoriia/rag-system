package cz.cvut.fel.foodrag.search;

import java.util.List;

/**
 * Status of one allergen for one product (see docs/DATA.md, "Allergen status model").
 * The rules are checked in the order below; the first rule that matches wins.
 */
public enum AllergenStatus {

    /** The allergen is in allergens_eu: the product contains it. */
    DECLARED,

    /** The allergen is in traces_eu: the product may contain traces of it. */
    TRACES,

    /** The product has allergen information, but this allergen is not in it. Not a guarantee. */
    NOT_DECLARED,

    /** The product has no allergen information at all. Never treated as allergen-free. */
    UNKNOWN;

    /**
     * @param tag          the allergen as a tag, for example "en:milk"
     * @param allergens    allergens_eu of the product
     * @param traces       traces_eu of the product
     * @param otherTags    allergens_other of the product (non-standard tags such as "cs:pšeničná")
     * @param declaredNone allergens_declared_none of the product (the tag "en:none")
     */
    public static AllergenStatus of(String tag, List<String> allergens, List<String> traces,
                                    List<String> otherTags, boolean declaredNone) {
        if (allergens.contains(tag)) {
            return DECLARED;
        }
        if (traces.contains(tag)) {
            return TRACES;
        }
        boolean hasAllergenInfo = !allergens.isEmpty() || !traces.isEmpty() || !otherTags.isEmpty() || declaredNone;
        return hasAllergenInfo ? NOT_DECLARED : UNKNOWN;
    }
}
