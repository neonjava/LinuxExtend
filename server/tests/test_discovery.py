"""Tests for mDNS ServiceAdvertiser and IP discovery."""

from unittest.mock import MagicMock, patch
from linuxextend.discovery import ServiceAdvertiser, _get_local_ip


def test_get_local_ip():
    ip = _get_local_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4


def test_service_advertiser_lifecycle():
    with patch("linuxextend.discovery.Zeroconf") as mock_zeroconf:
        mock_instance = MagicMock()
        mock_zeroconf.return_value = mock_instance

        advertiser = ServiceAdvertiser(
            port=8080,
            name="TestExtend",
            resolution="1920x1080",
        )

        advertiser.start()
        assert mock_instance.register_service.called
        assert advertiser.local_ip == advertiser._local_ip

        advertiser.stop()
        assert mock_instance.unregister_service.called
        assert mock_instance.close.called
