// Direct-ADS transport bridge. Wraps TcAdsDll; emits fraktal.opcua.snapshot.v1.
//
// Discovery: SYM_UPLOADINFO2 (0xF00F) -> sizes; SYM_UPLOAD (0xF00B) -> top-level
// symbols; SYM_DT_UPLOAD (0xF00E) -> datatype table. Each datatype entry carries
// its members as nested sub-entries (recursively), referencing member types by
// name. We build a datatype map, then expand every top-level symbol's type into
// leaf scalars, accumulating byte offsets and dotted names. Leaves get a value
// handle (SYM_HNDBYNAME 0xF003) and are read (SYM_VALBYHND 0xF005).
//
// All ADS index groups are pinned against Beckhoff TcAdsDef.h; the datatype
// upload pair (0xF00F/0xF00E) is verified live against the pinned runtime.

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include "fraktal_ads_bridge.h"
#include "TcAdsAPI.h"
#include "TcAdsDef.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace {

constexpr uint32_t kSymUploadInfo2 = 0xF00F;  // {nSym,nSymSize,nDt,nDtSize,...}
constexpr uint32_t kSymUpload = 0xF00B;        // top-level symbol entries
constexpr uint32_t kSymDtUpload = 0xF00E;      // datatype entries
constexpr uint32_t kSymHndByName = ADSIGRP_SYM_HNDBYNAME;    // 0xF003
constexpr uint32_t kSymValByHnd = ADSIGRP_SYM_VALBYHND;      // 0xF005
constexpr uint32_t kSymReleaseHnd = ADSIGRP_SYM_RELEASEHND;  // 0xF006
// ADS sum-command index groups (Beckhoff well-known; pin-verify per runtime):
// read N symbols by handle in ONE round trip. Request is N x {iGroup,iOffs,len};
// reply is N x errorCode (uint32) followed by N data blocks in order.
constexpr uint32_t kSumRead = 0xF080;   // ADSIGRP_SUMUP_READ
constexpr uint32_t kSumHndByName = 0xF082;  // ADSIGRP_SUMUP_READWRITE (name->hnd)
constexpr uint32_t kSumWrite = 0xF085;  // ADSIGRP_SUMUP_WRITE

constexpr size_t kMaxLeaves = 40000;   // guardrail (mirrors the OPC UA cap)
constexpr unsigned kMaxDepth = 24;

// Bound every ADS round trip so an unreachable/unrouted target fails fast with a
// clear error instead of hanging the worker isolate (and the UI) on TcAdsDll's
// long default timeout. 4 s covers a slow-but-live remote runtime; a genuinely
// unreachable AmsNetId (no AMS route) returns promptly.
constexpr uint32_t kAdsTimeoutMs = 4000;

// ADS scalar data types (TcAdsDef.h ADST_*). Enough to decode the Fraktal
// contract's published leaves; structs/arrays are expanded, not decoded here.
enum : uint32_t {
  ADST_VOID = 0,
  ADST_INT8 = 16, ADST_UINT8 = 17, ADST_INT16 = 2, ADST_UINT16 = 18,
  ADST_INT32 = 3, ADST_UINT32 = 19, ADST_INT64 = 20, ADST_UINT64 = 21,
  ADST_REAL32 = 4, ADST_REAL64 = 5, ADST_BIT = 33, ADST_STRING = 30,
};

std::string jsonEscape(const std::string& s) {
  std::string out;
  out.reserve(s.size() + 2);
  for (char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          char buf[8];
          std::snprintf(buf, sizeof(buf), "\\u%04x", c);
          out += buf;
        } else {
          out += c;
        }
    }
  }
  return out;
}

// A discovered leaf: dotted ADS symbol name, its scalar type + byte size.
struct Leaf {
  std::string symbol;   // MAIN.PneumaticPress.Status.State
  std::string path;     // PLC1/MAIN/PneumaticPress/Status/State
  uint32_t adsType;
  uint32_t size;
  uint32_t handle = 0;  // SYM_VALBYHND handle (0 = not yet resolved)
};

// One array dimension of a symbol/member/datatype (AdsDatatypeArrayInfo).
struct ArrayDim {
  uint32_t lBound;
  uint32_t elements;
};

// One member of a struct datatype (from a datatype sub-entry).
struct Member {
  std::string name;
  std::string typeName;  // resolves into the datatype map (empty = scalar leaf)
  uint32_t offs;
  uint32_t adsType;
  uint32_t size;
  uint16_t subItems;     // >0 means inline-expanded (rare); usually resolves by typeName
  std::vector<ArrayDim> arrays;  // non-empty: this member is an array of typeName
};

// A datatype: its scalar type (if terminal) and its members (if a struct), or its
// array dimensions + element type name (if a typedef'd array, e.g.
// "ARRAY [1..n] OF ST_Foo").
struct DataType {
  std::string name;
  std::string elementType;  // the `type` field: array element / alias base type
  uint32_t adsType;
  uint32_t size;
  std::vector<Member> members;
  std::vector<ArrayDim> arrays;
};

