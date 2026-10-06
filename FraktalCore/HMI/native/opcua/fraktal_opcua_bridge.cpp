#ifndef NOMINMAX
#define NOMINMAX
#endif

#include "fraktal_opcua_bridge.h"

#include "open62541.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace {

constexpr size_t kMaxBrowseNodes = 20000;
constexpr unsigned kMaxBrowseDepth = 20;
constexpr size_t kBrowseBatchSize = 128;
constexpr size_t kReadBatchSize = 256;
constexpr uint64_t kSlowReadIntervalMs = 2000;  // slow-tier (safety/power) heartbeat

struct NodeIdOwner {
  UA_NodeId value = UA_NODEID_NULL;

  NodeIdOwner() = default;
  explicit NodeIdOwner(const UA_NodeId& source) { UA_NodeId_copy(&source, &value); }
  NodeIdOwner(const NodeIdOwner&) = delete;
  NodeIdOwner& operator=(const NodeIdOwner&) = delete;
  NodeIdOwner(NodeIdOwner&& other) noexcept : value(other.value) {
    other.value = UA_NODEID_NULL;
  }
  NodeIdOwner& operator=(NodeIdOwner&& other) noexcept {
    if(this != &other) {
      UA_NodeId_clear(&value);
      value = other.value;
      other.value = UA_NODEID_NULL;
    }
    return *this;
  }
  ~NodeIdOwner() { UA_NodeId_clear(&value); }
};

struct ClientContext {
  UA_Client* client = nullptr;
  bool connected = false;
  bool discoveryComplete = false;
  bool discoveryTruncated = false;
  bool discoveryJustRan = false;  // emit the path list once, then clear
  size_t discoveredNodeCount = 0;
  size_t staleNodeCount = 0;        // cached vars that no longer resolve (per read)
  std::string lastError;
  std::unordered_map<std::string, NodeIdOwner> nodes;
  std::vector<std::string> variablePaths;
  // Config/live read tiering (the Dart classifier owns the policy): "slow"
  // paths are read once at discovery + on a heartbeat and cached; the rest are
  // read every snapshot. Keeps the recurring read to the dynamic subset while
  // the merged snapshot stays identical to a full read.
  std::unordered_set<std::string> slowPathSet;
  std::unordered_set<std::string> excludedPathSet;
  std::vector<std::string> fastPathList;
  std::vector<std::string> slowPathList;
  bool slowDirty = true;
  std::string slowValuesCache;
  std::string slowDataCache;
  uint64_t lastSlowReadMs = 0;
  // Stored connect credentials so a dropped OPC UA session (a PLC online change
  // reloads the TF6100 namespace and tears the session down) can be re-established
  // without a Dart round-trip.
  std::string endpoint;
  std::string username;
  std::string password;
  int32_t securityProfile = FRK_OPCUA_SECURITY_NONE;
  std::string securityPolicyUri;
  std::string applicationUri;
  std::string clientCertificatePath;
  std::string clientPrivateKeyPath;
  std::string clientPrivateKeyPassword;
  std::string trustListPath;
  std::string revocationListPath;
  uint32_t timeoutMs = 5000;

  ~ClientContext() {
    if(client != nullptr) {
      UA_Client_disconnect(client);
      UA_Client_delete(client);
    }
    std::fill(password.begin(), password.end(), '\0');
    std::fill(clientPrivateKeyPassword.begin(),
              clientPrivateKeyPassword.end(), '\0');
  }
};

bool readBinaryFile(const std::filesystem::path& path,
                    std::vector<uint8_t>& bytes,
                    std::string& error) {
  std::ifstream input(path, std::ios::binary | std::ios::ate);
  if(!input) {
    error = "Could not open security file: " + path.u8string();
    return false;
  }
  const std::streamsize size = input.tellg();
  if(size <= 0) {
    error = "Security file is empty: " + path.u8string();
    return false;
  }
  input.seekg(0, std::ios::beg);
  bytes.resize(static_cast<size_t>(size));
  if(!input.read(reinterpret_cast<char*>(bytes.data()), size)) {
    error = "Could not read security file: " + path.u8string();
    return false;
  }
  return true;
}

bool loadSecurityList(const std::string& configuredPath,
                      bool required,
                      std::vector<std::vector<uint8_t>>& contents,
                      std::string& error) {
  contents.clear();
  if(configuredPath.empty()) {
    if(required) error = "A trust-list file or directory is required";
    return !required;
  }
  try {
    const std::filesystem::path path = std::filesystem::u8path(configuredPath);
    std::vector<std::filesystem::path> files;
    if(std::filesystem::is_regular_file(path)) {
      files.push_back(path);
    } else if(std::filesystem::is_directory(path)) {
      for(const auto& entry : std::filesystem::directory_iterator(path)) {
        if(entry.is_regular_file()) files.push_back(entry.path());
      }
      std::sort(files.begin(), files.end());
    } else {
      error = "Security path does not exist: " + configuredPath;
      return false;
    }
    if(files.empty() && required) {
      error = "Security directory contains no files: " + configuredPath;
      return false;
    }
    for(const auto& file : files) {
      std::vector<uint8_t> bytes;
      if(!readBinaryFile(file, bytes, error)) return false;
      contents.push_back(std::move(bytes));
    }
    return true;
  } catch(const std::filesystem::filesystem_error& exception) {
    error = std::string("Could not enumerate security path: ") + exception.what();
    return false;
  }
}

std::vector<UA_ByteString> byteStrings(
    std::vector<std::vector<uint8_t>>& contents) {
  std::vector<UA_ByteString> result;
  result.reserve(contents.size());
  for(auto& bytes : contents) {
    UA_ByteString value;
    value.length = bytes.size();
    value.data = bytes.data();
    result.push_back(value);
  }
  return result;
}

UA_StatusCode privateKeyPasswordCallback(UA_ClientConfig* config,
                                         UA_ByteString* password) {
  if(config == nullptr || password == nullptr ||
     config->clientContext == nullptr) {
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }
  auto* context = static_cast<ClientContext*>(config->clientContext);
  if(context->clientPrivateKeyPassword.empty()) {
    context->lastError =
        "Encrypted OPC UA private key requires "
        "FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD";
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }
  const UA_StatusCode status =
      UA_ByteString_allocBuffer(password,
                                context->clientPrivateKeyPassword.size());
  if(status != UA_STATUSCODE_GOOD) return status;
  std::memcpy(password->data, context->clientPrivateKeyPassword.data(),
              context->clientPrivateKeyPassword.size());
  return UA_STATUSCODE_GOOD;
}

