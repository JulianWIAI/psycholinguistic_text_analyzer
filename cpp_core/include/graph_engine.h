#pragma once
/**
 * graph_engine.h
 * --------------
 * In-memory graph engine for the PsychoLinguistic Analysis Engine.
 * Thread-safe via shared_mutex (multiple concurrent readers, exclusive writers).
 *
 * Namespace: psycho
 */

#include <shared_mutex>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <string>
#include <cstdint>
#include <memory>

namespace psycho {

// ---------------------------------------------------------------------------
// Node types
// ---------------------------------------------------------------------------
enum class NodeType : uint8_t {
    Document         = 0,
    Corpus           = 1,
    StylisticDevice  = 2,
    WordField        = 3,
    MacroCluster     = 4,
    SomaticArchetype = 5,
    Unknown          = 255
};

// ---------------------------------------------------------------------------
// Edge types
// ---------------------------------------------------------------------------
enum class EdgeType : uint8_t {
    BELONGS_TO            = 0,
    EXHIBITS_DEVICE       = 1,
    CO_OCCURS_WITH        = 2,
    HAS_SOMATIC_SIGNATURE = 3,
    Unknown               = 255
};

// ---------------------------------------------------------------------------
// Free conversion functions
// ---------------------------------------------------------------------------
NodeType    node_type_from_string(const std::string& s);
std::string node_type_to_string(NodeType t);
EdgeType    edge_type_from_string(const std::string& s);
std::string edge_type_to_string(EdgeType e);

// ---------------------------------------------------------------------------
// Graph data structures
// ---------------------------------------------------------------------------
struct GraphNode {
    std::string                                   id;
    NodeType                                      type;
    std::unordered_map<std::string, std::string>  properties;
};

struct AdjEntry {
    std::string target;
    EdgeType    relation;
    float       weight;
};

// n×n co-occurrence matrix (symmetric, feature-space)
struct CoMatrix {
    std::vector<std::string>          nodes;   // feature node ids (sorted)
    std::vector<std::vector<float>>   matrix;  // [n][n]
};

// Laplacian matrix L = D - A (dense double, for numpy eigen decomp)
struct LaplacianMatrix {
    std::vector<std::string>           nodes;  // feature node ids (sorted)
    std::vector<std::vector<double>>   data;   // [n][n]
};

// BFS traversal output
struct TraversalNode {
    std::string                                  id;
    std::string                                  type_str;
    std::unordered_map<std::string, std::string> properties;
};

struct TraversalEdge {
    std::string source;
    std::string target;
    std::string relation_str;
    float       weight;
};

struct TraversalResult {
    std::vector<TraversalNode> nodes;
    std::vector<TraversalEdge> edges;
};

// ---------------------------------------------------------------------------
// GraphEngine — main class
// ---------------------------------------------------------------------------
class GraphEngine {
public:
    GraphEngine()  = default;
    ~GraphEngine() = default;

    // Non-copyable (owns mutable internal state + mutex)
    GraphEngine(const GraphEngine&)            = delete;
    GraphEngine& operator=(const GraphEngine&) = delete;

    // --- Mutations (exclusive lock) ----------------------------------------
    void add_node(const std::string& id,
                  const std::string& type_str,
                  const std::unordered_map<std::string, std::string>& properties = {});

    void add_edge(const std::string& source,
                  const std::string& target,
                  const std::string& relation_str,
                  float              weight = 1.0f);

    // --- Queries (shared lock) ---------------------------------------------
    bool        has_node(const std::string& id)    const;
    std::size_t node_count()                        const;
    std::size_t edge_count()                        const;

    CoMatrix       get_co_occurrence_matrix(const std::vector<std::string>& corpus_ids) const;
    LaplacianMatrix compute_laplacian(const std::vector<std::string>& corpus_ids)        const;
    TraversalResult query_traversal(const std::string& start_id, int max_depth = 3)     const;

    std::vector<GraphNode> list_corpora() const;

    // --- Persistence -------------------------------------------------------
    void save_graph(const std::string& filepath) const;
    void load_graph(const std::string& filepath);

private:
    // Internal helper — called while already holding a shared lock
    CoMatrix _build_co_matrix_internal(const std::vector<std::string>& corpus_ids) const;

    mutable std::shared_mutex _mutex;

    std::unordered_map<std::string, GraphNode>               _nodes;
    std::unordered_map<std::string, std::vector<AdjEntry>>   _adj;   // forward adjacency
    std::unordered_map<std::string, std::vector<AdjEntry>>   _radj;  // reverse adjacency
    std::unordered_map<std::string, std::unordered_set<std::string>> _corpus_members;
};

} // namespace psycho
