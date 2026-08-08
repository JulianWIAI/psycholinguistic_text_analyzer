/**
 * graph_engine.cpp
 * ----------------
 * Implementation of psycho::GraphEngine — in-memory graph with
 * thread-safe access via shared_mutex.
 *
 * Thread model:
 *   - Reads  → shared_lock  (multiple concurrent)
 *   - Writes → unique_lock  (exclusive)
 */

#include "graph_engine.h"

#include <algorithm>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <queue>
#include <cmath>

namespace psycho {

// ===========================================================================
// String ↔ enum converters
// ===========================================================================

NodeType node_type_from_string(const std::string& s) {
    if (s == "Document")         return NodeType::Document;
    if (s == "Corpus")           return NodeType::Corpus;
    if (s == "StylisticDevice")  return NodeType::StylisticDevice;
    if (s == "WordField")        return NodeType::WordField;
    if (s == "MacroCluster")     return NodeType::MacroCluster;
    if (s == "SomaticArchetype") return NodeType::SomaticArchetype;
    return NodeType::Unknown;
}

std::string node_type_to_string(NodeType t) {
    switch (t) {
        case NodeType::Document:         return "Document";
        case NodeType::Corpus:           return "Corpus";
        case NodeType::StylisticDevice:  return "StylisticDevice";
        case NodeType::WordField:        return "WordField";
        case NodeType::MacroCluster:     return "MacroCluster";
        case NodeType::SomaticArchetype: return "SomaticArchetype";
        default:                         return "Unknown";
    }
}

EdgeType edge_type_from_string(const std::string& s) {
    if (s == "BELONGS_TO")            return EdgeType::BELONGS_TO;
    if (s == "EXHIBITS_DEVICE")       return EdgeType::EXHIBITS_DEVICE;
    if (s == "CO_OCCURS_WITH")        return EdgeType::CO_OCCURS_WITH;
    if (s == "HAS_SOMATIC_SIGNATURE") return EdgeType::HAS_SOMATIC_SIGNATURE;
    return EdgeType::Unknown;
}

std::string edge_type_to_string(EdgeType e) {
    switch (e) {
        case EdgeType::BELONGS_TO:            return "BELONGS_TO";
        case EdgeType::EXHIBITS_DEVICE:       return "EXHIBITS_DEVICE";
        case EdgeType::CO_OCCURS_WITH:        return "CO_OCCURS_WITH";
        case EdgeType::HAS_SOMATIC_SIGNATURE: return "HAS_SOMATIC_SIGNATURE";
        default:                              return "Unknown";
    }
}

// ===========================================================================
// Mutations
// ===========================================================================

void GraphEngine::add_node(
    const std::string& id,
    const std::string& type_str,
    const std::unordered_map<std::string, std::string>& properties)
{
    std::unique_lock<std::shared_mutex> lock(_mutex);

    NodeType t = node_type_from_string(type_str);

    GraphNode node;
    node.id         = id;
    node.type       = t;
    node.properties = properties;

    _nodes[id] = std::move(node);

    // Ensure adjacency entries exist for this node
    if (!_adj.count(id))  _adj[id]  = {};
    if (!_radj.count(id)) _radj[id] = {};

    // Corpus bookkeeping: ensure the member set exists (don't overwrite)
    if (t == NodeType::Corpus) {
        _corpus_members.emplace(id, std::unordered_set<std::string>{});
    }
}

void GraphEngine::add_edge(
    const std::string& source,
    const std::string& target,
    const std::string& relation_str,
    float              weight)
{
    std::unique_lock<std::shared_mutex> lock(_mutex);

    EdgeType rel = edge_type_from_string(relation_str);

    AdjEntry fwd;
    fwd.target   = target;
    fwd.relation = rel;
    fwd.weight   = weight;
    _adj[source].push_back(fwd);

    AdjEntry rev;
    rev.target   = source;
    rev.relation = rel;
    rev.weight   = weight;
    _radj[target].push_back(rev);

    // Track corpus membership
    if (rel == EdgeType::BELONGS_TO) {
        // source document belongs to target corpus
        _corpus_members[target].insert(source);
    }
}

// ===========================================================================
// Queries
// ===========================================================================

bool GraphEngine::has_node(const std::string& id) const {
    std::shared_lock<std::shared_mutex> lock(_mutex);
    return _nodes.count(id) > 0;
}

std::size_t GraphEngine::node_count() const {
    std::shared_lock<std::shared_mutex> lock(_mutex);
    return _nodes.size();
}

std::size_t GraphEngine::edge_count() const {
    std::shared_lock<std::shared_mutex> lock(_mutex);
    std::size_t total = 0;
    for (const auto& [id, vec] : _adj) {
        total += vec.size();
    }
    return total;
}

std::vector<GraphNode> GraphEngine::list_corpora() const {
    std::shared_lock<std::shared_mutex> lock(_mutex);
    std::vector<GraphNode> result;
    for (const auto& [id, node] : _nodes) {
        if (node.type == NodeType::Corpus) {
            result.push_back(node);
        }
    }
    return result;
}

// ---------------------------------------------------------------------------
// Co-occurrence matrix (internal, called under shared lock)
// ---------------------------------------------------------------------------
CoMatrix GraphEngine::_build_co_matrix_internal(
    const std::vector<std::string>& corpus_ids) const
{
    // 1. Collect document IDs that belong to any of the given corpora
    std::unordered_set<std::string> doc_set;
    for (const auto& cid : corpus_ids) {
        auto it = _corpus_members.find(cid);
        if (it == _corpus_members.end()) continue;
        for (const auto& doc_id : it->second) {
            // Confirm the node exists and is a Document
            auto nit = _nodes.find(doc_id);
            if (nit != _nodes.end() && nit->second.type == NodeType::Document) {
                doc_set.insert(doc_id);
            }
        }
    }

    // 2. Collect feature nodes reachable from those documents via relevant edges
    std::unordered_set<std::string> feature_set;
    for (const auto& doc_id : doc_set) {
        auto ait = _adj.find(doc_id);
        if (ait == _adj.end()) continue;
        for (const auto& entry : ait->second) {
            if (entry.relation == EdgeType::EXHIBITS_DEVICE ||
                entry.relation == EdgeType::CO_OCCURS_WITH)
            {
                auto nit = _nodes.find(entry.target);
                if (nit == _nodes.end()) continue;
                NodeType nt = nit->second.type;
                if (nt == NodeType::StylisticDevice ||
                    nt == NodeType::WordField        ||
                    nt == NodeType::MacroCluster)
                {
                    feature_set.insert(entry.target);
                }
            }
        }
    }

    // 3. Build sorted node list
    std::vector<std::string> feature_nodes(feature_set.begin(), feature_set.end());
    std::sort(feature_nodes.begin(), feature_nodes.end());

    const std::size_t n = feature_nodes.size();

    // Index map for fast lookup
    std::unordered_map<std::string, std::size_t> idx;
    idx.reserve(n);
    for (std::size_t i = 0; i < n; ++i) {
        idx[feature_nodes[i]] = i;
    }

    // 4. Build co-occurrence matrix
    std::vector<std::vector<float>> matrix(n, std::vector<float>(n, 0.0f));

    for (const auto& doc_id : doc_set) {
        auto ait = _adj.find(doc_id);
        if (ait == _adj.end()) continue;

        // Collect (feature_idx, weight) pairs for this document
        std::vector<std::pair<std::size_t, float>> doc_features;
        for (const auto& entry : ait->second) {
            if (entry.relation != EdgeType::EXHIBITS_DEVICE &&
                entry.relation != EdgeType::CO_OCCURS_WITH)
                continue;
            auto iit = idx.find(entry.target);
            if (iit == idx.end()) continue;
            doc_features.emplace_back(iit->second, entry.weight);
        }

        // For each feature pair, accumulate weight product
        for (std::size_t a = 0; a < doc_features.size(); ++a) {
            for (std::size_t b = 0; b < doc_features.size(); ++b) {
                matrix[doc_features[a].first][doc_features[b].first]
                    += doc_features[a].second * doc_features[b].second;
            }
        }
    }

    CoMatrix result;
    result.nodes  = std::move(feature_nodes);
    result.matrix = std::move(matrix);
    return result;
}

CoMatrix GraphEngine::get_co_occurrence_matrix(
    const std::vector<std::string>& corpus_ids) const
{
    std::shared_lock<std::shared_mutex> lock(_mutex);
    return _build_co_matrix_internal(corpus_ids);
}

// ---------------------------------------------------------------------------
// Laplacian  L = D - A
// ---------------------------------------------------------------------------
LaplacianMatrix GraphEngine::compute_laplacian(
    const std::vector<std::string>& corpus_ids) const
{
    std::shared_lock<std::shared_mutex> lock(_mutex);

    CoMatrix co = _build_co_matrix_internal(corpus_ids);
    const std::size_t n = co.nodes.size();

    std::vector<std::vector<double>> L(n, std::vector<double>(n, 0.0));

    for (std::size_t i = 0; i < n; ++i) {
        double degree = 0.0;
        for (std::size_t j = 0; j < n; ++j) {
            degree += static_cast<double>(co.matrix[i][j]);
        }
        for (std::size_t j = 0; j < n; ++j) {
            L[i][j] = -static_cast<double>(co.matrix[i][j]);
        }
        L[i][i] = degree;
    }

    LaplacianMatrix result;
    result.nodes = std::move(co.nodes);
    result.data  = std::move(L);
    return result;
}

// ---------------------------------------------------------------------------
// BFS traversal
// ---------------------------------------------------------------------------
TraversalResult GraphEngine::query_traversal(
    const std::string& start_id,
    int                max_depth) const
{
    std::shared_lock<std::shared_mutex> lock(_mutex);

    TraversalResult result;

    if (!_nodes.count(start_id)) {
        return result;
    }

    // BFS: queue holds (node_id, current_depth)
    std::queue<std::pair<std::string, int>> q;
    std::unordered_set<std::string> visited;

    q.push({start_id, 0});
    visited.insert(start_id);

    while (!q.empty()) {
        auto [current_id, depth] = q.front();
        q.pop();

        // Add node to result
        const GraphNode& gn = _nodes.at(current_id);
        TraversalNode tn;
        tn.id         = gn.id;
        tn.type_str   = node_type_to_string(gn.type);
        tn.properties = gn.properties;
        result.nodes.push_back(std::move(tn));

        if (depth >= max_depth) continue;

        // Expand neighbours
        auto ait = _adj.find(current_id);
        if (ait == _adj.end()) continue;

        for (const auto& entry : ait->second) {
            // Record edge regardless (even if target already visited)
            TraversalEdge te;
            te.source       = current_id;
            te.target       = entry.target;
            te.relation_str = edge_type_to_string(entry.relation);
            te.weight       = entry.weight;
            result.edges.push_back(te);

            if (!visited.count(entry.target) && _nodes.count(entry.target)) {
                visited.insert(entry.target);
                q.push({entry.target, depth + 1});
            }
        }
    }

    return result;
}

// ===========================================================================
// Persistence — simple JSON round-trip (manual ostringstream, no dependency)
// ===========================================================================

// Escape a string value for embedding in JSON
static std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 4);
    for (unsigned char c : s) {
        switch (c) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n";  break;
            case '\r': out += "\\r";  break;
            case '\t': out += "\\t";  break;
            default:
                if (c < 0x20) {
                    // Encode control characters as \uXXXX
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out;
}

// Serialize a string→string map as a JSON object
static std::string props_to_json(
    const std::unordered_map<std::string, std::string>& props)
{
    std::ostringstream ss;
    ss << '{';
    bool first = true;
    for (const auto& [k, v] : props) {
        if (!first) ss << ',';
        ss << '"' << json_escape(k) << '"'
           << ':'
           << '"' << json_escape(v) << '"';
        first = false;
    }
    ss << '}';
    return ss.str();
}

void GraphEngine::save_graph(const std::string& filepath) const {
    std::shared_lock<std::shared_mutex> lock(_mutex);

    std::ostringstream ss;
    ss << "{\n";

    // ---- nodes ----
    ss << "\"nodes\":[";
    bool first_node = true;
    for (const auto& [id, node] : _nodes) {
        if (!first_node) ss << ',';
        ss << '{'
           << "\"id\":\"" << json_escape(id) << "\","
           << "\"type\":\"" << node_type_to_string(node.type) << "\","
           << "\"properties\":" << props_to_json(node.properties)
           << '}';
        first_node = false;
    }
    ss << "],\n";

    // ---- edges ----
    ss << "\"edges\":[";
    bool first_edge = true;
    for (const auto& [src, entries] : _adj) {
        for (const auto& entry : entries) {
            if (!first_edge) ss << ',';
            ss << '{'
               << "\"source\":\"" << json_escape(src) << "\","
               << "\"target\":\"" << json_escape(entry.target) << "\","
               << "\"relation\":\"" << edge_type_to_string(entry.relation) << "\","
               << "\"weight\":" << entry.weight
               << '}';
            first_edge = false;
        }
    }
    ss << "],\n";

    // ---- corpus_members ----
    ss << "\"corpus_members\":{";
    bool first_corpus = true;
    for (const auto& [corpus_id, members] : _corpus_members) {
        if (!first_corpus) ss << ',';
        ss << '"' << json_escape(corpus_id) << '"' << ":[";
        bool first_member = true;
        for (const auto& member_id : members) {
            if (!first_member) ss << ',';
            ss << '"' << json_escape(member_id) << '"';
            first_member = false;
        }
        ss << ']';
        first_corpus = false;
    }
    ss << "}\n";

    ss << "}\n";

    // Write to .tmp then rename for atomicity
    const std::string tmp_path = filepath + ".tmp";
    {
        std::ofstream ofs(tmp_path, std::ios::out | std::ios::trunc);
        if (!ofs) {
            throw std::runtime_error("GraphEngine::save_graph: cannot open file for writing: " + tmp_path);
        }
        ofs << ss.str();
    }

    // Overwrite destination
    if (std::rename(tmp_path.c_str(), filepath.c_str()) != 0) {
        throw std::runtime_error("GraphEngine::save_graph: rename failed for: " + filepath);
    }
}

// ---------------------------------------------------------------------------
// Minimal string-find JSON parser for the format we write ourselves
// ---------------------------------------------------------------------------

// Skip whitespace
static std::size_t skip_ws(const std::string& s, std::size_t pos) {
    while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\n' ||
                               s[pos] == '\r' || s[pos] == '\t'))
        ++pos;
    return pos;
}