std::string uaString(const UA_String& value) {
  if(value.data == nullptr || value.length == 0) return {};
  return std::string(reinterpret_cast<const char*>(value.data), value.length);
}

void jsonEscaped(std::ostringstream& out, const std::string& value) {
  out << '"';
  for(const unsigned char ch : value) {
    switch(ch) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\b': out << "\\b"; break;
      case '\f': out << "\\f"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if(ch < 0x20) {
          static const char hex[] = "0123456789abcdef";
          out << "\\u00" << hex[(ch >> 4) & 0x0f] << hex[ch & 0x0f];
        } else {
          out << static_cast<char>(ch);
        }
    }
  }
  out << '"';
}

std::string nodeKey(const UA_NodeId& id) {
  UA_String printed = UA_STRING_NULL;
  if(UA_NodeId_print(&id, &printed) != UA_STATUSCODE_GOOD) return {};
  const std::string result = uaString(printed);
  UA_String_clear(&printed);
  return result;
}

// A cached NodeId that no longer resolves: the PLC address space changed under
// us (a symbol added/removed/renamed by an online change). Such reads are the
// signal to invalidate the discovery cache and re-browse next snapshot.
bool nodeGone(UA_StatusCode status) {
  return status == UA_STATUSCODE_BADNODEIDUNKNOWN ||
         status == UA_STATUSCODE_BADNODEIDINVALID;
}

template <typename T>
void numberArray(std::ostringstream& out, const UA_Variant& variant) {
  const auto* values = static_cast<const T*>(variant.data);
  out << '[';
  for(size_t i = 0; i < variant.arrayLength; ++i) {
    if(i != 0) out << ',';
    out << +values[i];
  }
  out << ']';
}

bool scalarJson(std::ostringstream& out, const UA_Variant& value) {
  if(value.data == nullptr || value.type == nullptr) {
    out << "null";
    return true;
  }
  const bool scalar = UA_Variant_isScalar(&value);
  if(!scalar) {
    if(value.type == &UA_TYPES[UA_TYPES_BOOLEAN]) {
      const auto* values = static_cast<const UA_Boolean*>(value.data);
      out << '[';
      for(size_t i = 0; i < value.arrayLength; ++i) {
        if(i != 0) out << ',';
        out << (values[i] ? "true" : "false");
      }
      out << ']';
      return true;
    }
    if(value.type == &UA_TYPES[UA_TYPES_SBYTE]) { numberArray<UA_SByte>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_BYTE]) { numberArray<UA_Byte>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_INT16]) { numberArray<UA_Int16>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_UINT16]) { numberArray<UA_UInt16>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_INT32]) { numberArray<UA_Int32>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_UINT32]) { numberArray<UA_UInt32>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_INT64]) { numberArray<UA_Int64>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_UINT64]) { numberArray<UA_UInt64>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_FLOAT]) { numberArray<UA_Float>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_DOUBLE]) { numberArray<UA_Double>(out, value); return true; }
    if(value.type == &UA_TYPES[UA_TYPES_STRING]) {
      const auto* values = static_cast<const UA_String*>(value.data);
      out << '[';
      for(size_t i = 0; i < value.arrayLength; ++i) {
        if(i != 0) out << ',';
        jsonEscaped(out, uaString(values[i]));
      }
      out << ']';
      return true;
    }
    return false;
  }

  if(value.type == &UA_TYPES[UA_TYPES_BOOLEAN]) {
    out << (*static_cast<const UA_Boolean*>(value.data) ? "true" : "false");
  } else if(value.type == &UA_TYPES[UA_TYPES_SBYTE]) {
    out << +*static_cast<const UA_SByte*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_BYTE]) {
    out << +*static_cast<const UA_Byte*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT16]) {
    out << *static_cast<const UA_Int16*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT16]) {
    out << *static_cast<const UA_UInt16*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT32]) {
    out << *static_cast<const UA_Int32*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT32]) {
    out << *static_cast<const UA_UInt32*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT64]) {
    out << *static_cast<const UA_Int64*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT64]) {
    out << *static_cast<const UA_UInt64*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_FLOAT]) {
    out << *static_cast<const UA_Float*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_DOUBLE]) {
    out << *static_cast<const UA_Double*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_STRING] ||
            value.type == &UA_TYPES[UA_TYPES_BYTESTRING]) {
    jsonEscaped(out, uaString(*static_cast<const UA_String*>(value.data)));
  } else if(value.type == &UA_TYPES[UA_TYPES_LOCALIZEDTEXT]) {
    jsonEscaped(out, uaString(static_cast<const UA_LocalizedText*>(value.data)->text));
  } else if(value.type == &UA_TYPES[UA_TYPES_QUALIFIEDNAME]) {
    jsonEscaped(out, uaString(static_cast<const UA_QualifiedName*>(value.data)->name));
  } else if(value.type == &UA_TYPES[UA_TYPES_DATETIME]) {
    out << *static_cast<const UA_DateTime*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_STATUSCODE]) {
    out << *static_cast<const UA_StatusCode*>(value.data);
  } else {
    return false;
  }
  return true;
}

const char* variantTypeName(const UA_Variant& value) {
  if(value.type == nullptr) return "Unknown";
  if(value.type == &UA_TYPES[UA_TYPES_BOOLEAN]) return "Boolean";
  if(value.type == &UA_TYPES[UA_TYPES_SBYTE]) return "SByte";
  if(value.type == &UA_TYPES[UA_TYPES_BYTE]) return "Byte";
  if(value.type == &UA_TYPES[UA_TYPES_INT16]) return "Int16";
  if(value.type == &UA_TYPES[UA_TYPES_UINT16]) return "UInt16";
  if(value.type == &UA_TYPES[UA_TYPES_INT32]) return "Int32";
  if(value.type == &UA_TYPES[UA_TYPES_UINT32]) return "UInt32";
  if(value.type == &UA_TYPES[UA_TYPES_INT64]) return "Int64";
  if(value.type == &UA_TYPES[UA_TYPES_UINT64]) return "UInt64";
  if(value.type == &UA_TYPES[UA_TYPES_FLOAT]) return "Float";
  if(value.type == &UA_TYPES[UA_TYPES_DOUBLE]) return "Double";
  if(value.type == &UA_TYPES[UA_TYPES_STRING]) return "String";
  if(value.type == &UA_TYPES[UA_TYPES_BYTESTRING]) return "ByteString";
  if(value.type == &UA_TYPES[UA_TYPES_LOCALIZEDTEXT]) return "LocalizedText";
  if(value.type == &UA_TYPES[UA_TYPES_QUALIFIEDNAME]) return "QualifiedName";
  if(value.type == &UA_TYPES[UA_TYPES_DATETIME]) return "DateTime";
  if(value.type == &UA_TYPES[UA_TYPES_STATUSCODE]) return "StatusCode";
  return "Unknown";
}

