package com.linuxextend.network

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    ERROR,
}

class FrameReceiver {
    companion object {
        private const val TAG = "FrameReceiver"
        private const val RECONNECT_BASE_MS = 1000L
        private const val RECONNECT_MAX_MS = 16000L
    }

    private val _currentFrame = MutableStateFlow<Bitmap?>(null)
    val currentFrame: StateFlow<Bitmap?> = _currentFrame.asStateFlow()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _fps = MutableStateFlow(0)
    val fps: StateFlow<Int> = _fps.asStateFlow()

    // Conflated channel: always keeps only the latest frame, drops stale ones
    private val frameChannel = Channel<ByteArray>(capacity = Channel.CONFLATED)

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // Keep-alive for streaming
        .connectTimeout(5, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var currentUrl: String? = null
    private var shouldReconnect = false
    private var reconnectAttempt = 0

    // FPS tracking
    private val frameCount = AtomicInteger(0)
    private var fpsTrackingStarted = false

    private val bitmapOptions = BitmapFactory.Options().apply {
        inPreferredConfig = Bitmap.Config.RGB_565 // 50% memory savings vs ARGB_8888
    }

    init {
        // Frame decode consumer coroutine
        scope.launch(Dispatchers.Default) {
            frameChannel.receiveAsFlow().collect { bytes ->
                try {
                    val bitmap = BitmapFactory.decodeByteArray(
                        bytes, 0, bytes.size, bitmapOptions
                    )
                    if (bitmap != null) {
                        _currentFrame.value = bitmap
                        frameCount.incrementAndGet()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Frame decode error", e)
                }
            }
        }

        // FPS counter coroutine
        scope.launch {
            while (true) {
                kotlinx.coroutines.delay(1000)
                if (fpsTrackingStarted) {
                    _fps.value = frameCount.getAndSet(0)
                }
            }
        }
    }

    fun connect(wsUrl: String) {
        disconnect()

        currentUrl = wsUrl
        shouldReconnect = true
        reconnectAttempt = 0
        _connectionState.value = ConnectionState.CONNECTING

        doConnect(wsUrl)
    }

    private fun doConnect(wsUrl: String) {
        Log.i(TAG, "Connecting to $wsUrl")

        val request = Request.Builder()
            .url(wsUrl)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Connected to $wsUrl")
                _connectionState.value = ConnectionState.CONNECTED
                reconnectAttempt = 0
                fpsTrackingStarted = true
                frameCount.set(0)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                // Send to conflated channel — drops old frame if decoder is busy
                frameChannel.trySend(bytes.toByteArray())
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Server closing: $code $reason")
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Connection closed: $code $reason")
                _connectionState.value = ConnectionState.DISCONNECTED
                fpsTrackingStarted = false
                _fps.value = 0
                attemptReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "Connection failed: ${t.message}")
                _connectionState.value = ConnectionState.ERROR
                fpsTrackingStarted = false
                _fps.value = 0
                attemptReconnect()
            }
        })
    }

    private fun attemptReconnect() {
        if (!shouldReconnect || currentUrl == null) return

        reconnectAttempt++
        val delay = (RECONNECT_BASE_MS * (1L shl minOf(reconnectAttempt - 1, 4)))
            .coerceAtMost(RECONNECT_MAX_MS)

        Log.i(TAG, "Reconnecting in ${delay}ms (attempt $reconnectAttempt)")

        scope.launch {
            kotlinx.coroutines.delay(delay)
            if (shouldReconnect && currentUrl != null) {
                _connectionState.value = ConnectionState.CONNECTING
                doConnect(currentUrl!!)
            }
        }
    }

    fun disconnect() {
        shouldReconnect = false
        fpsTrackingStarted = false
        _fps.value = 0
        webSocket?.close(1000, "App disconnected")
        webSocket = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    fun destroy() {
        disconnect()
        scope.cancel()
    }
}
