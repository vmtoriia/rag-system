package cz.cvut.fel.foodrag.api;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

/**
 * Body of POST /api/search, for example {"question": "ovesný nápoj", "k": 5}.
 * k (how many products to return) is optional; the default is 5.
 */
public record SearchRequest(
        @NotBlank String question,
        @Min(1) @Max(50) Integer k) {

    public int kOrDefault() {
        return k == null ? 5 : k;
    }
}
