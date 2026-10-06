library;

/// HMI presentation choices only. No PLC values, permissions or command state
/// are retained here when the connection owner withdraws the operator shell.
class ModuleViewState {
  String? selectedTabId;
  final _hiddenByView = <String, Object>{};

  /// One typed selection per chart/history view, shared across its remounts.
  Set<T> hiddenFor<T>(String view) =>
      _hiddenByView.putIfAbsent(view, () => <T>{}) as Set<T>;
}