struct Reader {
  const uint8_t* p;
  const uint8_t* end;
  bool ok = true;
  uint32_t u32() {
    if (p + 4 > end) { ok = false; return 0; }
    uint32_t v;
    std::memcpy(&v, p, 4);
    p += 4;
    return v;
  }
  uint16_t u16() {
    if (p + 2 > end) { ok = false; return 0; }
    uint16_t v;
    std::memcpy(&v, p, 2);
    p += 2;
    return v;
  }
  std::string str(size_t n) {
    if (p + n > end) { ok = false; return {}; }
    std::string s(reinterpret_cast<const char*>(p), n);
    p += n;
    return s;
  }
  void skip(size_t n) { p = (p + n <= end) ? p + n : end; }
};

struct ClientContext {
  long port = 0;
  AmsAddr server{};
  bool connected = false;
  bool discovered = false;
  std::string lastError;

  std::vector<Leaf> leaves;
  std::unordered_map<std::string, size_t> leafByPath;  // path -> index in leaves
  std::unordered_set<std::string> excluded;            // on-demand paths

  ~ClientContext() { closePort(); }

  // Explicitly release every held value handle in ONE round trip via the
  // sum-write to SYM_RELEASEHND. Best-effort (errors ignored): the port is about
  // to close regardless. Closing the AMS port reclaims handles on a LOCAL
  // runtime, but a ROUTED/REMOTE target does not always reclaim on port close —
  // so without this explicit release, every reconnect/disconnect leaks the whole
  // handle set on the remote PLC and exhausts its symbol-server pool
  // (CAdsWatchServerR0 "no more handles") within a few sessions.
  void releaseHandles() {
    if (!port) return;
    uint32_t n = 0;
    for (const auto& lf : leaves) if (lf.handle) ++n;
    if (n == 0) return;
    // Sum-write request: n x {iGroup=SYM_RELEASEHND, iOffs=0, size=4} header,
    // then the 4-byte handle values concatenated.
    std::vector<uint8_t> req(static_cast<size_t>(n) * 12 + static_cast<size_t>(n) * 4);
    const uint32_t ig = kSymReleaseHnd, io = 0, sz = 4;
    size_t h = 0, d = static_cast<size_t>(n) * 12;
    for (const auto& lf : leaves) {
      if (!lf.handle) continue;
      std::memcpy(&req[h + 0], &ig, 4);
      std::memcpy(&req[h + 4], &io, 4);
      std::memcpy(&req[h + 8], &sz, 4);
      h += 12;
      std::memcpy(&req[d], &lf.handle, 4);
      d += 4;
    }
    // Best-effort: ignore the reply/error codes. The port closes next regardless.
    AdsSyncWriteReqEx(port, &server, kSumWrite, n,
                      static_cast<uint32_t>(req.size()), req.data());
  }

  // Close the AMS port, which releases EVERY value handle opened on it in one
  // operation (TwinCAT reclaims a port's handles on close). This is the bulk
  // release for reconnect/disconnect/destroy — far cheaper than ~2670 synchronous
  // SYM_RELEASEHND round trips (tens of seconds). After close, handle numbers are
  // stale, so forget them.
  void closePort() {
    if (port) {
      releaseHandles();   // explicit batch release (reliable for remote targets)
      AdsPortCloseEx(port);
      port = 0;
    }
    for (auto& lf : leaves) lf.handle = 0;
  }
};

// Read `arrayDim` AdsDatatypeArrayInfo structs ({lBound, elements}) into `out`.
void readArrays(Reader& r, uint16_t arrayDim, std::vector<ArrayDim>& out) {
  for (uint16_t i = 0; i < arrayDim && r.ok; ++i) {
    ArrayDim a;
    a.lBound = r.u32();
    a.elements = r.u32();
    out.push_back(a);
  }
}

// Parse a datatype sub-entry (a Member). Returns the total bytes consumed via
// the entry's own entryLength; fills `m`. Layout mirrors AdsDatatypeEntry.
bool parseMember(Reader& r, Member& m) {
  const uint8_t* start = r.p;
  uint32_t entryLength = r.u32();
  r.u32();  // version
  r.u32();  // hashValue
  r.u32();  // typeHashValue
  uint32_t size = r.u32();
  uint32_t offs = r.u32();
  uint32_t adsType = r.u32();
  r.u32();  // flags
  uint16_t nameLen = r.u16();
  uint16_t typeLen = r.u16();
  uint16_t commentLen = r.u16();
  uint16_t arrayDim = r.u16();
  uint16_t subItems = r.u16();
  std::string name = r.str(nameLen); r.skip(1);
  std::string typeName = r.str(typeLen); r.skip(1);
  r.skip(commentLen + 1);
  readArrays(r, arrayDim, m.arrays);  // array info follows the strings
  if (!r.ok) return false;
  m.name = name;
  m.typeName = typeName;
  m.offs = offs;
  m.adsType = adsType;
  m.size = size;
  m.subItems = subItems;
  // Advance to the entry end (skips any inline sub-entries we do not need,
  // because members resolve by typeName in the datatype map).
  r.p = start + entryLength;
  if (r.p > r.end) { r.ok = false; return false; }
  return true;
}

