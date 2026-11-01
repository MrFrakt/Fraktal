library;

/// Shared desktop/gateway endpoint validation. Gateways require the serial pin.
final class CipEndpoint {
  final String host;
  final int port, slot;
  final String? serial;
  CipEndpoint._(this.host, this.port, this.slot, this.serial);

  factory CipEndpoint.parse(String text, {bool requireSerial = false}) {
    final uri = Uri.parse(text);
    // Uri normalizes an explicit port zero away for schemes with no default.
    // Inspect the supplied authority before that information is lost.
    final authority =
        text.split('://').skip(1).join('://').split(RegExp(r'[/?#]')).first;
    final explicit = RegExp(r':([0-9]*)$').firstMatch(authority);
    if (explicit != null && (int.tryParse(explicit[1]!) ?? 0) == 0)
      throw const FormatException('Invalid CIP port.');
    if (uri.scheme != 'cip' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.fragment.isNotEmpty ||
        uri.path.isNotEmpty && uri.path != '/' ||
        uri.queryParametersAll.entries.any((e) =>
            !const {'slot', 'serial'}.contains(e.key) || e.value.length != 1))
      throw const FormatException('Invalid CIP endpoint.');
    final slot = int.tryParse(uri.queryParameters['slot'] ?? '0');
    final port = uri.hasPort ? uri.port : 44818;
    final serial = uri.queryParameters['serial'];
    if (slot == null ||
        slot < 0 ||
        slot > 255 ||
        port < 1 ||
        port > 65535 ||
        requireSerial && serial == null ||
        serial != null && !RegExp(r'^[0-9A-Fa-f]{8}$').hasMatch(serial))
      throw const FormatException('Invalid CIP slot, port or serial pin.');
    return CipEndpoint._(uri.host, port, slot, serial);
  }
}