// UA_DateTime is a signed count of 100 ns intervals since 1601-01-01 UTC.
// JSON carries Unix microseconds as a string so Web clients do not lose
// precision by passing the 64-bit value through a JavaScript number.
void jsonTimestamp(std::ostringstream& out, UA_DateTime value) {
  constexpr UA_Int64 kUnixEpochOffset = 116444736000000000LL;
  const UA_Int64 unixMicroseconds = (value - kUnixEpochOffset) / 10;
  jsonEscaped(out, std::to_string(unixMicroseconds));
}

bool shouldTraverse(const UA_ReferenceDescription& ref, unsigned depth) {
  if(ref.nodeId.serverIndex != 0) return false;
  // Namespace-zero children under Objects are server infrastructure. Fraktal
  // application symbols live in a vendor/application namespace.
  if(depth == 0 && ref.browseName.namespaceIndex == 0) return false;
  return ref.nodeClass == UA_NODECLASS_OBJECT ||
         ref.nodeClass == UA_NODECLASS_VARIABLE;
}

bool readPublishedCount(UA_Client* client,
                        const UA_NodeId& node,
                        size_t& count) {
  UA_Variant value;
  UA_Variant_init(&value);
  const UA_StatusCode status = UA_Client_readValueAttribute(client, node, &value);
  if(status != UA_STATUSCODE_GOOD || value.data == nullptr ||
     value.arrayLength != 0) {
    UA_Variant_clear(&value);
    return false;
  }

  uint64_t converted = 0;
  bool valid = true;
  if(value.type == &UA_TYPES[UA_TYPES_SBYTE]) {
    const auto raw = *static_cast<const UA_SByte*>(value.data);
    valid = raw >= 0;
    if(valid) converted = static_cast<uint64_t>(raw);
  } else if(value.type == &UA_TYPES[UA_TYPES_BYTE]) {
    converted = *static_cast<const UA_Byte*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT16]) {
    const auto raw = *static_cast<const UA_Int16*>(value.data);
    valid = raw >= 0;
    if(valid) converted = static_cast<uint64_t>(raw);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT16]) {
    converted = *static_cast<const UA_UInt16*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT32]) {
    const auto raw = *static_cast<const UA_Int32*>(value.data);
    valid = raw >= 0;
    if(valid) converted = static_cast<uint64_t>(raw);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT32]) {
    converted = *static_cast<const UA_UInt32*>(value.data);
  } else if(value.type == &UA_TYPES[UA_TYPES_INT64]) {
    const auto raw = *static_cast<const UA_Int64*>(value.data);
    valid = raw >= 0;
    if(valid) converted = static_cast<uint64_t>(raw);
  } else if(value.type == &UA_TYPES[UA_TYPES_UINT64]) {
    converted = *static_cast<const UA_UInt64*>(value.data);
  } else {
    valid = false;
  }
  UA_Variant_clear(&value);
  if(!valid || converted > kMaxBrowseNodes) return false;
  count = static_cast<size_t>(converted);
  return true;
}

bool parseIndexedMember(const std::string& path,
                        const char* member,
                        std::string& ownerPath,
                        size_t& index) {
  const std::string marker = std::string("/") + member;
  const size_t markerAt = path.rfind(marker);
  if(markerAt == std::string::npos) return false;
  const size_t suffixAt = markerAt + marker.size();
  if(suffixAt >= path.size()) return false;

  size_t firstDigit = suffixAt;
  size_t lastDigit = path.size();
  if(path[suffixAt] == '[') {
    firstDigit = suffixAt + 1;
    if(path.back() != ']') return false;
    lastDigit = path.size() - 1;
  } else if(path[suffixAt] == '/') {
    firstDigit = suffixAt + 1;
  } else {
    return false;
  }
  if(firstDigit >= lastDigit) return false;

  size_t parsed = 0;
  for(size_t i = firstDigit; i < lastDigit; ++i) {
    const char digit = path[i];
    if(digit < '0' || digit > '9') return false;
    parsed = parsed * 10 + static_cast<size_t>(digit - '0');
    if(parsed > kMaxBrowseNodes) return false;
  }
  ownerPath = path.substr(0, markerAt);
  // TF6100 represents a PLC ARRAY as a named container followed by indexed
  // children with the same browse name, for example:
  //   Topology/Nodes/Nodes[3]
  //   .../Nodes[3]/Channels/Channels[2]
  // The published count is a sibling of the container (Topology/NodeCount or
  // Nodes[3]/ChannelCount), so normalize away that extra container segment.
  // Some OPC UA projections expose the indexed member directly; retain
  // support for that form as well.
  if(ownerPath.size() >= marker.size() &&
     ownerPath.compare(ownerPath.size() - marker.size(),
                       marker.size(), marker) == 0) {
    ownerPath.erase(ownerPath.size() - marker.size());
  }
  index = parsed;
  return true;
}

bool withinPublishedTopologyCounts(
    const std::string& path,
    const std::unordered_map<std::string, size_t>& nodeCounts,
    const std::unordered_map<std::string, size_t>& channelCounts) {
  std::string ownerPath;
  size_t index = 0;
  if(parseIndexedMember(path, "Nodes", ownerPath, index)) {
    const auto found = nodeCounts.find(ownerPath);
    if(found != nodeCounts.end() && index > found->second) return false;
  }
  if(parseIndexedMember(path, "Channels", ownerPath, index)) {
    const auto found = channelCounts.find(ownerPath);
    if(found != channelCounts.end() && index > found->second) return false;
  }
  return true;
}

struct PendingBrowseNode {
  NodeIdOwner node;
  std::string path;
  unsigned depth;

  PendingBrowseNode(const UA_NodeId& source,
                    std::string browsePath,
                    unsigned browseDepth)
      : node(source), path(std::move(browsePath)), depth(browseDepth) {}
};

uint64_t steadyMs() {
  return static_cast<uint64_t>(
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now().time_since_epoch())
          .count());
}

