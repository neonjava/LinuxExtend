"""mDNS/Zeroconf service advertising for network discovery."""

import logging
import socket

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


def _get_local_ip() -> str:
    """Get the local IP address (not 127.0.0.1) by connecting to an external address.

    This doesn't actually send any data — it just determines which
    network interface would be used for outbound connections.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        # Connect to a public DNS server (doesn't send data)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        logger.warning("Could not determine local IP, falling back to hostname resolution")
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class ServiceAdvertiser:
    """Advertises the LinuxExtend server via mDNS/Zeroconf.

    Android clients can discover the server on the local network
    by looking for `_linuxextend._tcp.local.` services.
    """

    def __init__(
        self,
        port: int,
        name: str = "LinuxExtend",
        resolution: str = "1920x1080",
    ):
        self.port = port
        self.name = name
        self.resolution = resolution

        self._zeroconf: Zeroconf | None = None
        self._service_info: ServiceInfo | None = None
        self._local_ip = _get_local_ip()

    def start(self) -> None:
        """Register the mDNS service."""
        try:
            hostname = socket.gethostname()

            self._service_info = ServiceInfo(
                type_="_linuxextend._tcp.local.",
                name=f"{self.name}._linuxextend._tcp.local.",
                addresses=[socket.inet_aton(self._local_ip)],
                port=self.port,
                properties={
                    "version": "1.0",
                    "resolution": self.resolution,
                    "hostname": hostname,
                },
                server=f"{hostname}.local.",
            )

            self._zeroconf = Zeroconf()
            self._zeroconf.register_service(self._service_info)

            logger.info(
                "mDNS service advertised: %s._linuxextend._tcp.local. at %s:%d",
                self.name, self._local_ip, self.port,
            )
        except Exception as e:
            logger.error("Failed to start mDNS advertising: %s", e)
            self._zeroconf = None

    def stop(self) -> None:
        """Unregister the mDNS service and close Zeroconf."""
        if self._zeroconf and self._service_info:
            try:
                self._zeroconf.unregister_service(self._service_info)
                logger.info("mDNS service unregistered")
            except Exception as e:
                logger.warning("Error unregistering mDNS service: %s", e)

        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception:
                pass
            self._zeroconf = None

    @property
    def local_ip(self) -> str:
        """The local IP address being advertised."""
        return self._local_ip
