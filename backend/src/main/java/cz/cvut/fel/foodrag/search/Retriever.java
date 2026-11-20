package cz.cvut.fel.foodrag.search;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * Finds the products closest in meaning to a question.
 *
 * VECTOR mode: the k closest products out of all 5,888.
 * HYBRID mode: the database first removes products that break the filters (WHERE),
 * then returns the k closest of the remaining ones (ORDER BY ... LIMIT).
 *
 * In both modes every result gets the status of each requested allergen,
 * so the evaluation can count unsafe results of the vector-only search.
 */
@Service
public class Retriever {

    private static final String SELECT = """
            SELECT ean, name, brands, url,
                   allergens_eu, traces_eu, allergens_other, allergens_declared_none,
                   1 - (embedding <=> ?::vector) AS similarity
            FROM products
            """;

    // DECLARED: the product lists one of the allergens (&& means "the two lists share an element")
    private static final String NOT_DECLARED_ALLERGEN = "NOT (allergens_eu && ?::text[])";

    // TRACES: the product may contain traces of one of the allergens
    private static final String NO_TRACES = "NOT (traces_eu && ?::text[])";

    // UNKNOWN is removed: a product without any allergen information is never treated as allergen-free
    private static final String HAS_ALLERGEN_INFO = """
            (cardinality(allergens_eu) > 0 OR cardinality(traces_eu) > 0
                 OR cardinality(allergens_other) > 0 OR allergens_declared_none)""";

    private final EmbeddingModel embeddingModel;
    private final JdbcTemplate jdbc;

    public Retriever(EmbeddingModel embeddingModel, JdbcTemplate jdbc) {
        this.embeddingModel = embeddingModel;
        this.jdbc = jdbc;
    }

    public List<ProductHit> search(String question, int k, SearchMode mode, SearchFilters filters) {
        String vectorText = toPgVector(embeddingModel.embed(question));
        List<String> allergenTags = filters.excludeAllergenTags();

        // The values for the "?" marks, in the same order as the marks appear in the SQL
        List<Object> params = new ArrayList<>();
        params.add(vectorText);

        List<String> conditions = new ArrayList<>();
        if (mode == SearchMode.HYBRID && !allergenTags.isEmpty()) {
            String tagArray = toPgTextArray(allergenTags);
            conditions.add(NOT_DECLARED_ALLERGEN);
            params.add(tagArray);
            if (filters.tracesPolicy() == TracesPolicy.EXCLUDE) {
                conditions.add(NO_TRACES);
                params.add(tagArray);
            }
            conditions.add(HAS_ALLERGEN_INFO);
        }

        String sql = SELECT
                + (conditions.isEmpty() ? "" : "WHERE " + String.join("\n  AND ", conditions) + "\n")
                + "ORDER BY embedding <=> ?::vector\nLIMIT ?";
        params.add(vectorText);
        params.add(k);

        return jdbc.query(sql, (row, rowNumber) -> toHit(row, allergenTags), params.toArray());
    }

    private static ProductHit toHit(ResultSet row, List<String> allergenTags) throws SQLException {
        List<String> allergens = textList(row, "allergens_eu");
        List<String> traces = textList(row, "traces_eu");
        List<String> other = textList(row, "allergens_other");
        boolean declaredNone = row.getBoolean("allergens_declared_none");

        Map<String, AllergenStatus> statuses = new LinkedHashMap<>();
        for (String tag : allergenTags) {
            String name = tag.substring("en:".length());
            statuses.put(name, AllergenStatus.of(tag, allergens, traces, other, declaredNone));
        }

        return new ProductHit(
                row.getString("ean"),
                row.getString("name"),
                row.getString("brands"),
                row.getDouble("similarity"),
                row.getString("url"),
                statuses);
    }

    /** A PostgreSQL text[] column as a Java list; a missing value becomes an empty list. */
    private static List<String> textList(ResultSet row, String column) throws SQLException {
        Array array = row.getArray(column);
        return array == null ? List.of() : Arrays.asList((String[]) array.getArray());
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

    /** PostgreSQL reads a text array written as {a,b}, for example "{en:milk,en:eggs}". */
    static String toPgTextArray(List<String> values) {
        return "{" + String.join(",", values) + "}";
    }
}