// Splits the discovered variable paths into the "slow" (config) subset the Dart
// tier flagged and the "fast" remainder, and invalidates the slow cache so the
// next snapshot re-reads it once.
void repartition(ClientContext& context) {
  context.fastPathList.clear();
  context.slowPathList.clear();
  for(const auto& path : context.variablePaths) {
    // Excluded (on-demand) paths are kept in the NodeId cache (so an explicit
    // read_values can serve them) but never enter a snapshot read list.
    if(context.excludedPathSet.find(path) != context.excludedPathSet.end())
      continue;
    if(context.slowPathSet.find(path) != context.slowPathSet.end())
      context.slowPathList.push_back(path);
    else
      context.fastPathList.push_back(path);
  }
  context.slowDirty = true;
  context.slowValuesCache.clear();
  context.slowDataCache.clear();
}

bool discover(ClientContext& context) {
  context.nodes.clear();
  context.variablePaths.clear();
  context.discoveredNodeCount = 0;
  context.discoveryTruncated = false;

  std::unordered_set<std::string> visited;
  std::unordered_map<std::string, size_t> topologyNodeCounts;
  std::unordered_map<std::string, size_t> topologyChannelCounts;
  std::vector<PendingBrowseNode> pending;
  const UA_NodeId objects = UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER);
  visited.insert(nodeKey(objects));
  pending.emplace_back(objects, "", 0);

  size_t cursor = 0;
  size_t batchLimit = kBrowseBatchSize;
  while(cursor < pending.size() &&
        context.discoveredNodeCount < kMaxBrowseNodes) {
    const size_t batchSize =
        std::min(batchLimit, pending.size() - cursor);
    UA_BrowseRequest request;
    UA_BrowseRequest_init(&request);
    request.requestedMaxReferencesPerNode = 0;
    request.nodesToBrowse = static_cast<UA_BrowseDescription*>(
        UA_Array_new(batchSize, &UA_TYPES[UA_TYPES_BROWSEDESCRIPTION]));
    request.nodesToBrowseSize = batchSize;
    for(size_t i = 0; i < batchSize; ++i) {
      UA_BrowseDescription& description = request.nodesToBrowse[i];
      UA_NodeId_copy(&pending[cursor + i].node.value, &description.nodeId);
      description.browseDirection = UA_BROWSEDIRECTION_FORWARD;
      description.referenceTypeId =
          UA_NODEID_NUMERIC(0, UA_NS0ID_HIERARCHICALREFERENCES);
      description.includeSubtypes = true;
      description.resultMask = UA_BROWSERESULTMASK_ALL;
    }

    UA_BrowseResponse response =
        UA_Client_Service_browse(context.client, request);
    UA_BrowseRequest_clear(&request);
    const UA_StatusCode serviceResult = response.responseHeader.serviceResult;
    if(serviceResult == UA_STATUSCODE_BADTOOMANYOPERATIONS && batchSize > 1) {
      UA_BrowseResponse_clear(&response);
      batchLimit = std::max<size_t>(1, batchSize / 2);
      continue;
    }
    if(serviceResult != UA_STATUSCODE_GOOD) {
      context.lastError = std::string("Browse failed: ") +
                          UA_StatusCode_name(serviceResult);
      UA_BrowseResponse_clear(&response);
      return false;
    }

    const size_t resultCount = std::min(response.resultsSize, batchSize);
    for(size_t resultIndex = 0; resultIndex < resultCount; ++resultIndex) {
      // Appending children can reallocate pending, so never retain a reference
      // into the vector while processing this result.
      const std::string parentPath = pending[cursor + resultIndex].path;
      const unsigned parentDepth = pending[cursor + resultIndex].depth;
      const UA_BrowseResult& result = response.results[resultIndex];
      if(result.statusCode != UA_STATUSCODE_GOOD) continue;

      // NodeCount and ChannelCount bound the otherwise large fixed TwinCAT
      // arrays. Read these siblings before enqueueing array elements so unused
      // Nodes[7..64] and Channels[n+1..16] never consume the namespace budget.
      for(size_t i = 0; i < result.referencesSize; ++i) {
        const UA_ReferenceDescription& ref = result.references[i];
        if(ref.nodeClass != UA_NODECLASS_VARIABLE ||
           ref.nodeId.serverIndex != 0) {
          continue;
        }
        const std::string name = uaString(ref.browseName.name);
        if(name != "NodeCount" && name != "ChannelCount") continue;
        size_t count = 0;
        if(!readPublishedCount(context.client, ref.nodeId.nodeId, count)) continue;
        if(name == "NodeCount") {
          topologyNodeCounts[parentPath] = count;
        } else {
          topologyChannelCounts[parentPath] = count;
        }
      }

      for(size_t i = 0;
          i < result.referencesSize &&
          context.discoveredNodeCount < kMaxBrowseNodes;
          ++i) {
        const UA_ReferenceDescription& ref = result.references[i];
        if(!shouldTraverse(ref, parentDepth)) continue;
        const std::string name = uaString(ref.browseName.name);
        if(name.empty()) continue;
        const UA_NodeId& child = ref.nodeId.nodeId;
        const std::string idKey = nodeKey(child);
        if(idKey.empty() || !visited.insert(idKey).second) continue;
        const std::string path = parentPath.empty()
                                     ? name
                                     : parentPath + "/" + name;
        if(!withinPublishedTopologyCounts(
               path, topologyNodeCounts, topologyChannelCounts)) {
          continue;
        }
        ++context.discoveredNodeCount;
        context.nodes.emplace(path, NodeIdOwner(child));
        if(ref.nodeClass == UA_NODECLASS_VARIABLE)
          context.variablePaths.push_back(path);
        if(parentDepth < kMaxBrowseDepth)
          pending.emplace_back(child, path, parentDepth + 1);
      }
    }
    UA_BrowseResponse_clear(&response);
    cursor += batchSize;
  }

  context.discoveryTruncated =
      context.discoveredNodeCount >= kMaxBrowseNodes || cursor < pending.size();
  context.discoveryComplete = true;
  context.discoveryJustRan = true;
  repartition(context);
  return true;
}

