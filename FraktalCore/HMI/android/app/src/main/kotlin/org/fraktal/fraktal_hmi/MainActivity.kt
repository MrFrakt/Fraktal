package org.fraktal.fraktal_hmi

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        SecureStore.register(flutterEngine.dartExecutor.binaryMessenger, applicationContext)
    }
}