// Parse a JSON string starting at pos (must point at opening '"')
// Returns the string value and advances pos past the closing '"'
static std::string parse_json_string(const std::string& s, std::size_t& pos) {
    if (pos >= s.size() || s[pos] != '"') {
        throw std::runtime_error("GraphEngine::load_graph: expected '\"' at position " + std::to_string(pos));
    }
    ++pos; // skip opening quote
    std::string result;
    while (pos < s.size() && s[pos] != '"') {
        if (s[pos] == '\\') {
            ++pos;
            if (pos >= s.size()) break;
            switch (s[pos]) {
                case '"':  result += '"';  break;
                case '\\': result += '\\'; break;
                case '/':  result += '/';  break;
                case 'n':  result += '\n'; break;
                case 'r':  result += '\r'; break;
                case 't':  result += '\t'; break;
                case 'u': {
                    // \uXXXX — read 4 hex digits and output as UTF-8
                    if (pos + 4 < s.size()) {
                        std::string hex = s.substr(pos + 1, 4);
                        unsigned int cp = std::stoul(hex, nullptr, 16);
                        pos += 4;
                        // Encode as UTF-8 (BMP only, sufficient for our format)
                        if (cp < 0x80) {
                            result += static_cast<char>(cp);
                        } else if (cp < 0x800) {
                            result += static_cast<char>(0xC0 | (cp >> 6));
                            result += static_cast<char>(0x80 | (cp & 0x3F));
                        } else {
                            result += static_cast<char>(0xE0 | (cp >> 12));
                            result += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
                            result += static_cast<char>(0x80 | (cp & 0x3F));
                        }
                    }
                    break;
                }
                default: result += s[pos]; break;
            }
        } else {
            result += s[pos];
        }
        ++pos;
    }
    if (pos < s.size()) ++pos; // skip closing quote
    return result;
}