// Read the datatype table (0xF00E) into a name->DataType map.
bool uploadDatatypes(ClientContext& ctx, uint32_t nDt, uint32_t nDtSize,
                     std::unordered_map<std::string, DataType>& types) {
  std::vector<uint8_t> blob(nDtSize);
  unsigned long read = 0;
  long err = AdsSyncReadReqEx2(ctx.port, &ctx.server, kSymDtUpload, 0, nDtSize,
                               blob.data(), &read);
  if (err) {
    ctx.lastError = "DT upload failed: " + std::to_string(err);
    return false;
  }
  Reader r{blob.data(), blob.data() + read};
  for (uint32_t i = 0; i < nDt && r.ok && r.p < r.end; ++i) {
    const uint8_t* start = r.p;
    uint32_t entryLength = r.u32();
    r.u32();  // version
    r.u32();  // hashValue
    r.u32();  // typeHashValue
    uint32_t size = r.u32();
    r.u32();  // offs (0 at top level)
    uint32_t adsType = r.u32();
    r.u32();  // flags
    uint16_t nameLen = r.u16();
    uint16_t typeLen = r.u16();
    uint16_t commentLen = r.u16();
    uint16_t arrayDim = r.u16();
    uint16_t subItems = r.u16();
    std::string name = r.str(nameLen); r.skip(1);
    std::string typeName = r.str(typeLen); r.skip(1);
    r.skip(commentLen + 1);
    if (!r.ok) break;
    DataType dt;
    dt.name = name;
    dt.elementType = typeName;  // element/base type for array or alias datatypes
    dt.adsType = adsType;
    dt.size = size;
    // Array info precedes the sub-entries (AdsDatatypeEntry layout).
    readArrays(r, arrayDim, dt.arrays);
    // Sub-entries (members) follow inline for struct datatypes.
    for (uint16_t s = 0; s < subItems && r.ok; ++s) {
      Member m;
      if (!parseMember(r, m)) break;
      dt.members.push_back(std::move(m));
    }
    types[name] = std::move(dt);
    r.p = start + entryLength;
    if (r.p > r.end) break;
  }
  return true;
}

// Recursively expand a symbol/member into scalar leaves. `arrays` holds THIS
// node's array dimensions (empty for a scalar or struct).
//
// Array elements use the TF6100 OPC UA browse convention the snapshot mapper
// expects — the array node `Foo` contains children `Foo[i]`, i.e. a DOUBLE path
// segment `Foo/Foo[i]` — while the ADS symbol (used for handle-by-name) takes a
// single `[i]` suffix (`Foo[i]`). Getting these to match is what makes arrays
// (config manifest entries, SupportedModes, fieldbus Nodes/Channels, release
// Reasons) resolve over ADS exactly as they do over OPC UA.
void expand(ClientContext& ctx,
            const std::unordered_map<std::string, DataType>& types,
            const std::string& symbol, const std::string& path,
            const std::string& typeName, uint32_t adsType, uint32_t size,
            const std::vector<ArrayDim>& arrays, unsigned depth) {
  if (ctx.leaves.size() >= kMaxLeaves || depth > kMaxDepth) return;

  // Resolve the effective array dimensions: declared on this node (an array
  // member/symbol), or via a typedef'd array datatype ("ARRAY [..] OF T").
  std::vector<ArrayDim> dims = arrays;
  std::string elemType = typeName;
  uint32_t elemAdsType = adsType;
  if (dims.empty()) {
    auto it = types.find(typeName);
    if (it != types.end() && !it->second.arrays.empty()) {
      dims = it->second.arrays;
      elemType = it->second.elementType;
      elemAdsType = it->second.adsType;
    }
  }

  if (!dims.empty()) {
    const ArrayDim dim = dims.front();
    const std::vector<ArrayDim> rest(dims.begin() + 1, dims.end());
    const uint32_t elemSize = dim.elements ? size / dim.elements : size;
    const std::string seg = path.substr(path.rfind('/') + 1);
    for (uint32_t k = 0; k < dim.elements; ++k) {
      if (ctx.leaves.size() >= kMaxLeaves) return;
      const std::string ix = "[" + std::to_string(dim.lBound + k) + "]";
      expand(ctx, types, symbol + ix, path + "/" + seg + ix, elemType,
             elemAdsType, elemSize, rest, depth + 1);
    }
    return;
  }

  auto it = types.find(typeName);
  if (it != types.end() && !it->second.members.empty()) {
    for (const auto& m : it->second.members) {
      expand(ctx, types, symbol + "." + m.name, path + "/" + m.name,
             m.typeName, m.adsType, m.size, m.arrays, depth + 1);
    }
    return;
  }

  // Terminal: a scalar leaf (or an opaque struct with no decodable members —
  // skip those, they are not part of the browse contract the mapper reads).
  if (adsType == ADST_VOID) return;
  Leaf lf;
  lf.symbol = symbol;
  lf.path = path;
  lf.adsType = adsType;
  lf.size = size;
  ctx.leafByPath[path] = ctx.leaves.size();
  ctx.leaves.push_back(std::move(lf));
}

// Drop unused fixed-array fieldbus elements once the active counts are known.
void pruneFieldbus(ClientContext& ctx);

