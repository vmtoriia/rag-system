package cz.cvut.fel.foodrag.search;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Nutrients that a search can limit, all per 100 g. Each name maps to a column "<name>_100g" in the products table.
 *
 * Column names cannot be passed to SQL as "?" values, so they are written into the SQL text.
 * That is safe only because every name is checked against this fixed list first.
 */
public final class Nutrients {

    public static final List<String> NAMES = List.of(
            "energy_kcal", "fat", "saturated_fat", "carbohydrates", "sugars", "fiber", "proteins", "salt");

    private Nutrients() {
    }

    /** "sugars" -> "sugars_100g". */
    public static String column(String name) {
        if (!NAMES.contains(name)) {
            throw new IllegalArgumentException("Unknown nutrient '" + name + "'. Allowed values: " + NAMES);
        }
        return name + "_100g";
    }

    /**
     * Checks limits from a request, for example {"sugars": 5}, and returns them with cleaned names.
     * An unknown name or a missing or negative value is rejected.
     */
    public static Map<String, Double> validate(Map<String, Double> limits) {
        if (limits == null) {
            return Map.of();
        }
        Map<String, Double> result = new LinkedHashMap<>();
        for (Map.Entry<String, Double> limit : limits.entrySet()) {
            String name = limit.getKey() == null ? "" : limit.getKey().trim().toLowerCase();
            column(name);
            Double value = limit.getValue();
            if (value == null || value < 0) {
                throw new IllegalArgumentException("The limit for '" + name + "' must be a number >= 0");
            }
            result.put(name, value);
        }
        return result;
    }
}