// Reads the given paths' values and appends them to the flat `values` object and
// the v2 `dataValues` object. Accumulates staleNodeCount (the caller resets it).
bool readValuesInto(ClientContext& context,
                    const std::vector<std::string>& paths,
                    std::ostringstream& values,
                    bool& firstValue,
                    std::ostringstream& dataValues,
                    bool& firstDataValue) {
  size_t cursor = 0;
  size_t batchLimit = kReadBatchSize;
  while(cursor < paths.size()) {
    const size_t batchSize = std::min(batchLimit, paths.size() - cursor);
    UA_ReadRequest request;
    UA_ReadRequest_init(&request);
    request.nodesToRead = static_cast<UA_ReadValueId*>(
        UA_Array_new(batchSize, &UA_TYPES[UA_TYPES_READVALUEID]));
    request.nodesToReadSize = batchSize;
    for(size_t i = 0; i < batchSize; ++i) {
      const auto found = context.nodes.find(paths[cursor + i]);
      if(found == context.nodes.end()) continue;
      UA_NodeId_copy(&found->second.value, &request.nodesToRead[i].nodeId);
      request.nodesToRead[i].attributeId = UA_ATTRIBUTEID_VALUE;
    }

    UA_ReadResponse response = UA_Client_Service_read(context.client, request);
    UA_ReadRequest_clear(&request);
    const UA_StatusCode serviceResult = response.responseHeader.serviceResult;
    if(serviceResult == UA_STATUSCODE_BADTOOMANYOPERATIONS && batchSize > 1) {
      UA_ReadResponse_clear(&response);
      batchLimit = std::max<size_t>(1, batchSize / 2);
      continue;
    }
    if(serviceResult != UA_STATUSCODE_GOOD) {
      context.lastError = std::string("Read failed: ") +
                          UA_StatusCode_name(serviceResult);
      UA_ReadResponse_clear(&response);
      return false;
    }

    const size_t resultCount = std::min(response.resultsSize, batchSize);
    for(size_t i = 0; i < resultCount; ++i) {
      const UA_DataValue& dataValue = response.results[i];
      // A cached NodeId that no longer resolves means the PLC address space
      // changed under us (online change). Count it; a surge invalidates the
      // discovery cache so the next snapshot re-browses the fresh tree.
      if(nodeGone(dataValue.status)) ++context.staleNodeCount;

      std::ostringstream encoded;
      const bool hasEncodedValue =
          dataValue.hasValue && scalarJson(encoded, dataValue.value);
      if(!firstDataValue) dataValues << ',';
      firstDataValue = false;
      jsonEscaped(dataValues, paths[cursor + i]);
      dataValues << ":{\"status\":" << dataValue.status
                 << ",\"type\":";
      jsonEscaped(dataValues,
                  dataValue.hasValue ? variantTypeName(dataValue.value)
                                     : "Unknown");
      if(hasEncodedValue) dataValues << ",\"value\":" << encoded.str();
      if(dataValue.hasSourceTimestamp) {
        dataValues << ",\"sourceTimestampUs\":";
        jsonTimestamp(dataValues, dataValue.sourceTimestamp);
      }
      if(dataValue.hasServerTimestamp) {
        dataValues << ",\"serverTimestampUs\":";
        jsonTimestamp(dataValues, dataValue.serverTimestamp);
      }
      dataValues << '}';

      // Keep the v1 flat values object for compatibility and discovery. A
      // non-Good value is deliberately absent so legacy clients cannot render
      // a value that OPC UA says is unusable.
      if(!UA_StatusCode_isGood(dataValue.status) || !hasEncodedValue) continue;
      if(!firstValue) values << ',';
      firstValue = false;
      jsonEscaped(values, paths[cursor + i]);
      values << ':' << encoded.str();
    }
    UA_ReadResponse_clear(&response);
    cursor += batchSize;
  }
  return true;
}

// Diagnostic view of every child directly under Objects, before any
// traversal filtering, so an empty snapshot names what the server offered.
void describeRootChildren(ClientContext& context, std::ostringstream& out) {
  UA_BrowseRequest request;
  UA_BrowseRequest_init(&request);
  request.requestedMaxReferencesPerNode = 0;
  request.nodesToBrowse = UA_BrowseDescription_new();
  request.nodesToBrowseSize = 1;
  request.nodesToBrowse[0].nodeId = UA_NODEID_NUMERIC(0, UA_NS0ID_OBJECTSFOLDER);
  request.nodesToBrowse[0].browseDirection = UA_BROWSEDIRECTION_FORWARD;
  request.nodesToBrowse[0].referenceTypeId =
      UA_NODEID_NUMERIC(0, UA_NS0ID_HIERARCHICALREFERENCES);
  request.nodesToBrowse[0].includeSubtypes = true;
  request.nodesToBrowse[0].resultMask = UA_BROWSERESULTMASK_ALL;
  UA_BrowseResponse response = UA_Client_Service_browse(context.client, request);
  UA_BrowseRequest_clear(&request);
  bool first = true;
  if(response.responseHeader.serviceResult == UA_STATUSCODE_GOOD) {
    for(size_t resultIndex = 0; resultIndex < response.resultsSize; ++resultIndex) {
      const UA_BrowseResult& result = response.results[resultIndex];
      for(size_t i = 0; i < result.referencesSize; ++i) {
        const UA_ReferenceDescription& ref = result.references[i];
        std::ostringstream item;
        item << ref.browseName.namespaceIndex << ':'
             << uaString(ref.browseName.name) << '(';
        switch(ref.nodeClass) {
          case UA_NODECLASS_OBJECT: item << "Object"; break;
          case UA_NODECLASS_VARIABLE: item << "Variable"; break;
          default: item << static_cast<int>(ref.nodeClass); break;
        }
        item << ')';
        if(!first) out << ',';
        first = false;
        jsonEscaped(out, item.str());
      }
    }
  }
  UA_BrowseResponse_clear(&response);
}

// Read the standard Server/NamespaceArray even when access control hides all
// application objects. This separates "NodeManager not loaded" from "loaded
// namespace is not browsable by this identity" in startup diagnostics.
void describeNamespaces(ClientContext& context, std::ostringstream& out) {
  UA_Variant value;
  UA_Variant_init(&value);
  const UA_StatusCode status = UA_Client_readValueAttribute(
      context.client,
      UA_NODEID_NUMERIC(0, UA_NS0ID_SERVER_NAMESPACEARRAY),
      &value);
  if(status == UA_STATUSCODE_GOOD &&
     UA_Variant_hasArrayType(&value, &UA_TYPES[UA_TYPES_STRING]) &&
     scalarJson(out, value)) {
    UA_Variant_clear(&value);
    return;
  }
  UA_Variant_clear(&value);
  out << "[]";
}