// Full discovery: symbol upload + datatype walk -> ctx.leaves.
bool discover(ClientContext& ctx) {
  // Reconnect closes+reopens the AMS port before clearing `discovered`, so the
  // port is fresh here and any prior handles were already released by that close
  // (see frk_ads_connect). Leaves are therefore empty on entry; just reset.
  ctx.leaves.clear();
  ctx.leafByPath.clear();

  uint32_t info[6] = {0};
  unsigned long read = 0;
  long err = AdsSyncReadReqEx2(ctx.port, &ctx.server, kSymUploadInfo2, 0,
                               sizeof(info), info, &read);
  if (err) {
    ctx.lastError = "SYM_UPLOADINFO2 failed: " + std::to_string(err);
    return false;
  }
  const uint32_t nSym = info[0];
  const uint32_t nSymSize = info[1];
  const uint32_t nDt = info[2];
  const uint32_t nDtSize = info[3];

  std::unordered_map<std::string, DataType> types;
  if (!uploadDatatypes(ctx, nDt, nDtSize, types)) return false;

  std::vector<uint8_t> symBlob(nSymSize);
  err = AdsSyncReadReqEx2(ctx.port, &ctx.server, kSymUpload, 0, nSymSize,
                          symBlob.data(), &read);
  if (err) {
    ctx.lastError = "SYM_UPLOAD failed: " + std::to_string(err);
    return false;
  }
  Reader r{symBlob.data(), symBlob.data() + read};
  for (uint32_t i = 0; i < nSym && r.ok && r.p < r.end; ++i) {
    const uint8_t* start = r.p;
    uint32_t entryLength = r.u32();
    r.u32();  // iGroup
    r.u32();  // iOffs
    uint32_t size = r.u32();
    uint32_t adsType = r.u32();
    r.u32();  // flags
    uint16_t nameLen = r.u16();
    uint16_t typeLen = r.u16();
    uint16_t commentLen = r.u16();
    std::string name = r.str(nameLen); r.skip(1);
    std::string typeName = r.str(typeLen); r.skip(1);
    r.skip(commentLen + 1);
    if (!r.ok) break;
    // Only Fraktal application symbols under MAIN or the fieldbus GVL matter;
    // the mapper ignores everything without a Status.Name, but expanding the
    // whole PLC is wasteful, so scope to MAIN.* and *Fieldbus* roots.
    if (name.rfind("MAIN.", 0) == 0 || name.find("Fieldbus") != std::string::npos) {
      std::string path = "PLC1/" + name;
      for (auto& c : path) if (c == '.') c = '/';
      expand(ctx, types, name, path, typeName, adsType, size, {}, 0);
    }
    r.p = start + entryLength;
    if (r.p > r.end) break;
  }
  pruneFieldbus(ctx);  // shrink fixed-size bus arrays to the active nodes/channels
  ctx.discovered = true;
  return true;
}

// Ensure a leaf has a value handle (SYM_HNDBYNAME).
bool ensureHandle(ClientContext& ctx, Leaf& lf) {
  if (lf.handle) return true;
  unsigned long read = 0;
  uint32_t handle = 0;
  long err = AdsSyncReadWriteReqEx2(
      ctx.port, &ctx.server, kSymHndByName, 0, sizeof(handle), &handle,
      static_cast<uint32_t>(lf.symbol.size()),
      const_cast<char*>(lf.symbol.c_str()), &read);
  if (err || read < sizeof(handle)) return false;
  lf.handle = handle;
  return true;
}

// Read a small integer leaf value now (used at discovery time); -1 on failure.
long long readIntLeaf(ClientContext& ctx, Leaf& lf) {
  if (!ensureHandle(ctx, lf)) return -1;
  uint8_t buf[8] = {0};
  unsigned long read = 0;
  uint32_t sz = lf.size ? lf.size : 4;
  if (sz > 8) sz = 8;
  if (AdsSyncReadReqEx2(ctx.port, &ctx.server, kSymValByHnd, lf.handle, sz, buf,
                        &read))
    return -1;
  long long v = 0;
  std::memcpy(&v, buf, read < sz ? read : sz);
  return v;
}

// The integer inside the first "[...]" following `marker` in `path`; -1 if none.
int indexAfter(const std::string& path, const std::string& marker) {
  size_t m = path.find(marker);
  if (m == std::string::npos) return -1;
  size_t lb = path.find('[', m);
  if (lb == std::string::npos || lb + 1 >= path.size()) return -1;
  int v = 0;
  size_t i = lb + 1;
  if (path[i] < '0' || path[i] > '9') return -1;
  for (; i < path.size() && path[i] >= '0' && path[i] <= '9'; ++i)
    v = v * 10 + (path[i] - '0');
  return v;
}