// Parse a JSON object (string→string map) starting at '{'
static std::unordered_map<std::string, std::string>
parse_string_map(const std::string& s, std::size_t& pos) {
    std::unordered_map<std::string, std::string> result;
    pos = skip_ws(s, pos);
    if (pos >= s.size() || s[pos] != '{') {
        throw std::runtime_error("GraphEngine::load_graph: expected '{' for object");
    }
    ++pos; // skip '{'
    pos = skip_ws(s, pos);
    if (pos < s.size() && s[pos] == '}') { ++pos; return result; }

    while (pos < s.size()) {
        pos = skip_ws(s, pos);
        std::string key = parse_json_string(s, pos);
        pos = skip_ws(s, pos);
        if (pos < s.size() && s[pos] == ':') ++pos;
        pos = skip_ws(s, pos);
        std::string val = parse_json_string(s, pos);
        result[key] = val;
        pos = skip_ws(s, pos);
        if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
        if (pos < s.size() && s[pos] == '}') { ++pos; break; }
    }
    return result;
}

// Parse a JSON array of strings starting at '['
static std::vector<std::string>
parse_string_array(const std::string& s, std::size_t& pos) {
    std::vector<std::string> result;
    pos = skip_ws(s, pos);
    if (pos >= s.size() || s[pos] != '[') {
        throw std::runtime_error("GraphEngine::load_graph: expected '[' for array");
    }
    ++pos;
    pos = skip_ws(s, pos);
    if (pos < s.size() && s[pos] == ']') { ++pos; return result; }

    while (pos < s.size()) {
        pos = skip_ws(s, pos);
        result.push_back(parse_json_string(s, pos));
        pos = skip_ws(s, pos);
        if (pos < s.size() && s[pos] == ',') { ++pos; continue; }
        if (pos < s.size() && s[pos] == ']') { ++pos; break; }
    }
    return result;
}

