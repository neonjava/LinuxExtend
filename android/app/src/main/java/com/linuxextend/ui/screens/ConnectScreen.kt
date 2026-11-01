package com.linuxextend.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.linuxextend.network.DiscoveredServer
import com.linuxextend.network.ServerDiscovery
import kotlinx.coroutines.launch

@Composable
fun ConnectScreen(onConnect: (String) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val discovery = remember { ServerDiscovery(context) }
    val servers = remember { mutableStateListOf<DiscoveredServer>() }
    var isSearching by remember { mutableStateOf(false) }

    var ipAddress by remember { mutableStateOf("127.0.0.1") }
    var port by remember { mutableStateOf("8080") }
    var usbMode by remember { mutableStateOf(true) }
    var showAdvancedWifi by remember { mutableStateOf(false) }

    // Start mDNS discovery only when advanced WiFi mode is enabled
    DisposableEffect(showAdvancedWifi) {
        if (showAdvancedWifi) {
            isSearching = true
            val job = scope.launch {
                try {
                    discovery.discover().collect { server ->
                        if (servers.none { it.host == server.host && it.port == server.port }) {
                            servers.add(server)
                        }
                    }
                } catch (_: Exception) {
                    isSearching = false
                }
            }
            onDispose {
                job.cancel()
                isSearching = false
            }
        } else {
            onDispose {}
        }
    }

    fun buildWsUrl(): String {
        val host = if (usbMode) "127.0.0.1" else ipAddress.trim()
        val p = port.trim().ifEmpty { "8080" }
        return "ws://$host:$p/ws/screen"
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(32.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Left side: Branding & Instructions
            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(end = 32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = "🖥️",
                    fontSize = 56.sp,
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "LinuxExtend",
                    style = MaterialTheme.typography.headlineLarge,
                    color = MaterialTheme.colorScheme.onBackground,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "USB Second Monitor (No Wi-Fi)",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    text = "Plug in USB cable and tap Connect below.\nZero latency. No Wi-Fi or Bluetooth required.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    lineHeight = 18.sp,
                )
            }

            // Right side: Connection Actions
            Column(
                modifier = Modifier
                    .weight(1.5f)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(24.dp),
            ) {
                // USB Priority Action
                Text(
                    text = "🔌 Direct USB Connection",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "Connects directly through ADB reverse port forwarding (127.0.0.1:8080)",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(14.dp))

                Button(
                    onClick = { onConnect("ws://127.0.0.1:8080/ws/screen") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                    ),
                ) {
                    Text(
                        text = "⚡ Connect via USB (1-Tap)",
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                    )
                }

                Spacer(Modifier.height(16.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Spacer(Modifier.height(12.dp))

                // Optional / Advanced Wi-Fi Toggle
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showAdvancedWifi = !showAdvancedWifi }
                        .padding(vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = if (showAdvancedWifi) "▼ Hide Wi-Fi Settings" else "▶ Wi-Fi / Custom IP (Optional)",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }

                if (showAdvancedWifi) {
                    Spacer(Modifier.height(8.dp))
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        OutlinedTextField(
                            value = ipAddress,
                            onValueChange = { 
                                ipAddress = it 
                                usbMode = false
                            },
                            label = { Text("IP Address") },
                            singleLine = true,
                            modifier = Modifier.weight(2f),
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = ImeAction.Next,
                            ),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.primary,
                                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                            ),
                        )
                        Spacer(Modifier.width(8.dp))
                        OutlinedTextField(
                            value = port,
                            onValueChange = { port = it },
                            label = { Text("Port") },
                            singleLine = true,
                            modifier = Modifier.weight(1f),
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = ImeAction.Done,
                            ),
                            keyboardActions = KeyboardActions(
                                onDone = { onConnect(buildWsUrl()) },
                            ),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.primary,
                                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                            ),
                        )
                    }

                    Spacer(Modifier.height(8.dp))

                    OutlinedButton(
                        onClick = { onConnect(buildWsUrl()) },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                    ) {
                        Text("Connect to Custom IP")
                    }
                }
            }
        }
    }
}

@Composable
private fun ServerItem(server: DiscoveredServer, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(Color(0xFF4ECDC4)),
        )
        Spacer(Modifier.width(10.dp))
        Column {
            Text(
                text = server.name,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                text = "${server.host.hostAddress}:${server.port}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