// The Fraktal fieldbus GVL sizes Nodes[]/Channels[] to a fixed MAX but only the
// first NodeCount / per-node ChannelCount are wired. TF6100 only browses the
// active ones; ADS SYM_UPLOAD exposes the whole array, so without this the
// on-demand fieldbus read would touch ~thousands of dead slots every refresh and
// stall the worker. Read the counts once and drop the inactive array elements.
// Unreadable counts -> keep everything (correct, just not pruned).
void pruneFieldbus(ClientContext& ctx) {
  std::string topo;  // e.g. "PLC1/GVL_PressFieldbus/Topology"
  for (auto& lf : ctx.leaves) {
    size_t p = lf.path.find("/Topology/");
    if (p != std::string::npos) { topo = lf.path.substr(0, p + 9); break; }
  }
  if (topo.empty()) return;
  const std::string nodesPrefix = topo + "/Nodes/Nodes[";
  const std::string chPrefix = "/Channels/Channels[";
  auto nc = ctx.leafByPath.find(topo + "/NodeCount");
  if (nc == ctx.leafByPath.end()) return;
  const long long nodeCount = readIntLeaf(ctx, ctx.leaves[nc->second]);
  if (nodeCount < 0) return;
  std::unordered_map<int, long long> chan;  // active node index -> channel count
  for (int i = 1; i <= nodeCount; ++i) {
    auto it = ctx.leafByPath.find(nodesPrefix + std::to_string(i) + "]/ChannelCount");
    if (it != ctx.leafByPath.end())
      chan[i] = readIntLeaf(ctx, ctx.leaves[it->second]);
  }
  std::vector<Leaf> kept;
  kept.reserve(ctx.leaves.size());
  for (auto& lf : ctx.leaves) {
    if (lf.path.find(nodesPrefix) != std::string::npos) {
      const int ni = indexAfter(lf.path, "/Nodes/Nodes[");
      bool drop = ni > nodeCount;
      if (!drop) {
        const int cj = indexAfter(lf.path, chPrefix);
        auto ci = chan.find(ni);
        const long long cc = ci != chan.end() ? ci->second : -1;
        if (cj >= 0 && cc >= 0 && cj > cc) drop = true;
      }
      if (drop) {
        // Release the server handle before discarding the leaf, or the pruned
        // fieldbus slots leak on the PLC symbol server.
        if (lf.handle) {
          long h = lf.handle;
          AdsSyncWriteReqEx(ctx.port, &ctx.server, kSymReleaseHnd, 0, sizeof(h), &h);
          lf.handle = 0;
        }
        continue;
      }
    }
    kept.push_back(std::move(lf));
  }
  ctx.leaves.swap(kept);
  ctx.leafByPath.clear();
  for (size_t i = 0; i < ctx.leaves.size(); ++i)
    ctx.leafByPath[ctx.leaves[i].path] = i;
}

// Encode one leaf's raw bytes into JSON per its ADS scalar type; "" if
// undecodable. Shared by the per-symbol (readLeaf) and sum-read paths.
std::string encodeScalar(uint32_t adsType, const uint8_t* d, size_t len) {
  auto rdI = [&](int bytes, bool sign) -> long long {
    long long v = 0;
    std::memcpy(&v, d, bytes);
    if (sign) { const int sh = (8 - bytes) * 8; v = (v << sh) >> sh; }
    return v;
  };
  switch (adsType) {
    case ADST_BIT: return d[0] ? "true" : "false";
    case ADST_UINT8: return std::to_string((unsigned)d[0]);
    case ADST_INT8: return std::to_string((int)(int8_t)d[0]);
    case ADST_INT16: return std::to_string((short)rdI(2, true));
    case ADST_UINT16: return std::to_string((unsigned short)rdI(2, false));
    case ADST_INT32: return std::to_string((int)rdI(4, true));
    case ADST_UINT32: return std::to_string((unsigned)rdI(4, false));
    case ADST_INT64: return std::to_string((long long)rdI(8, true));
    case ADST_UINT64: { unsigned long long v; std::memcpy(&v, d, 8); return std::to_string(v); }
    case ADST_REAL32: { float f; std::memcpy(&f, d, 4); return std::to_string(f); }
    case ADST_REAL64: { double f; std::memcpy(&f, d, 8); return std::to_string(f); }
    case ADST_STRING: {
      size_t n = 0; while (n < len && d[n] != 0) ++n;
      return "\"" + jsonEscape(std::string((const char*)d, n)) + "\"";
    }
    default: return {};
  }
}

// Read one leaf's value; append `"path":<json>` to out. Returns false only on a
// transport-level failure (a per-symbol error is skipped, not fatal).
bool readLeaf(ClientContext& ctx, Leaf& lf, std::ostringstream& out,
              bool& first) {
  if (!ensureHandle(ctx, lf)) return true;  // skip unresolved
  std::vector<uint8_t> buf(lf.size > 0 ? lf.size : 4);
  unsigned long read = 0;
  long err = AdsSyncReadReqEx2(ctx.port, &ctx.server, kSymValByHnd, lf.handle,
                               static_cast<uint32_t>(buf.size()), buf.data(),
                               &read);
  if (err) {
    lf.handle = 0;  // stale handle (online change) -> re-resolve next time
    return true;
  }
  std::string encoded = encodeScalar(lf.adsType, buf.data(), read);
  if (encoded.empty()) return true;  // undecodable -> skip
  if (!first) out << ',';
  first = false;
  out << '"' << jsonEscape(lf.path) << "\":" << encoded;
  return true;
}

