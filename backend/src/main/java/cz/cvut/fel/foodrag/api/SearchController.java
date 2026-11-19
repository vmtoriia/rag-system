package cz.cvut.fel.foodrag.api;

import java.util.List;

import cz.cvut.fel.foodrag.search.ProductHit;
import cz.cvut.fel.foodrag.search.Retriever;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * POST /api/search: returns the products closest in meaning to the question, without generating an answer.
 * The evaluation will use this endpoint to measure precision@k and latency.
 */
@RestController
public class SearchController {

    private final Retriever retriever;

    public SearchController(Retriever retriever) {
        this.retriever = retriever;
    }

    @PostMapping("/api/search")
    public SearchResponse search(@Valid @RequestBody SearchRequest request) {
        long start = System.nanoTime();
        List<ProductHit> products = retriever.search(request.question(), request.kOrDefault());
        long latencyMs = (System.nanoTime() - start) / 1_000_000;
        return new SearchResponse(request.question(), "vector", products.size(), latencyMs, products);
    }
}