UA_StatusCode configureClient(ClientContext& context, UA_ClientConfig* config) {
  if(context.securityProfile == FRK_OPCUA_SECURITY_NONE) {
    return UA_ClientConfig_setDefault(config);
  }
  if(context.securityProfile != FRK_OPCUA_SECURITY_SIGN_ENCRYPT_USER &&
     context.securityProfile != FRK_OPCUA_SECURITY_SIGN_ENCRYPT_ANONYMOUS) {
    context.lastError = "Unsupported OPC UA security profile";
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }
  if(context.securityPolicyUri.empty() || context.applicationUri.empty() ||
     context.clientCertificatePath.empty() ||
     context.clientPrivateKeyPath.empty()) {
    context.lastError =
        "Secure OPC UA requires policy URI, application URI, certificate, and private key";
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }

  std::vector<uint8_t> certificateBytes;
  std::vector<uint8_t> privateKeyBytes;
  if(!readBinaryFile(std::filesystem::u8path(context.clientCertificatePath),
                     certificateBytes, context.lastError) ||
     !readBinaryFile(std::filesystem::u8path(context.clientPrivateKeyPath),
                     privateKeyBytes, context.lastError)) {
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }
  std::vector<std::vector<uint8_t>> trustContents;
  std::vector<std::vector<uint8_t>> revocationContents;
  if(!loadSecurityList(context.trustListPath, true, trustContents,
                       context.lastError) ||
     !loadSecurityList(context.revocationListPath, false, revocationContents,
                       context.lastError)) {
    std::fill(privateKeyBytes.begin(), privateKeyBytes.end(), 0);
    return UA_STATUSCODE_BADCONFIGURATIONERROR;
  }
  std::vector<UA_ByteString> trustList = byteStrings(trustContents);
  std::vector<UA_ByteString> revocationList = byteStrings(revocationContents);
  UA_ByteString certificate{certificateBytes.size(), certificateBytes.data()};
  UA_ByteString privateKey{privateKeyBytes.size(), privateKeyBytes.data()};
  config->clientContext = &context;
  config->privateKeyPasswordCallback = privateKeyPasswordCallback;
  UA_StatusCode status = UA_ClientConfig_setDefaultEncryption(
      config, certificate, privateKey,
      trustList.empty() ? nullptr : trustList.data(), trustList.size(),
      revocationList.empty() ? nullptr : revocationList.data(),
      revocationList.size());
  std::fill(privateKeyBytes.begin(), privateKeyBytes.end(), 0);
  if(status != UA_STATUSCODE_GOOD) {
    if(context.lastError.empty()) {
      context.lastError =
          std::string("Encrypted client configuration failed: ") +
          UA_StatusCode_name(status);
    }
    return status;
  }

  config->securityMode = UA_MESSAGESECURITYMODE_SIGNANDENCRYPT;
  UA_String_clear(&config->securityPolicyUri);
  config->securityPolicyUri = UA_STRING_ALLOC(context.securityPolicyUri.c_str());
  UA_String_clear(&config->clientDescription.applicationUri);
  config->clientDescription.applicationUri =
      UA_STRING_ALLOC(context.applicationUri.c_str());
  if(config->securityPolicyUri.data == nullptr ||
     config->clientDescription.applicationUri.data == nullptr) {
    context.lastError = "Could not allocate secure OPC UA client identity";
    return UA_STATUSCODE_BADOUTOFMEMORY;
  }
  return UA_STATUSCODE_GOOD;
}

bool connectStored(ClientContext& context, const char* operation) {
  context.lastError.clear();
  if(context.endpoint.empty()) {
    context.lastError = std::string(operation) +
                        " attempted without a stored endpoint";
    return false;
  }
  if(context.client != nullptr) {
    UA_Client_disconnect(context.client);
    UA_Client_delete(context.client);
    context.client = nullptr;
  }
  context.client = UA_Client_new();
  if(context.client == nullptr) {
    context.lastError = "UA_Client_new failed";
    context.connected = false;
    return false;
  }
  UA_ClientConfig* config = UA_Client_getConfig(context.client);
  UA_StatusCode status = configureClient(context, config);
  if(status == UA_STATUSCODE_GOOD) {
    config->timeout = context.timeoutMs;
    if(!context.username.empty()) {
      status = UA_Client_connectUsername(context.client, context.endpoint.c_str(),
                                         context.username.c_str(),
                                         context.password.c_str());
    } else {
      status = UA_Client_connect(context.client, context.endpoint.c_str());
    }
  }
  context.connected = status == UA_STATUSCODE_GOOD;
  context.nodes.clear();
  context.variablePaths.clear();
  // The path->tier partition is rebuilt by discover(); drop the stale derived
  // state now. slowPathSet (the Dart policy) intentionally persists a reconnect.
  context.fastPathList.clear();
  context.slowPathList.clear();
  context.slowValuesCache.clear();
  context.slowDataCache.clear();
  context.slowDirty = true;
  context.discoveryComplete = false;
  context.discoveryTruncated = false;
  context.discoveredNodeCount = 0;
  if(!context.connected) {
    if(context.lastError.empty()) {
      context.lastError = std::string(operation) + " failed: " +
                          UA_StatusCode_name(status);
    }
    return false;
  }
  context.lastError.clear();
  return true;
}

// Re-establish the OPC UA session with the cached credentials. Always clears the
// cached NodeId map: after a reconnect the browse paths may map to fresh NodeIds,
// so the next snapshot re-discovers. Returns whether a usable session is up.
bool reconnect(ClientContext& context) {
  return connectStored(context, "Reconnect");
}

// Recover transparently from a dropped session. A PLC online change reloads the
// TF6100 namespace and tears the session down; open62541 only auto-reconnects
// when its event loop is pumped, and this client is driven by explicit service
// calls. So check the live state and reconnect here before each snapshot.
bool ensureSession(ClientContext& context) {
  if(!context.connected || context.client == nullptr) return reconnect(context);
  UA_SecureChannelState channelState = UA_SECURECHANNELSTATE_CLOSED;
  UA_SessionState sessionState = UA_SESSIONSTATE_CLOSED;
  UA_StatusCode connectStatus = UA_STATUSCODE_GOOD;
  UA_Client_getState(context.client, &channelState, &sessionState, &connectStatus);
  if(connectStatus != UA_STATUSCODE_GOOD ||
     sessionState != UA_SESSIONSTATE_ACTIVATED) {
    return reconnect(context);
  }
  return true;
}

