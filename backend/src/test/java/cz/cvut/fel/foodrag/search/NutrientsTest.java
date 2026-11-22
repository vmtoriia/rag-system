package cz.cvut.fel.foodrag.search;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Nutrient names end up inside the SQL text, so only names from the fixed list may pass.
 */
class NutrientsTest {

    @Test
    void knownNameBecomesColumn() {
        assertEquals("sugars_100g", Nutrients.column("sugars"));
    }

    @Test
    void namesAreCleanedBeforeTheCheck() {
        assertEquals(Map.of("sugars", 5.0), Nutrients.validate(Map.of(" Sugars ", 5.0)));
    }

    @Test
    void missingLimitsMeanNoLimits() {
        assertEquals(Map.of(), Nutrients.validate(null));
    }

    @Test
    void unknownNutrientIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> Nutrients.validate(Map.of("vitamin_c", 10.0)));
    }

    @Test
    void sqlInsteadOfNameIsRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> Nutrients.validate(Map.of("sugars_100g <= 100 OR 1=1 --", 5.0)));
    }

    @Test
    void negativeLimitIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> Nutrients.validate(Map.of("salt", -1.0)));
    }
}
