library;

/// Optional deployment freshness envelope. Missing preserves older transports;
/// a present unknown/malformed envelope fails closed.
class OpcUaFreshnessBudget {
  final Duration pollPeriod, fastGood, fastExpiry, slowPeriod, slowGood, slowExpiry;

  const OpcUaFreshnessBudget._(this.pollPeriod, this.fastGood, this.fastExpiry,
      this.slowPeriod, this.slowGood, this.slowExpiry);

  static OpcUaFreshnessBudget? parse(Map<String, Object?> document) {
    if (!document.containsKey('freshnessBudget')) return null;
    final raw = document['freshnessBudget'];
    if (raw is! Map ||
        raw['schemaVersion'] is! int ||
        raw['schemaVersion'] != 1) {
      throw const FormatException('Unsupported freshness budget.');
    }
    Duration duration(String key) {
      final value = raw[key];
      if (value is! int || value <= 0 || value > 60000) {
        throw FormatException('Invalid freshness budget: $key.');
      }
      return Duration(milliseconds: value);
    }

    final poll = duration('pollPeriodMs');
    final good = duration('fastGoodMs'), expiry = duration('fastExpiryMs');
    final slow = duration('slowPeriodMs');
    final slowGood = duration('slowGoodMs'),
        slowExpiry = duration('slowExpiryMs');
    if (!(poll < good &&
        good < expiry &&
        slow < slowGood &&
        slowGood < slowExpiry)) {
      throw const FormatException('Invalid freshness budget ordering.');
    }
    return OpcUaFreshnessBudget._(poll, good, expiry, slow, slowGood, slowExpiry);
  }

  static Duration age(Object? value) {
    if (value is! num || !value.isFinite || value < 0) {
      throw const FormatException('Missing or invalid monotonic sample age.');
    }
    return Duration(microseconds: (value * 1000).ceil());
  }

  /// Source ages are measured after the gateway's wait/acquisition. Its optional
  /// processing bracket removes that already-accounted time from the RPC's
  /// conservative transit allowance. A millisecond covers clock resolution;
  /// malformed or implausible brackets fail closed. Legacy replies keep the
  /// full RPC allowance.
  Duration transitAllowance(Map<String, Object?> document, Duration rpcElapsed) {
    if (!document.containsKey('responseProcessingMs')) return rpcElapsed;
    final processed = age(document['responseProcessingMs']);
    final upperBound = rpcElapsed + const Duration(milliseconds: 1);
    if (processed > upperBound) {
      throw const FormatException('Gateway processing exceeds the RPC duration.');
    }
    return upperBound - processed;
  }

  Map<String, Object?> ageDocument(
      Map<String, Object?> document, Duration localAge) {
    final raw = document['values'];
    final metadata = document['dataValues'];
    if (raw is! Map || metadata is! Map) {
      throw const FormatException('Freshness requires DataValue metadata.');
    }
    final values = <String, Object?>{};
    final dataValues = <String, Object?>{};
    for (final path in {...metadata.keys, ...raw.keys}) {
      final source = metadata[path];
      final sampleAge = source is Map ? source['ageMs'] : null;
      if (source is! Map ||
          source['status'] is! int ||
          (source['status'] as int) < 0 ||
          (source['status'] as int) > 0xffffffff ||
          (source['tier'] != 'fast' && source['tier'] != 'slow') ||
          sampleAge is! num ||
          !sampleAge.isFinite ||
          sampleAge < 0) {
        dataValues['$path'] = {
          if (source is Map)
            for (final item in source.entries) '${item.key}': item.value,
          'status': 0x80000000,
          'qualityReason': 'read-metadata-invalid',
        };
        continue;
      }
      final elapsed = age(source['ageMs']) + localAge;
      final slow = source['tier'] == 'slow';
      final good = slow ? slowGood : fastGood,
          expiry = slow ? slowExpiry : fastExpiry;
      final severity = elapsed >= expiry
          ? 0x80000000
          : elapsed >= good
              ? 0x40000000
              : 0;
      final value = <String, Object?>{
        for (final item in source.entries) '${item.key}': item.value
      };
      if (severity > ((source['status'] as int) & 0xc0000000)) {
        value['status'] = severity;
        value['qualityReason'] =
            elapsed >= expiry ? 'read-expired' : 'read-late';
      }
      value['ageMs'] = elapsed.inMicroseconds / 1000;
      dataValues['$path'] = value;
      if (((value['status'] as int) & 0xc0000000) == 0 &&
          raw.containsKey(path)) {
        values['$path'] = raw[path];
      }
    }
    return {...document, 'values': values, 'dataValues': dataValues};
  }
}
