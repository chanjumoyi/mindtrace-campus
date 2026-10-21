package com.mindtrace.collector;

import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        installInsetBridge();
        hideSystemNavigation();
        // Some launchers/emulators restore the navigation bar after the
        // WebView is attached, so re-apply once the first frame is stable.
        View decor = getWindow().getDecorView();
        decor.postDelayed(this::hideSystemNavigation, 500);
        decor.postDelayed(this::hideSystemNavigation, 1500);
        // Re-dispatch after the first page load so the CSS inset variables
        // are injected into the loaded document, not about:blank.
        decor.postDelayed(decor::requestApplyInsets, 1200);
        decor.postDelayed(decor::requestApplyInsets, 2500);
    }

    @Override
    public void onResume() {
        super.onResume();
        hideSystemNavigation();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemNavigation();
        }
    }

    /**
     * The app is edge-to-edge, but older WebViews do not expose CSS
     * env(safe-area-inset-*). Publish the status-bar inset as CSS variables
     * instead; the navigation bar itself stays hidden.
     */
    private void installInsetBridge() {
        View decor = getWindow().getDecorView();
        ViewCompat.setOnApplyWindowInsetsListener(decor, (view, windowInsets) -> {
            Insets status = windowInsets.getInsets(
                WindowInsetsCompat.Type.statusBars() | WindowInsetsCompat.Type.displayCutout()
            );
            Insets navigation = windowInsets.getInsets(WindowInsetsCompat.Type.navigationBars());
            float density = getResources().getDisplayMetrics().density;
            int top = Math.round(
                (windowInsets.isVisible(WindowInsetsCompat.Type.statusBars()) ? status.top : 0) / density
            );
            int bottom = Math.round(
                (windowInsets.isVisible(WindowInsetsCompat.Type.navigationBars()) ? navigation.bottom : 0) / density
            );
            String script = String.format(
                "document.documentElement.style.setProperty('--native-inset-top','%dpx');" +
                "document.documentElement.style.setProperty('--native-inset-bottom','%dpx');",
                top,
                bottom
            );
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().evaluateJavascript(script, null);
            }
            return windowInsets;
        });
    }

    /**
     * The collector is a full-screen writing surface. Android's three-button
     * navigation bar overlaps the bottom action area, so keep it hidden and
     * let a deliberate edge swipe reveal it temporarily.
     */
    @SuppressWarnings("deprecation")
    private void hideSystemNavigation() {
        View decor = getWindow().getDecorView();
        decor.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        }
    }
}
