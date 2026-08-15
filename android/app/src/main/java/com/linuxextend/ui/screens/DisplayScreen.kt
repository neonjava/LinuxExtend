package com.linuxextend.ui.screens

import android.app.Activity
import android.view.WindowManager
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontVariation.weight
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.linuxextend.network.ConnectionState
import com.linuxextend.viewmodel.ScreenViewModel

@Composable
fun DisplayScreen(
    wsUrl: String,
    onDisconnect: () -> Unit,
    viewModel: ScreenViewModel = viewModel(),
) {
    val frame by viewModel.currentFrame.collectAsStateWithLifecycle()
    val connectionState by viewModel.connectionState.collectAsStateWithLifecycle()
    val fps by viewModel.fps.collectAsStateWithLifecycle()

    var showOverlay by remember { mutableStateOf(false) }
    var showFps by remember { mutableStateOf(true) }

    // Keep screen on
    val context = LocalContext.current
    DisposableEffect(Unit) {
        val window = (context as? Activity)?.window
        window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    // Connect on launch
    LaunchedEffect(wsUrl) {
        viewModel.connect(wsUrl)
    }

    // Clean up on leave
    DisposableEffect(Unit) {
        onDispose {
            viewModel.disconnect()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .pointerInput(Unit) {
                detectTapGestures(
                    onLongPress = { showOverlay = !showOverlay },
                    onDoubleTap = { showFps = !showFps },
                )
            },
        contentAlignment = Alignment.Center,
    ) {
        // Stream display
        frame?.let { bitmap ->
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = "Second Screen",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Fit,
            )
        }

        // Connection status overlay (center)
        when (connectionState) {
            ConnectionState.CONNECTING -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(36.dp),
                        color = Color(0xFF4ECDC4),
                        strokeWidth = 3.dp,
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = "Connecting...",
                        color = Color.Gray,
                        fontSize = 14.sp,
                    )
                }
            }
            ConnectionState.ERROR -> {
                if (frame == null) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text("⚠️", fontSize = 36.sp)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = "Connection failed",
                            color = Color(0xFFE74C3C),
                            fontSize = 14.sp,
                        )
                        Text(
                            text = "Reconnecting...",
                            color = Color.Gray,
                            fontSize = 12.sp,
                        )
                    }
                }
            }
            ConnectionState.DISCONNECTED -> {
                if (frame == null) {
                    Text(
                        text = "Disconnected",
                        color = Color.Gray,
                        fontSize = 14.sp,
                    )
                }
            }
            ConnectionState.CONNECTED -> { /* showing frames */ }
        }

        // FPS counter (top-right)
        AnimatedVisibility(
            visible = showFps && connectionState == ConnectionState.CONNECTED,
            enter = fadeIn(),
            exit = fadeOut(),
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(12.dp),
        ) {
            Row(
                modifier = Modifier
                    .background(
                        Color.Black.copy(alpha = 0.5f),
                        RoundedCornerShape(6.dp),
                    )
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .background(Color(0xFF4ECDC4), RoundedCornerShape(3.dp)),
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = "$fps FPS",
                    color = Color.White.copy(alpha = 0.8f),
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }

        // Disconnect overlay (long press)
        AnimatedVisibility(
            visible = showOverlay,
            enter = fadeIn(),
            exit = fadeOut(),
            modifier = Modifier.align(Alignment.BottomCenter).padding(24.dp),
        ) {
            Button(
                onClick = {
                    showOverlay = false
                    onDisconnect()
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFFE74C3C),
                    contentColor = Color.White,
                ),
                shape = RoundedCornerShape(10.dp),
            ) {
                Text("Disconnect", fontWeight = FontWeight.SemiBold)
            }
        }
    }
}