// Sum-read the given leaves in ONE ADS round trip, appending "path":value pairs.
// Falls back to false if the sum service is unavailable (caller then per-reads).
bool sumRead(ClientContext& ctx, const std::vector<Leaf*>& leaves,
             std::ostringstream& out, bool& first) {
  if (leaves.empty()) return true;
  const uint32_t n = static_cast<uint32_t>(leaves.size());
  // Request: n x {iGroup, iOffs=handle, length}
  std::vector<uint8_t> req(n * 12);
  uint32_t totalData = 0;
  for (uint32_t i = 0; i < n; ++i) {
    uint32_t ig = kSymValByHnd, io = leaves[i]->handle,
             ln = leaves[i]->size ? leaves[i]->size : 4;
    std::memcpy(&req[i * 12 + 0], &ig, 4);
    std::memcpy(&req[i * 12 + 4], &io, 4);
    std::memcpy(&req[i * 12 + 8], &ln, 4);
    totalData += ln;
  }
  std::vector<uint8_t> resp(n * 4 + totalData);
  unsigned long read = 0;
  long err = AdsSyncReadWriteReqEx2(ctx.port, &ctx.server, kSumRead, n,
                                    static_cast<uint32_t>(resp.size()), resp.data(),
                                    static_cast<uint32_t>(req.size()), req.data(),
                                    &read);
  if (err) return false;  // service unsupported / failed -> caller per-reads
  const uint8_t* codes = resp.data();
  const uint8_t* data = resp.data() + n * 4;
  size_t off = 0;
  for (uint32_t i = 0; i < n; ++i) {
    uint32_t code;
    std::memcpy(&code, codes + i * 4, 4);
    const uint32_t ln = leaves[i]->size ? leaves[i]->size : 4;
    if (code == 0) {
      std::string enc = encodeScalar(leaves[i]->adsType, data + off, ln);
      if (!enc.empty()) {
        if (!first) out << ',';
        first = false;
        out << '"' << jsonEscape(leaves[i]->path) << "\":" << enc;
      }
    } else {
      leaves[i]->handle = 0;  // stale -> re-resolve next discovery
    }
    off += ln;
  }
  return true;
}

// Resolve value handles for every leaf that lacks one in ONE round trip, via the
// sum ReadWrite of SYM_HNDBYNAME (0xF082). Without this, a large on-demand read
// (e.g. the whole fieldbus topology) would issue one SYM_HNDBYNAME per leaf —
// thousands of sequential round trips that stall the worker for tens of seconds.
// On any failure the leaf keeps handle 0 and the per-symbol ensureHandle() path
// still resolves it, so this is a pure fast-path.
void batchEnsureHandles(ClientContext& ctx, const std::vector<Leaf*>& leaves) {
  std::vector<Leaf*> todo;
  for (auto* lf : leaves) if (!lf->handle) todo.push_back(lf);
  if (todo.empty()) return;
  // Resolve in CHUNKS under a wall-clock budget. One giant ~2670-entry sum-call
  // is uninterruptible: on a slow/remote PLC (or while its symbol pool grows)
  // it can run well past the caller's bound, so the Dart side kills the worker
  // isolate — and a killed isolate never runs its native teardown, leaking the
  // whole handle set + AMS port. Chunking keeps each native call short and the
  // budget makes the function return promptly (partial is fine; a healthy PLC
  // resolves all handles well under the budget), so the isolate stays
  // responsive and closePort()/releaseHandles() can run on failure.
  constexpr uint32_t kChunk = 200;
  constexpr auto kBudget = std::chrono::milliseconds(5000);
  const auto start = std::chrono::steady_clock::now();
  auto push32 = [](std::vector<uint8_t>& b, uint32_t v) {
    const uint8_t* p = reinterpret_cast<const uint8_t*>(&v);
    b.insert(b.end(), p, p + 4);
  };
  for (size_t base = 0; base < todo.size(); base += kChunk) {
    if (std::chrono::steady_clock::now() - start > kBudget) return;  // budget hit
    const uint32_t n = static_cast<uint32_t>(
        std::min<size_t>(kChunk, todo.size() - base));
    // Write: n x {iGroup=SYM_HNDBYNAME, iOffs=0, readLen=4, writeLen=nameLen},
    // then the names concatenated. Reply: n x {errorCode, readLength} + handles.
    std::vector<uint8_t> wbuf;
    for (uint32_t i = 0; i < n; ++i) {
      Leaf* lf = todo[base + i];
      push32(wbuf, kSymHndByName);
      push32(wbuf, 0);
      push32(wbuf, 4);
      push32(wbuf, static_cast<uint32_t>(lf->symbol.size()));
    }
    for (uint32_t i = 0; i < n; ++i) {
      Leaf* lf = todo[base + i];
      wbuf.insert(wbuf.end(), lf->symbol.begin(), lf->symbol.end());
    }
    std::vector<uint8_t> rbuf(static_cast<size_t>(n) * 8 + static_cast<size_t>(n) * 4);
    unsigned long read = 0;
    long err = AdsSyncReadWriteReqEx2(ctx.port, &ctx.server, kSumHndByName, n,
                                      static_cast<uint32_t>(rbuf.size()), rbuf.data(),
                                      static_cast<uint32_t>(wbuf.size()), wbuf.data(),
                                      &read);
    if (err) return;  // service unsupported -> per-symbol fallback keeps handle 0
    const uint8_t* hdr = rbuf.data();
    const uint8_t* data = rbuf.data() + static_cast<size_t>(n) * 8;
    size_t off = 0;
    for (uint32_t i = 0; i < n; ++i) {
      uint32_t code = 0, len = 0;
      std::memcpy(&code, hdr + i * 8, 4);
      std::memcpy(&len, hdr + i * 8 + 4, 4);
      if (code == 0 && len >= 4) {
        uint32_t h = 0;
        std::memcpy(&h, data + off, 4);
        todo[base + i]->handle = h;
      }
      off += len;
    }
  }
}