// Parse a float value (terminated by ',', '}', ']', or whitespace)
static float parse_float(const std::string& s, std::size_t& pos) {
    pos = skip_ws(s, pos);
    std::size_t start = pos;
    while (pos < s.size() && s[pos] != ',' && s[pos] != '}' &&
           s[pos] != ']' && s[pos] != ' ' && s[pos] != '\n' &&
           s[pos] != '\r' && s[pos] != '\t')
    {
        ++pos;
    }
    std::string token = s.substr(start, pos - start);
    return std::stof(token);
}

void GraphEngine::load_graph(const std::string& filepath) {
    // Read file contents
    std::ifstream ifs(filepath, std::ios::in);
    if (!ifs) {
        throw std::runtime_error("GraphEngine::load_graph: cannot open file: " + filepath);
    }
    std::ostringstream buf;
    buf << ifs.rdbuf();
    const std::string content = buf.str();

    std::unique_lock<std::shared_mutex> lock(_mutex);

    // Clear existing state
    _nodes.clear();
    _adj.clear();
    _radj.clear();
    _corpus_members.clear();

    std::size_t pos = 0;

    // Skip to opening '{'
    pos = skip_ws(content, pos);
    if (pos >= content.size() || content[pos] != '{') {
        throw std::runtime_error("GraphEngine::load_graph: invalid JSON root");
    }
    ++pos;

    // Parse top-level keys in the order we write them: nodes, edges, corpus_members
    while (pos < content.size()) {
        pos = skip_ws(content, pos);
        if (pos >= content.size()) break;
        if (content[pos] == '}') break;
        if (content[pos] == ',') { ++pos; continue; }

        // Read key
        std::string key = parse_json_string(content, pos);
        pos = skip_ws(content, pos);
        if (pos < content.size() && content[pos] == ':') ++pos;
        pos = skip_ws(content, pos);

        if (key == "nodes") {
            // Parse array of node objects
            if (pos < content.size() && content[pos] != '[') {
                throw std::runtime_error("GraphEngine::load_graph: expected '[' for nodes");
            }
            ++pos; // skip '['
            pos = skip_ws(content, pos);
            if (pos < content.size() && content[pos] == ']') { ++pos; continue; }

            while (pos < content.size()) {
                pos = skip_ws(content, pos);
                if (content[pos] == ']') { ++pos; break; }
                if (content[pos] == ',') { ++pos; continue; }

                // Parse node object '{'
                if (content[pos] != '{') {
                    throw std::runtime_error("GraphEngine::load_graph: expected '{' for node");
                }
                ++pos;

                std::string node_id, node_type_str;
                std::unordered_map<std::string, std::string> node_props;

                while (pos < content.size()) {
                    pos = skip_ws(content, pos);
                    if (content[pos] == '}') { ++pos; break; }
                    if (content[pos] == ',') { ++pos; continue; }

                    std::string nkey = parse_json_string(content, pos);
                    pos = skip_ws(content, pos);
                    if (pos < content.size() && content[pos] == ':') ++pos;
                    pos = skip_ws(content, pos);

                    if (nkey == "id") {
                        node_id = parse_json_string(content, pos);
                    } else if (nkey == "type") {
                        node_type_str = parse_json_string(content, pos);
                    } else if (nkey == "properties") {
                        node_props = parse_string_map(content, pos);
                    } else {
                        // Skip unknown value: find next comma or closing brace
                        // (simplified: skip past a string value if present)
                        if (content[pos] == '"') {
                            parse_json_string(content, pos);
                        }
                    }
                }

                if (!node_id.empty()) {
                    GraphNode gn;
                    gn.id         = node_id;
                    gn.type       = node_type_from_string(node_type_str);
                    gn.properties = std::move(node_props);
                    _nodes[node_id] = std::move(gn);
                    if (!_adj.count(node_id))  _adj[node_id]  = {};
                    if (!_radj.count(node_id)) _radj[node_id] = {};
                    if (node_type_from_string(node_type_str) == NodeType::Corpus) {
                        _corpus_members.emplace(node_id, std::unordered_set<std::string>{});
                    }
                }

                pos = skip_ws(content, pos);
                if (pos < content.size() && content[pos] == ',') ++pos;
            }

        } else if (key == "edges") {
            if (pos < content.size() && content[pos] != '[') {
                throw std::runtime_error("GraphEngine::load_graph: expected '[' for edges");
            }
            ++pos;
            pos = skip_ws(content, pos);
            if (pos < content.size() && content[pos] == ']') { ++pos; continue; }

            while (pos < content.size()) {
                pos = skip_ws(content, pos);
                if (content[pos] == ']') { ++pos; break; }
                if (content[pos] == ',') { ++pos; continue; }
                if (content[pos] != '{') {
                    throw std::runtime_error("GraphEngine::load_graph: expected '{' for edge");
                }
                ++pos;

                std::string e_source, e_target, e_relation;
                float e_weight = 1.0f;

                while (pos < content.size()) {
                    pos = skip_ws(content, pos);
                    if (content[pos] == '}') { ++pos; break; }
                    if (content[pos] == ',') { ++pos; continue; }

                    std::string ekey = parse_json_string(content, pos);
                    pos = skip_ws(content, pos);
                    if (pos < content.size() && content[pos] == ':') ++pos;
                    pos = skip_ws(content, pos);

                    if (ekey == "source") {
                        e_source = parse_json_string(content, pos);
                    } else if (ekey == "target") {
                        e_target = parse_json_string(content, pos);
                    } else if (ekey == "relation") {
                        e_relation = parse_json_string(content, pos);
                    } else if (ekey == "weight") {
                        e_weight = parse_float(content, pos);
                    } else {
                        if (content[pos] == '"') parse_json_string(content, pos);
                    }
                }

                if (!e_source.empty() && !e_target.empty()) {
                    EdgeType rel = edge_type_from_string(e_relation);

                    AdjEntry fwd;
                    fwd.target   = e_target;
                    fwd.relation = rel;
                    fwd.weight   = e_weight;
                    _adj[e_source].push_back(fwd);

                    AdjEntry rev;
                    rev.target   = e_source;
                    rev.relation = rel;
                    rev.weight   = e_weight;
                    _radj[e_target].push_back(rev);

                    if (rel == EdgeType::BELONGS_TO) {
                        _corpus_members[e_target].insert(e_source);
                    }
                }

                pos = skip_ws(content, pos);
                if (pos < content.size() && content[pos] == ',') ++pos;
            }

        } else if (key == "corpus_members") {
            // Object: corpus_id -> array of member ids
            pos = skip_ws(content, pos);
            if (pos >= content.size() || content[pos] != '{') {
                throw std::runtime_error("GraphEngine::load_graph: expected '{' for corpus_members");
            }
            ++pos;
            pos = skip_ws(content, pos);
            if (pos < content.size() && content[pos] == '}') { ++pos; continue; }

            while (pos < content.size()) {
                pos = skip_ws(content, pos);
                if (content[pos] == '}') { ++pos; break; }
                if (content[pos] == ',') { ++pos; continue; }

                std::string corpus_key = parse_json_string(content, pos);
                pos = skip_ws(content, pos);
                if (pos < content.size() && content[pos] == ':') ++pos;
                pos = skip_ws(content, pos);

                auto members = parse_string_array(content, pos);
                auto& member_set = _corpus_members[corpus_key];
                for (auto& m : members) {
                    member_set.insert(m);
                }

                pos = skip_ws(content, pos);
                if (pos < content.size() && content[pos] == ',') ++pos;
            }
        } else {
            // Unknown top-level key — skip its value by scanning for matching bracket/brace
            // (simplified: just skip until next '"' at depth 0 or end)
            if (pos < content.size() && (content[pos] == '[' || content[pos] == '{')) {
                char open  = content[pos];
                char close = (open == '[') ? ']' : '}';
                int depth  = 1;
                ++pos;
                while (pos < content.size() && depth > 0) {
                    if (content[pos] == '"') {
                        parse_json_string(content, pos);
                        continue;
                    }
                    if (content[pos] == open)  ++depth;
                    if (content[pos] == close) --depth;
                    ++pos;
                }
            }
        }
    }
}

} // namespace psycho
