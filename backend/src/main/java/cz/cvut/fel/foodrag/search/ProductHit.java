package cz.cvut.fel.foodrag.search;

import java.util.Map;

/**
 * One product found by a search.
 * similarity: how close the product is in meaning to the question (1 = same direction, higher = closer).
 * allergenStatus: the status of every allergen from the request, for example {"milk": "NOT_DECLARED"}.
 * nutritionPer100g: the value of every nutrient from the request, for example {"sugars": 3.2}; null = unknown.
 */
public record ProductHit(String ean, String name, String brands, double similarity, String url,
                         Map<String, AllergenStatus> allergenStatus, Map<String, Double> nutritionPer100g) {
}
