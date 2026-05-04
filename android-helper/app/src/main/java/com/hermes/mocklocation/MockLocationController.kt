package com.hermes.mocklocation

import android.Manifest
import android.app.AppOpsManager
import android.content.Context
import android.content.pm.PackageManager
import android.location.Criteria
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.util.Log

data class MockLocationResult(
    val ok: Boolean,
    val message: String,
    val error: Throwable? = null,
)

class MockLocationController(private val context: Context) {
    private val locationManager =
        context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

    fun setMockLocation(lat: Double, lon: Double, accuracy: Float): MockLocationResult {
        Log.e(LOG_TAG, "MockLocationController setMockLocation entered: lat=$lat lon=$lon accuracy=$accuracy")
        if (!isSelectedAsMockLocationApp()) {
            Log.e(LOG_TAG, "Hermes Mock Location Helper is not selected as the mock location app.")
            return MockLocationResult(
                ok = false,
                message = "Hermes Mock Location Helper is not selected as the mock location app. Select it in Developer options.",
            )
        }

        val providers = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
        var successCount = 0
        var lastError: Throwable? = null

        for (provider in providers) {
            try {
                ensureTestProvider(provider)
                locationManager.setTestProviderEnabled(provider, true)
                locationManager.setTestProviderLocation(provider, buildLocation(provider, lat, lon, accuracy))
                successCount += 1
                Log.e(LOG_TAG, "Set mock location for provider=$provider lat=$lat lon=$lon accuracy=$accuracy")
            } catch (security: SecurityException) {
                lastError = security
                Log.e(LOG_TAG, "Mock location permission denied for provider=$provider", security)
            } catch (error: IllegalArgumentException) {
                lastError = error
                Log.e(LOG_TAG, "Provider unavailable for provider=$provider", error)
            } catch (error: RuntimeException) {
                lastError = error
                Log.e(LOG_TAG, "Failed to set mock location for provider=$provider", error)
            }
        }

        return if (successCount > 0) {
            MockLocationResult(
                ok = true,
                message = "Mock location set for $successCount provider(s): lat=$lat lon=$lon accuracy=$accuracy",
            )
        } else {
            MockLocationResult(
                ok = false,
                message = "Failed to set mock location. Confirm Developer options mock location app selection.",
                error = lastError,
            )
        }
    }

    private fun ensureTestProvider(provider: String) {
        try {
            locationManager.addTestProvider(
                provider,
                false,
                false,
                false,
                false,
                true,
                true,
                true,
                Criteria.POWER_LOW,
                Criteria.ACCURACY_FINE,
            )
            Log.e(LOG_TAG, "Added test provider: $provider")
        } catch (alreadyExists: IllegalArgumentException) {
            Log.e(LOG_TAG, "Test provider already exists or provider can be reused: $provider", alreadyExists)
        } catch (security: SecurityException) {
            Log.e(LOG_TAG, "Cannot add test provider, will try existing provider: $provider", security)
        } catch (error: RuntimeException) {
            Log.e(LOG_TAG, "Failed to add test provider, will try existing provider: $provider", error)
        }
    }

    private fun buildLocation(provider: String, lat: Double, lon: Double, accuracy: Float): Location {
        return Location(provider).apply {
            latitude = lat
            longitude = lon
            this.accuracy = accuracy
            time = System.currentTimeMillis()
            elapsedRealtimeNanos = SystemClock.elapsedRealtimeNanos()
        }
    }

    private fun isSelectedAsMockLocationApp(): Boolean {
        if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            Log.e(LOG_TAG, "Fine location permission is not granted; mock app selection still required.")
        }

        val appOps = context.getSystemService(AppOpsManager::class.java)
        val mode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_MOCK_LOCATION,
                Process.myUid(),
                context.packageName,
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_MOCK_LOCATION,
                Process.myUid(),
                context.packageName,
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }
}