char* dup(const std::string& s) {
  char* r = static_cast<char*>(std::malloc(s.size() + 1));
  if (r) std::memcpy(r, s.c_str(), s.size() + 1);
  return r;
}

}  // namespace

extern "C" {

FrkAdsHandle frk_ads_create(void) { return new ClientContext(); }

void frk_ads_destroy(FrkAdsHandle handle) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx) return;
  ctx->closePort();  // bulk-releases the port's value handles
  delete ctx;
}

int32_t frk_ads_connect(FrkAdsHandle handle, const char* ams_net_id,
                        uint16_t ams_port) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx) return 0;
  ctx->lastError.clear();
  // The Dart worker reuses one ClientContext across reconnects and re-issues
  // `connect` on the SAME context. Closing the old AMS port releases every value
  // handle opened on it in one operation, so we must close it BEFORE opening a
  // new one — otherwise every reconnect leaks the port AND orphans the whole
  // prior handle set on the PLC symbol server (CAdsWatchServerR0 "no more
  // handles"). Closing the port is the bulk release; per-handle SYM_RELEASEHND
  // here would be ~2670 synchronous round trips (tens of seconds) for nothing.
  if (ctx->port) {
    AdsPortCloseEx(ctx->port);
    ctx->port = 0;
  }
  ctx->leaves.clear();
  ctx->leafByPath.clear();
  ctx->discovered = false;
  ctx->port = AdsPortOpenEx();
  if (!ctx->port) { ctx->lastError = "AdsPortOpenEx failed"; return 0; }
  // Parse "a.b.c.d.e.f".
  unsigned vals[6] = {0};
  if (std::sscanf(ams_net_id, "%u.%u.%u.%u.%u.%u", &vals[0], &vals[1], &vals[2],
                  &vals[3], &vals[4], &vals[5]) != 6) {
    ctx->lastError = std::string("bad AmsNetId: ") + ams_net_id;
    AdsPortCloseEx(ctx->port);
    ctx->port = 0;
    return 0;
  }
  for (int i = 0; i < 6; ++i) ctx->server.netId.b[i] = (uint8_t)vals[i];
  ctx->server.port = ams_port;
  // Bound every subsequent ADS round trip. This shortens (though does not always
  // fully cap) a hang to an unreachable/black-holed target; the Dart client also
  // bounds each call and kills the isolate on timeout, which is the reliable
  // guard. We deliberately do NOT probe with ReadState here: a PLC runtime port
  // (851/854) does not answer ReadState (returns ADSERR_TARGETPORTNOTFOUND) even
  // when it is perfectly reachable, so a probe would false-negative live PLCs.
  AdsSyncSetTimeoutEx(ctx->port, kAdsTimeoutMs);
  ctx->connected = true;
  ctx->discovered = false;
  return 1;
}

void frk_ads_disconnect(FrkAdsHandle handle) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx) return;
  ctx->closePort();  // bulk-releases the port's value handles
  ctx->connected = false;
  ctx->discovered = false;
}

int32_t frk_ads_is_connected(FrkAdsHandle handle) {
  auto* ctx = static_cast<ClientContext*>(handle);
  return (ctx && ctx->connected) ? 1 : 0;
}

const char* frk_ads_last_error(FrkAdsHandle handle) {
  auto* ctx = static_cast<ClientContext*>(handle);
  return ctx ? ctx->lastError.c_str() : "";
}

char* frk_ads_snapshot_json(FrkAdsHandle handle) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx || !ctx->connected) return nullptr;
  ctx->lastError.clear();
  if (!ctx->discovered && !discover(*ctx)) return nullptr;

  std::ostringstream values;
  std::ostringstream paths;
  bool firstV = true, firstP = true;
  // Build the path list (all leaves) and the fast set (non-excluded, handle-
  // resolved). Ensure handles first so the sum-read has valid offsets.
  std::vector<Leaf*> fast;
  for (auto& lf : ctx->leaves) {
    if (!firstP) paths << ',';
    firstP = false;
    paths << '"' << jsonEscape(lf.path) << '"';
    if (ctx->excluded.count(lf.path)) continue;  // on-demand: not cyclic
    fast.push_back(&lf);
  }
  // Resolve all handles in one round trip (per-symbol fallback for stragglers),
  // then keep only the resolved leaves for the sum-read.
  batchEnsureHandles(*ctx, fast);
  std::vector<Leaf*> ready;
  ready.reserve(fast.size());
  for (auto* lf : fast)
    if (lf->handle || ensureHandle(*ctx, *lf)) ready.push_back(lf);
  fast.swap(ready);
  // One round trip for the whole fast set; per-symbol fallback if unsupported.
  if (!sumRead(*ctx, fast, values, firstV)) {
    firstV = true;
    values.str("");
    for (auto* lf : fast) readLeaf(*ctx, *lf, values, firstV);
  }
  std::ostringstream doc;
  doc << "{\"protocol\":\"fraktal.opcua.snapshot.v1\",\"nodeCount\":"
      << ctx->leaves.size()
      << ",\"truncated\":" << (ctx->leaves.size() >= kMaxLeaves ? "true" : "false")
      << ",\"rootChildren\":[\"4:PLC1(Object)\"]"
      << ",\"namespaces\":[\"http://opcfoundation.org/UA/\",\"urn:BeckhoffAutomation:Ua:PLC1\"]"
      << ",\"paths\":[" << paths.str() << "]"
      << ",\"values\":{" << values.str() << "}}";
  return dup(doc.str());
}

