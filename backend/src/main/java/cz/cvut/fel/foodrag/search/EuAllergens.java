package cz.cvut.fel.foodrag.search;

import java.util.List;

/**
 * The 14 allergens that EU law requires on food labels (Regulation 1169/2011, Annex II).
 * The names are the same as the Open Food Facts tags without the "en:" prefix.
 */
public final class EuAllergens {

    public static final List<String> NAMES = List.of(
            "gluten", "crustaceans", "eggs", "fish", "peanuts", "soybeans", "milk",
            "nuts", "celery", "mustard", "sesame-seeds", "sulphur-dioxide-and-sulphites",
            "lupin", "molluscs");

    private EuAllergens() {
    }

    /** "milk" -> "en:milk". An unknown name is rejected, so a typo cannot silently turn a filter off. */
    public static String toTag(String name) {
        String cleaned = name == null ? "" : name.trim().toLowerCase();
        if (!NAMES.contains(cleaned)) {
            throw new IllegalArgumentException("Unknown allergen '" + name + "'. Allowed values: " + NAMES);
        }
        return "en:" + cleaned;
    }
}
