"""Screen capture engine using grim + TurboJPEG for Hyprland outputs."""

import hashlib
import logging
import subprocess
import threading
import time

import numpy as np
from turbojpeg import TurboJPEG

logger = logging.getLogger(__name__)


class CaptureError(Exception):
    """Raised when screen capture operations fail."""


class ScreenCapture:
    """Captures frames from a Hyprland output using grim + TurboJPEG.

    Runs a background thread that:
    1. Captures PPM frames via grim (faster than JPEG from grim)
    2. Detects unchanged frames to skip encoding
    3. Encodes to JPEG via TurboJPEG (libjpeg-turbo)
    4. Stores the latest frame for WebSocket consumers

    Usage:
        capture = ScreenCapture("HEADLESS-1", fps=25, quality=75)
        capture.start()
        frame = capture.get_frame()  # Latest JPEG bytes or None
        capture.stop()
    """

    def __init__(self, output_name: str, fps: int = 25, quality: int = 75):
        self.output_name = output_name
        self.target_fps = fps
        self.frame_interval = 1.0 / fps
        self.quality = quality

        # TurboJPEG encoder with fallback
        self._jpeg = None
        try:
            self._jpeg = TurboJPEG()
            logger.info("Using TurboJPEG hardware/SIMD acceleration")
        except Exception:
            logger.info("TurboJPEG native library not found; using direct grim JPEG capture")

        # Thread-safe latest frame storage
        self._latest_frame: bytes | None = None
        self._lock = threading.Lock()

        # Capture thread control
        self._running = False
        self._thread: threading.Thread | None = None

        # Dirty frame detection
        self._prev_hash: str | None = None

        # FPS tracking
        self._frame_count = 0
        self._fps_start_time = time.monotonic()
        self._actual_fps: float = 0.0

        # Verify grim is available
        self._check_grim()

    def _check_grim(self) -> None:
        """Verify that grim is installed and accessible."""
        try:
            subprocess.run(
                ["grim", "--help"],
                capture_output=True,
                timeout=3,
            )
        except FileNotFoundError:
            raise CaptureError(
                "grim is not installed. Install it with: sudo dnf install grim"
            )
        except subprocess.TimeoutExpired:
            pass  # --help might hang, but binary exists

    def _capture_ppm(self) -> bytes | None:
        """Capture a single PPM frame from grim to stdout."""
        try:
            result = subprocess.run(
                ["grim", "-c", "-o", self.output_name, "-t", "ppm", "-"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace").strip()
                if "unknown output" in stderr:
                    logger.error("Output '%s' not found", self.output_name)
                    return None
                logger.warning("grim capture failed: %s", stderr)
                return None
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning("grim capture timed out")
            return None
        except Exception as e:
            logger.error("Capture error: %s", e)
            return None

    def _parse_ppm(self, data: bytes) -> np.ndarray | None:
        """Parse PPM (P6) binary data into a numpy RGB array.

        PPM P6 format:
            P6\\n
            WIDTH HEIGHT\\n
            255\\n
            <raw RGB bytes>
        """
        try:
            # Find the header end — three newlines
            # P6\nWIDTH HEIGHT\nMAXVAL\n
            pos = 0

            # Line 1: "P6"
            nl1 = data.index(b"\n", pos)
            magic = data[pos:nl1].strip()
            if magic != b"P6":
                logger.error("Not a PPM P6 file: %s", magic)
                return None
            pos = nl1 + 1

            # Skip comments (lines starting with #)
            while data[pos:pos + 1] == b"#":
                nl = data.index(b"\n", pos)
                pos = nl + 1

            # Line 2: "WIDTH HEIGHT"
            nl2 = data.index(b"\n", pos)
            dims = data[pos:nl2].split()
            width = int(dims[0])
            height = int(dims[1])
            pos = nl2 + 1

            # Line 3: "255" (max value)
            nl3 = data.index(b"\n", pos)
            pos = nl3 + 1

            # Remaining bytes are raw RGB
            pixel_data = data[pos:]
            expected_size = width * height * 3

            if len(pixel_data) < expected_size:
                logger.warning(
                    "PPM data too short: got %d, expected %d",
                    len(pixel_data), expected_size,
                )
                return None

            img = np.frombuffer(pixel_data[:expected_size], dtype=np.uint8)
            img = img.reshape((height, width, 3))
            return img

        except (ValueError, IndexError) as e:
            logger.error("PPM parse error: %s", e)
            return None

    def _is_frame_dirty(self, img: np.ndarray) -> bool:
        """Check if the frame has changed from the previous one.

        Uses a fast downsampled hash comparison to detect static screens.
        """
        # Downsample heavily: take every 32nd pixel
        sample = img[::32, ::32, :].tobytes()
        frame_hash = hashlib.md5(sample).hexdigest()

        if frame_hash == self._prev_hash:
            return False

        self._prev_hash = frame_hash
        return True

    def _update_fps(self) -> None:
        """Track actual capture FPS."""
        self._frame_count += 1
        now = time.monotonic()
        elapsed = now - self._fps_start_time

        if elapsed >= 1.0:
            self._actual_fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_start_time = now

    def _capture_loop(self) -> None:
        """Main capture loop running in a background thread."""
        logger.info(
            "Capture started: output=%s fps=%d quality=%d",
            self.output_name, self.target_fps, self.quality,
        )

        consecutive_failures = 0
        max_failures = 30  # Stop after ~30 consecutive failures

        while self._running:
            t0 = time.monotonic()

            if self._jpeg is None:
                # Direct grim JPEG capture mode
                try:
                    proc = subprocess.run(
                        ["grim", "-c", "-o", self.output_name, "-t", "jpeg", "-q", str(self.quality), "-"],
                        capture_output=True,
                        timeout=5,
                    )
                    if proc.returncode != 0:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            logger.error("Too many consecutive capture failures (%d)", consecutive_failures)
                            self._running = False
                            break
                        time.sleep(self.frame_interval)
                        continue

                    jpg_bytes = proc.stdout
                    consecutive_failures = 0

                    # Dirty check on first 4KB of JPEG data for static screen detection
                    sample_hash = hashlib.md5(jpg_bytes[:4096]).hexdigest()
                    if sample_hash == self._prev_hash:
                        elapsed = time.monotonic() - t0
                        sleep_time = max(0.0, self.frame_interval - elapsed)
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                        continue

                    self._prev_hash = sample_hash

                    with self._lock:
                        self._latest_frame = jpg_bytes

                    self._update_fps()
                except Exception as e:
                    logger.error("Direct capture error: %s", e)
                    time.sleep(self.frame_interval)
                    continue
            else:
                # PPM + TurboJPEG mode
                ppm_data = self._capture_ppm()

                if ppm_data is None:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error(
                            "Too many consecutive capture failures (%d). Stopping.",
                            consecutive_failures,
                        )
                        self._running = False
                        break
                    time.sleep(self.frame_interval)
                    continue

                consecutive_failures = 0

                # Parse PPM to numpy array
                img = self._parse_ppm(ppm_data)
                if img is None:
                    time.sleep(self.frame_interval)
                    continue

                # Skip encoding if frame hasn't changed (saves CPU)
                if not self._is_frame_dirty(img):
                    elapsed = time.monotonic() - t0
                    sleep_time = max(0.0, self.frame_interval - elapsed)
                    time.sleep(sleep_time)
                    continue

                # Encode to JPEG using TurboJPEG
                try:
                    jpg_bytes = self._jpeg.encode(img, quality=self.quality)
                except Exception as e:
                    logger.error("JPEG encoding failed: %s", e)
                    time.sleep(self.frame_interval)
                    continue

                # Store the latest frame
                with self._lock:
                    self._latest_frame = jpg_bytes

                self._update_fps()

            # Frame pacing
            elapsed = time.monotonic() - t0
            sleep_time = max(0.0, self.frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("Capture loop ended")

    def start(self) -> None:
        """Start the capture background thread."""
        if self._running:
            logger.warning("Capture is already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="screen-capture"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the capture background thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("Capture stopped")

    def get_frame(self) -> bytes | None:
        """Get the latest JPEG frame bytes (thread-safe)."""
        with self._lock:
            return self._latest_frame

    @property
    def actual_fps(self) -> float:
        """Current actual capture FPS."""
        return round(self._actual_fps, 1)

    @property
    def is_running(self) -> bool:
        """Whether the capture thread is active."""
        return self._running
