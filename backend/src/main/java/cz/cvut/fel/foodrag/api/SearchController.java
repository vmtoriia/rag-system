package cz.cvut.fel.foodrag.api;

import java.util.List;

import cz.cvut.fel.foodrag.search.ProductHit;
import cz.cvut.fel.foodrag.search.Retriever;
import cz.cvut.fel.foodrag.search.SearchFilters;
import cz.cvut.fel.foodrag.search.SearchMode;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/**
 * POST /api/search: returns the products closest in meaning to the question, without generating an answer.
 * The evaluation will use this endpoint to compare VECTOR and HYBRID (precision@k, safety, latency).
 */
@RestController
public class SearchController {

    private final Retriever retriever;

    public SearchController(Retriever retriever) {
        this.retriever = retriever;
    }

    @PostMapping("/api/search")
    public SearchResponse search(@Valid @RequestBody SearchRequest request) {
        SearchFilters filters;
        try {
            filters = request.filters();
        } catch (IllegalArgumentException e) {
            // A wrong allergen or nutrient name is the user's mistake: answer 400 Bad Request with the reason
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, e.getMessage());
        }
        SearchMode mode = request.modeOrDefault();

        long start = System.nanoTime();
        List<ProductHit> products = retriever.search(request.question(), request.kOrDefault(), mode, filters);
        long latencyMs = (System.nanoTime() - start) / 1_000_000;

        return new SearchResponse(request.question(), mode, filters, products.size(), latencyMs, products);
    }
}
