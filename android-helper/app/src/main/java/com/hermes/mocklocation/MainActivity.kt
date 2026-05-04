package com.hermes.mocklocation

import android.app.AppOpsManager
import android.app.Activity
import android.content.Context
import android.os.Bundle
import android.os.Process
import android.util.Log
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var statusText: TextView
    private lateinit var lastLocationText: TextView
    private lateinit var mockAppText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.e(LOG_TAG, "MainActivity onCreate entered")

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 48, 40, 40)
        }

        val title = TextView(this).apply {
            text = "Hermes Mock Location Helper"
            textSize = 22f
        }
        statusText = TextView(this).apply { textSize = 16f }
        lastLocationText = TextView(this).apply { textSize = 16f }
        mockAppText = TextView(this).apply { textSize = 16f }
        val helpText = TextView(this).apply {
            text = "Select this app as the mock location app in Android Developer options before sending ADB broadcasts."
            textSize = 15f
        }

        layout.addView(title)
        layout.addView(statusText)
        layout.addView(lastLocationText)
        layout.addView(mockAppText)
        layout.addView(helpText)
        setContentView(layout)
    }

    override fun onResume() {
        super.onResume()
        renderStatus()
    }

    private fun renderStatus() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val status = prefs.getString(KEY_STATUS, "Waiting for ADB broadcast.")
        val lat = prefs.getString(KEY_LAT, "-")
        val lon = prefs.getString(KEY_LON, "-")
        val accuracy = prefs.getString(KEY_ACCURACY, "-")
        val updatedAt = prefs.getString(KEY_UPDATED_AT, "-")

        statusText.text = "Status: $status"
        lastLocationText.text = "Last location: lat=$lat, lon=$lon, accuracy=$accuracy, updated=$updatedAt"
        mockAppText.text = "Selected as mock location app: ${isMockLocationApp()}"
    }

    private fun isMockLocationApp(): Boolean {
        val appOps = getSystemService(AppOpsManager::class.java)
        val mode = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                AppOpsManager.OPSTR_MOCK_LOCATION,
                Process.myUid(),
                packageName,
            )
        } else {
            @Suppress("DEPRECATION")
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_MOCK_LOCATION,
                Process.myUid(),
                packageName,
            )
        }
        return mode == AppOpsManager.MODE_ALLOWED
    }
}
