import 'dart:io';
void main() {
  const enabled = bool.fromEnvironment('fraktal.cip.trace');
  print('fraktal.cip.trace=$enabled');
  if (!enabled) exitCode=1;
}
