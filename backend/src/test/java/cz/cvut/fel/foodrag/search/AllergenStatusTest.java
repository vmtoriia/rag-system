package cz.cvut.fel.foodrag.search;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * One test per rule of the allergen status model, plus the two conflicts found in the data.
 * Each test builds a small made-up product and checks the status of milk.
 */
class AllergenStatusTest {

    private static final String MILK = "en:milk";
    private static final List<String> EMPTY = List.of();

    @Test
    void milkInAllergensIsDeclared() {
        assertEquals(AllergenStatus.DECLARED,
                AllergenStatus.of(MILK, List.of("en:gluten", MILK), EMPTY, EMPTY, false));
    }

    @Test
    void milkOnlyInTracesIsTraces() {
        assertEquals(AllergenStatus.TRACES,
                AllergenStatus.of(MILK, EMPTY, List.of(MILK), EMPTY, false));
    }

    @Test
    void anotherAllergenListedMeansNotDeclared() {
        assertEquals(AllergenStatus.NOT_DECLARED,
                AllergenStatus.of(MILK, List.of("en:gluten"), EMPTY, EMPTY, false));
    }

    @Test
    void explicitNoneMeansNotDeclared() {
        assertEquals(AllergenStatus.NOT_DECLARED,
                AllergenStatus.of(MILK, EMPTY, EMPTY, EMPTY, true));
    }

    @Test
    void nonStandardTagCountsAsAllergenInformation() {
        assertEquals(AllergenStatus.NOT_DECLARED,
                AllergenStatus.of(MILK, EMPTY, EMPTY, List.of("cs:pšeničná"), false));
    }

    @Test
    void noAllergenInformationIsUnknown() {
        assertEquals(AllergenStatus.UNKNOWN,
                AllergenStatus.of(MILK, EMPTY, EMPTY, EMPTY, false));
    }

    // Conflict in the data: milk is both an allergen and a trace. The stronger status wins.
    @Test
    void declaredWinsOverTraces() {
        assertEquals(AllergenStatus.DECLARED,
                AllergenStatus.of(MILK, List.of(MILK), List.of(MILK), EMPTY, false));
    }

    // Conflict in the data: 37 products are marked "en:none" but still list milk.
    @Test
    void declaredWinsOverExplicitNone() {
        assertEquals(AllergenStatus.DECLARED,
                AllergenStatus.of(MILK, List.of(MILK), EMPTY, EMPTY, true));
    }
}