template <typename T>
int32_t writeScalar(ClientContext* context,
                    const char* path,
                    const T& value,
                    const UA_DataType& type) {
  if(context == nullptr || !context->connected || path == nullptr) return 0;
  const auto found = context->nodes.find(path);
  if(found == context->nodes.end()) {
    context->lastError = std::string("Unknown browse path: ") + path;
    return 0;
  }
  const UA_StatusCode status = UA_Client_writeValueAttribute_scalar(
      context->client, found->second.value, &value, &type);
  if(status != UA_STATUSCODE_GOOD) {
    context->lastError = std::string("Write failed: ") + UA_StatusCode_name(status);
    return 0;
  }
  return 1;
}

}  // namespace

extern "C" {

FrkOpcUaHandle frk_opcua_create(void) {
  return new ClientContext();
}

void frk_opcua_destroy(FrkOpcUaHandle handle) {
  delete static_cast<ClientContext*>(handle);
}

int32_t frk_opcua_connect(FrkOpcUaHandle handle,
                          const char* endpoint,
                          const char* username,
                          const char* password,
                          uint32_t timeout_ms) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr || endpoint == nullptr) return 0;
  context->endpoint = endpoint;
  context->username = (username != nullptr) ? username : "";
  std::fill(context->password.begin(), context->password.end(), '\0');
  context->password = (password != nullptr) ? password : "";
  context->securityProfile = FRK_OPCUA_SECURITY_NONE;
  context->securityPolicyUri.clear();
  context->applicationUri.clear();
  context->clientCertificatePath.clear();
  context->clientPrivateKeyPath.clear();
  std::fill(context->clientPrivateKeyPassword.begin(),
            context->clientPrivateKeyPassword.end(), '\0');
  context->clientPrivateKeyPassword.clear();
  context->trustListPath.clear();
  context->revocationListPath.clear();
  context->timeoutMs = timeout_ms;
  return connectStored(*context, "Connect") ? 1 : 0;
}

int32_t frk_opcua_connect_secure(FrkOpcUaHandle handle,
                                 const char* endpoint,
                                 const char* username,
                                 const char* password,
                                 uint32_t timeout_ms,
                                 int32_t security_profile,
                                 const char* security_policy_uri,
                                 const char* application_uri,
                                 const char* client_certificate_path,
                                 const char* client_private_key_path,
                                 const char* client_private_key_password,
                                 const char* trust_list_path,
                                 const char* revocation_list_path) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr || endpoint == nullptr) return 0;
  context->endpoint = endpoint;
  context->username = (username != nullptr) ? username : "";
  std::fill(context->password.begin(), context->password.end(), '\0');
  context->password = (password != nullptr) ? password : "";
  context->securityProfile = security_profile;
  context->securityPolicyUri =
      (security_policy_uri != nullptr) ? security_policy_uri : "";
  context->applicationUri =
      (application_uri != nullptr) ? application_uri : "";
  context->clientCertificatePath =
      (client_certificate_path != nullptr) ? client_certificate_path : "";
  context->clientPrivateKeyPath =
      (client_private_key_path != nullptr) ? client_private_key_path : "";
  std::fill(context->clientPrivateKeyPassword.begin(),
            context->clientPrivateKeyPassword.end(), '\0');
  context->clientPrivateKeyPassword =
      (client_private_key_password != nullptr)
          ? client_private_key_password
          : "";
  context->trustListPath =
      (trust_list_path != nullptr) ? trust_list_path : "";
  context->revocationListPath =
      (revocation_list_path != nullptr) ? revocation_list_path : "";
  context->timeoutMs = timeout_ms;
  return connectStored(*context, "Connect") ? 1 : 0;
}

void frk_opcua_disconnect(FrkOpcUaHandle handle) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr || context->client == nullptr) return;
  UA_Client_disconnect(context->client);
  context->connected = false;
  std::fill(context->password.begin(), context->password.end(), '\0');
  context->password.clear();
  std::fill(context->clientPrivateKeyPassword.begin(),
            context->clientPrivateKeyPassword.end(), '\0');
  context->clientPrivateKeyPassword.clear();
  context->nodes.clear();
  context->variablePaths.clear();
  context->discoveryComplete = false;
  context->discoveryTruncated = false;
  context->discoveredNodeCount = 0;
}

int32_t frk_opcua_is_connected(FrkOpcUaHandle handle) {
  const auto* context = static_cast<const ClientContext*>(handle);
  return context != nullptr && context->connected ? 1 : 0;
}

const char* frk_opcua_last_error(FrkOpcUaHandle handle) {
  const auto* context = static_cast<const ClientContext*>(handle);
  return context == nullptr ? "Invalid OPC UA client handle" : context->lastError.c_str();
}

