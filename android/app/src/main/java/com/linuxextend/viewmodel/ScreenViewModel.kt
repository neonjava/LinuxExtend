package com.linuxextend.viewmodel

import android.graphics.Bitmap
import androidx.lifecycle.ViewModel
import com.linuxextend.network.ConnectionState
import com.linuxextend.network.FrameReceiver
import kotlinx.coroutines.flow.StateFlow

class ScreenViewModel : ViewModel() {

    private val frameReceiver = FrameReceiver()

    val currentFrame: StateFlow<Bitmap?> = frameReceiver.currentFrame
    val connectionState: StateFlow<ConnectionState> = frameReceiver.connectionState
    val fps: StateFlow<Int> = frameReceiver.fps

    fun connect(wsUrl: String) {
        frameReceiver.connect(wsUrl)
    }

    fun disconnect() {
        frameReceiver.disconnect()
    }

    override fun onCleared() {
        super.onCleared()
        frameReceiver.destroy()
    }
}