char* frk_ads_read_values_json(FrkAdsHandle handle, const char* paths) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx || !ctx->connected) return nullptr;
  if (!ctx->discovered && !discover(*ctx)) return nullptr;
  std::ostringstream values;
  bool first = true;
  if (paths) {
    // Collect the requested leaves, then resolve handles + read values in bulk.
    // A large scope (e.g. the fieldbus topology, ~thousands of leaves) is served
    // in ~2 round trips instead of one-per-leaf, so activating the fieldbus page
    // no longer stalls the worker.
    std::vector<Leaf*> want;
    std::string blob(paths);
    size_t start = 0;
    while (start <= blob.size()) {
      size_t nl = blob.find('\n', start);
      std::string path = blob.substr(start, nl == std::string::npos ? std::string::npos : nl - start);
      if (!path.empty()) {
        auto it = ctx->leafByPath.find(path);
        if (it != ctx->leafByPath.end()) want.push_back(&ctx->leaves[it->second]);
      }
      if (nl == std::string::npos) break;
      start = nl + 1;
    }
    batchEnsureHandles(*ctx, want);
    std::vector<Leaf*> ready;
    ready.reserve(want.size());
    for (auto* lf : want)
      if (lf->handle || ensureHandle(*ctx, *lf)) ready.push_back(lf);
    if (!sumRead(*ctx, ready, values, first)) {
      first = true;
      values.str("");
      for (auto* lf : ready) readLeaf(*ctx, *lf, values, first);
    }
  }
  std::ostringstream doc;
  doc << "{\"values\":{" << values.str() << "}}";
  return dup(doc.str());
}

int32_t frk_ads_set_excluded_paths(FrkAdsHandle handle, const char* paths) {
  auto* ctx = static_cast<ClientContext*>(handle);
  if (!ctx) return 0;
  ctx->excluded.clear();
  if (paths) {
    std::string blob(paths);
    size_t start = 0;
    while (start <= blob.size()) {
      size_t nl = blob.find('\n', start);
      std::string path = blob.substr(start, nl == std::string::npos ? std::string::npos : nl - start);
      if (!path.empty()) ctx->excluded.insert(path);
      if (nl == std::string::npos) break;
      start = nl + 1;
    }
  }
  return 1;
}

// --- writes: resolve the leaf handle by path and write by handle ---
namespace {
int32_t writeByPath(ClientContext* ctx, const char* path, const void* data,
                    uint32_t len) {
  if (!ctx || !ctx->connected || !path) return 0;
  auto it = ctx->leafByPath.find(path);
  if (it == ctx->leafByPath.end()) {
    ctx->lastError = std::string("unknown path: ") + path;
    return 0;
  }
  Leaf& lf = ctx->leaves[it->second];
  if (!ensureHandle(*ctx, lf)) return 0;
  long err = AdsSyncWriteReqEx(ctx->port, &ctx->server, kSymValByHnd, lf.handle,
                               len, const_cast<void*>(data));
  if (err) { ctx->lastError = "write failed: " + std::to_string(err); return 0; }
  return 1;
}
}  // namespace

int32_t frk_ads_write_bool(FrkAdsHandle h, const char* p, int32_t v) {
  uint8_t b = v ? 1 : 0;
  return writeByPath(static_cast<ClientContext*>(h), p, &b, 1);
}
int32_t frk_ads_write_int32(FrkAdsHandle h, const char* p, int32_t v) {
  return writeByPath(static_cast<ClientContext*>(h), p, &v, 4);
}
int32_t frk_ads_write_uint32(FrkAdsHandle h, const char* p, uint32_t v) {
  return writeByPath(static_cast<ClientContext*>(h), p, &v, 4);
}
int32_t frk_ads_write_int64(FrkAdsHandle h, const char* p, int64_t v) {
  return writeByPath(static_cast<ClientContext*>(h), p, &v, 8);
}
int32_t frk_ads_write_double(FrkAdsHandle h, const char* p, double v) {
  return writeByPath(static_cast<ClientContext*>(h), p, &v, 8);
}
int32_t frk_ads_write_string(FrkAdsHandle h, const char* p, const char* v) {
  const char* s = v ? v : "";
  return writeByPath(static_cast<ClientContext*>(h), p, s,
                     static_cast<uint32_t>(std::strlen(s) + 1));
}

void frk_ads_free_string(char* value) { std::free(value); }

}  // extern "C"
