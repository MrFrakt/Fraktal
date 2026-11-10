package org.fraktal.fraktal_hmi

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * The HMI's `fraktal/secure_store` channel (lib/data/s7web_vault_io.dart):
 * small secrets such as remembered CPU web logins, sealed with AES-256-GCM
 * under a key that lives in the Android Keystore and never leaves it. The
 * ciphertext sits in this app's private preferences; a restored backup
 * carries no key, so its entries no longer open and are dropped, and the HMI
 * asks for the login again.
 */
class SecureStore(context: Context) {
    private val preferences =
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    fun read(key: String): String? {
        val stored = preferences.getString(key, null) ?: return null
        return try {
            val parts = stored.split(':')
            val iv = Base64.decode(parts[0], Base64.NO_WRAP)
            val sealed = Base64.decode(parts[1], Base64.NO_WRAP)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv))
            cipher.updateAAD(key.toByteArray(Charsets.UTF_8))
            String(cipher.doFinal(sealed), Charsets.UTF_8)
        } catch (error: Exception) {
            delete(key)
            null
        }
    }

    fun write(key: String, value: String) {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        // The entry name is authenticated, so a value moved to another entry
        // does not open there.
        cipher.updateAAD(key.toByteArray(Charsets.UTF_8))
        val sealed = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        val stored = Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(sealed, Base64.NO_WRAP)
        check(preferences.edit().putString(key, stored).commit()) { "write failed" }
    }

    fun delete(key: String) {
        preferences.edit().remove(key).commit()
    }

    private fun key(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.let {
            return it.secretKey
        }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    companion object {
        private const val CHANNEL = "fraktal/secure_store"
        private const val KEYSTORE = "AndroidKeyStore"
        private const val ALIAS = "fraktal_secure_store"
        private const val PREFERENCES = "fraktal_secure_store"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val TAG_BITS = 128

        /** Entry names the HMI uses; anything else is refused. */
        private val KEY_NAME = Regex("^[a-z0-9_]{1,64}$")

        fun register(messenger: BinaryMessenger, context: Context) {
            val store = SecureStore(context)
            MethodChannel(messenger, CHANNEL).setMethodCallHandler { call, result ->
                val key = call.argument<String>("key")
                if (key == null || !KEY_NAME.matches(key)) {
                    result.error("bad-key", "Unknown secure store entry", null)
                    return@setMethodCallHandler
                }
                try {
                    when (call.method) {
                        "read" -> result.success(store.read(key))
                        "write" -> {
                            val value = call.argument<String>("value")
                            if (value == null) {
                                result.error("bad-value", "No value", null)
                            } else {
                                store.write(key, value)
                                result.success(null)
                            }
                        }
                        "delete" -> {
                            store.delete(key)
                            result.success(null)
                        }
                        else -> result.notImplemented()
                    }
                } catch (error: Exception) {
                    // The class name only: an exception message could carry data.
                    result.error("store-failed", error.javaClass.simpleName, null)
                }
            }
        }
    }
}
