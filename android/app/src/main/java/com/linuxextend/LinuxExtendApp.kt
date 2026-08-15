package com.linuxextend

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.linuxextend.ui.screens.ConnectScreen
import com.linuxextend.ui.screens.DisplayScreen
import com.linuxextend.ui.theme.LinuxExtendTheme
import java.net.URLDecoder
import java.net.URLEncoder

@Composable
fun LinuxExtendApp() {
    LinuxExtendTheme {
        val navController = rememberNavController()

        NavHost(navController = navController, startDestination = "connect") {
            composable("connect") {
                ConnectScreen(
                    onConnect = { wsUrl ->
                        val encoded = URLEncoder.encode(wsUrl, "UTF-8")
                        navController.navigate("display/$encoded")
                    }
                )
            }

            composable(
                route = "display/{wsUrl}",
                arguments = listOf(
                    navArgument("wsUrl") { type = NavType.StringType }
                )
            ) { backStackEntry ->
                val encodedUrl = backStackEntry.arguments?.getString("wsUrl") ?: ""
                val wsUrl = URLDecoder.decode(encodedUrl, "UTF-8")
                DisplayScreen(
                    wsUrl = wsUrl,
                    onDisconnect = { navController.popBackStack() }
                )
            }
        }
    }
}
