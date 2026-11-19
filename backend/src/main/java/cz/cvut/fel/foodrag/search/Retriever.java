package cz.cvut.fel.foodrag.search;

import java.util.List;

import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * Finds the products closest in meaning to a question (vector-only search).
 *
 * 1. The question is turned into a vector by the same embedding model as the products (bge-m3 in Ollama).
 * 2. The database compares it with all 5,888 product vectors (pgvector operator <=>, cosine distance)
 *    and returns the k closest products.
 */
@Service
public class Retriever {

    private static final String VECTOR_SEARCH_SQL = """
            SELECT ean, name, brands, url, 1 - (embedding <=> ?::vector) AS similarity
            FROM products
            ORDER BY embedding <=> ?::vector
            LIMIT ?
            """;

    private final EmbeddingModel embeddingModel;
    private final JdbcTemplate jdbc;

    // Spring passes in both helpers: the embedding model (configured in application.properties) and the JdbcTemplate.
    public Retriever(EmbeddingModel embeddingModel, JdbcTemplate jdbc) {
        this.embeddingModel = embeddingModel;
        this.jdbc = jdbc;
    }

    public List<ProductHit> search(String question, int k) {
        float[] questionVector = embeddingModel.embed(question);
        String vectorText = toPgVector(questionVector);

        return jdbc.query(
                VECTOR_SEARCH_SQL,
                (row, rowNumber) -> new ProductHit(
                        row.getString("ean"),
                        row.getString("name"),
                        row.getString("brands"),
                        row.getDouble("similarity"),
                        row.getString("url")),
                vectorText, vectorText, k);
    }

    /** pgvector reads a vector written as text, for example "[0.12,-0.03,0.5]". */
    static String toPgVector(float[] vector) {
        StringBuilder text = new StringBuilder("[");
        for (int i = 0; i < vector.length; i++) {
            if (i > 0) {
                text.append(',');
            }
            text.append(vector[i]);
        }
        return text.append(']').toString();
    }
}