char* frk_opcua_snapshot_json(FrkOpcUaHandle handle) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr) return nullptr;
  context->lastError.clear();

  // Recover transparently from a dropped OPC UA session (a PLC online change
  // reloads the TF6100 namespace and tears the session down). ensureSession
  // reconnects with the cached endpoint and clears the NodeId cache, so the
  // fresh structure is re-browsed below.
  if(!ensureSession(*context)) return nullptr;

  // Lazy discovery: browse on first snapshot, or after a reconnect/cache clear.
  if(!context->discoveryComplete && !discover(*context)) return nullptr;
  // Dual-rate read: fast (dynamic) paths every snapshot; slow (config) paths once
  // at discovery, then on a heartbeat or after an explicit refresh, cached in
  // between. The merged output is identical to a full read, so the mapper is
  // unchanged. The Dart classifier (opcua_field_tier.dart) owns which is which.
  // Any service-level read failure is treated as link loss: reconnect now and let
  // the next snapshot rediscover, rather than serving a stale/empty tree.
  context->staleNodeCount = 0;
  std::ostringstream fastValues;
  bool firstFastValue = true;
  std::ostringstream fastData;
  bool firstFastData = true;
  if(!readValuesInto(*context, context->fastPathList, fastValues, firstFastValue,
                     fastData, firstFastData)) {
    reconnect(*context);
    return nullptr;
  }
  const uint64_t nowMs = steadyMs();
  if(context->slowDirty ||
     nowMs - context->lastSlowReadMs >= kSlowReadIntervalMs) {
    std::ostringstream slowValues;
    bool firstSlowValue = true;
    std::ostringstream slowData;
    bool firstSlowData = true;
    if(!readValuesInto(*context, context->slowPathList, slowValues,
                       firstSlowValue, slowData, firstSlowData)) {
      reconnect(*context);
      return nullptr;
    }
    context->slowValuesCache = slowValues.str();
    context->slowDataCache = slowData.str();
    context->slowDirty = false;
    context->lastSlowReadMs = nowMs;
  }
  std::string valuesStr = fastValues.str();
  if(!context->slowValuesCache.empty()) {
    if(!valuesStr.empty()) valuesStr.push_back(',');
    valuesStr += context->slowValuesCache;
  }
  std::string dataStr = fastData.str();
  if(!context->slowDataCache.empty()) {
    if(!dataStr.empty()) dataStr.push_back(',');
    dataStr += context->slowDataCache;
  }

  // Structural change with a SURVIVING session (online change that did not drop
  // the link): if too many cached NodeIds no longer resolve, the address space
  // changed under us. Invalidate the cache so the next snapshot re-browses.
  if(!context->variablePaths.empty() &&
     context->staleNodeCount * 5 >= context->variablePaths.size()) {
    context->discoveryComplete = false;
  }

  std::ostringstream rootChildren;
  describeRootChildren(*context, rootChildren);
  std::ostringstream namespaces;
  describeNamespaces(*context, namespaces);

  // On the snapshot that followed a (re)discover, emit the full discovered
  // variable-path list once so the client can classify paths into read tiers
  // (excluded paths are never read into `values`, so the client can only learn
  // them here). Cleared after emission; the set is stable until rediscovery.
  std::string pathsJson = "[]";
  if(context->discoveryJustRan) {
    std::ostringstream paths;
    paths << '[';
    bool firstPath = true;
    for(const auto& path : context->variablePaths) {
      if(!firstPath) paths << ',';
      firstPath = false;
      jsonEscaped(paths, path);
    }
    paths << ']';
    pathsJson = paths.str();
    context->discoveryJustRan = false;
  }

  std::ostringstream document;
  document << "{\"protocol\":\"fraktal.opcua.snapshot.v1\",\"nodeCount\":"
           << context->discoveredNodeCount
           << ",\"truncated\":"
           << (context->discoveryTruncated ? "true" : "false")
           << ",\"rootChildren\":[" << rootChildren.str()
           << "],\"namespaces\":" << namespaces.str()
           << ",\"paths\":" << pathsJson
           << ",\"values\":{" << valuesStr
           << "},\"dataValues\":{" << dataStr << "}}";
  const std::string text = document.str();
  auto* result = static_cast<char*>(std::malloc(text.size() + 1));
  if(result == nullptr) return nullptr;
  std::memcpy(result, text.c_str(), text.size() + 1);
  return result;
}

void frk_opcua_free_string(char* value) { std::free(value); }

int32_t frk_opcua_set_slow_paths(FrkOpcUaHandle handle, const char* paths) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr) return 0;
  context->slowPathSet.clear();
  if(paths != nullptr) {
    const std::string blob(paths);
    size_t start = 0;
    while(start < blob.size()) {
      const size_t newline = blob.find('\n', start);
      const size_t end = newline == std::string::npos ? blob.size() : newline;
      if(end > start) {
        context->slowPathSet.insert(blob.substr(start, end - start));
      }
      if(newline == std::string::npos) break;
      start = newline + 1;
    }
  }
  repartition(*context);
  return 1;
}

int32_t frk_opcua_set_excluded_paths(FrkOpcUaHandle handle, const char* paths) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr) return 0;
  context->excludedPathSet.clear();
  if(paths != nullptr) {
    const std::string blob(paths);
    size_t start = 0;
    while(start < blob.size()) {
      const size_t newline = blob.find('\n', start);
      const size_t end = newline == std::string::npos ? blob.size() : newline;
      if(end > start) {
        context->excludedPathSet.insert(blob.substr(start, end - start));
      }
      if(newline == std::string::npos) break;
      start = newline + 1;
    }
  }
  repartition(*context);
  return 1;
}

void frk_opcua_refresh_slow(FrkOpcUaHandle handle) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context != nullptr) context->slowDirty = true;
}

char* frk_opcua_read_values_json(FrkOpcUaHandle handle, const char* paths) {
  auto* context = static_cast<ClientContext*>(handle);
  if(context == nullptr) return nullptr;
  context->lastError.clear();
  if(!ensureSession(*context)) return nullptr;
  if(!context->discoveryComplete && !discover(*context)) return nullptr;

  std::vector<std::string> requested;
  if(paths != nullptr) {
    const std::string blob(paths);
    size_t start = 0;
    while(start < blob.size()) {
      const size_t newline = blob.find('\n', start);
      const size_t end = newline == std::string::npos ? blob.size() : newline;
      if(end > start) requested.push_back(blob.substr(start, end - start));
      if(newline == std::string::npos) break;
      start = newline + 1;
    }
  }

  std::ostringstream values;
  bool firstValue = true;
  std::ostringstream dataValues;  // required by readValuesInto; not returned
  bool firstDataValue = true;
  if(!readValuesInto(*context, requested, values, firstValue,
                     dataValues, firstDataValue)) {
    return nullptr;
  }
  std::ostringstream document;
  document << "{\"values\":{" << values.str() << "}}";
  const std::string text = document.str();
  auto* result = static_cast<char*>(std::malloc(text.size() + 1));
  if(result == nullptr) return nullptr;
  std::memcpy(result, text.c_str(), text.size() + 1);
  return result;
}

int32_t frk_opcua_write_bool(FrkOpcUaHandle handle,
                             const char* browse_path,
                             int32_t value) {
  const UA_Boolean converted = value != 0;
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_BOOLEAN]);
}

int32_t frk_opcua_write_int64(FrkOpcUaHandle handle,
                              const char* browse_path,
                              int64_t value) {
  const UA_Int64 converted = value;
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_INT64]);
}

int32_t frk_opcua_write_int32(FrkOpcUaHandle handle,
                              const char* browse_path,
                              int32_t value) {
  const UA_Int32 converted = value;
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_INT32]);
}

int32_t frk_opcua_write_uint32(FrkOpcUaHandle handle,
                               const char* browse_path,
                               uint32_t value) {
  const UA_UInt32 converted = value;
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_UINT32]);
}

int32_t frk_opcua_write_double(FrkOpcUaHandle handle,
                               const char* browse_path,
                               double value) {
  const UA_Double converted = value;
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_DOUBLE]);
}

int32_t frk_opcua_write_string(FrkOpcUaHandle handle,
                               const char* browse_path,
                               const char* value) {
  UA_String converted = UA_STRING(const_cast<char*>(value == nullptr ? "" : value));
  return writeScalar(static_cast<ClientContext*>(handle), browse_path, converted,
                     UA_TYPES[UA_TYPES_STRING]);
}

}  // extern "C"
