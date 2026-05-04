package com.hermes.mocklocation

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import java.time.Instant

class MockLocationReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.e(LOG_TAG, "MockLocationReceiver onReceive entered: action=" + intent.action)
        if (intent.action != ACTION_SET_MOCK_LOCATION) {
            Log.e(LOG_TAG, "Ignoring unsupported action: ${intent.action}")
            return
        }

        Log.e(
            LOG_TAG,
            "MockLocationReceiver raw extras before parse: lat=${intent.extras?.get("lat")} " +
                "lon=${intent.extras?.get("lon")} accuracy=${intent.extras?.get("accuracy")}",
        )
        val lat = readDoubleExtra(intent, "lat")
        val lon = readDoubleExtra(intent, "lon")
        val accuracy = readFloatExtra(intent, "accuracy") ?: 10f
        Log.e(
            LOG_TAG,
            "MockLocationReceiver parsed extras: lat=$lat lon=$lon accuracy=$accuracy",
        )

        if (lat == null || lon == null) {
            val message = "Missing lat/lon extras; ignoring mock location broadcast."
            Log.e(LOG_TAG, message)
            saveStatus(context, message, null, null, null)
            return
        }

        if (!isValidLocation(lat, lon, accuracy)) {
            val message = "Invalid location lat=$lat lon=$lon accuracy=$accuracy; ignoring broadcast."
            Log.e(LOG_TAG, message)
            saveStatus(context, message, lat, lon, accuracy)
            return
        }

        val result = MockLocationController(context).setMockLocation(lat, lon, accuracy)
        saveStatus(context, result.message, lat, lon, accuracy)
        if (result.ok) {
            Log.e(LOG_TAG, result.message)
        } else {
            Log.e(LOG_TAG, result.message, result.error)
        }
    }

    private fun readDoubleExtra(intent: Intent, name: String): Double? {
        if (!intent.hasExtra(name)) return null
        return when (val value = intent.extras?.get(name)) {
            is Double -> value
            is Float -> value.toDouble()
            is Number -> value.toDouble()
            is String -> value.toDoubleOrNull()
            else -> null
        }
    }

    private fun readFloatExtra(intent: Intent, name: String): Float? {
        if (!intent.hasExtra(name)) return null
        return when (val value = intent.extras?.get(name)) {
            is Float -> value
            is Double -> value.toFloat()
            is Number -> value.toFloat()
            is String -> value.toFloatOrNull()
            else -> null
        }
    }

    private fun isValidLocation(lat: Double, lon: Double, accuracy: Float): Boolean {
        return lat in -90.0..90.0 && lon in -180.0..180.0 && accuracy > 0f
    }

    private fun saveStatus(
        context: Context,
        message: String,
        lat: Double?,
        lon: Double?,
        accuracy: Float?,
    ) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_STATUS, message)
            .putString(KEY_LAT, lat?.toString() ?: "-")
            .putString(KEY_LON, lon?.toString() ?: "-")
            .putString(KEY_ACCURACY, accuracy?.toString() ?: "-")
            .putString(KEY_UPDATED_AT, Instant.now().toString())
            .apply()
    }
}
