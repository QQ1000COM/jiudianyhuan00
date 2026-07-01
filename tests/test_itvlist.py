"""Unit tests for ITVlist.py"""

import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import aiohttp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ITVlist


class TestIsValidStream:
    """Tests for the is_valid_stream() pure function."""

    def test_valid_http_m3u8(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4:8080/live/stream.m3u8") is True

    def test_valid_http_ts(self):
        assert ITVlist.is_valid_stream("http://example.com/live/ch1.ts") is True

    def test_valid_http_flv(self):
        assert ITVlist.is_valid_stream("http://example.com/live/ch1.flv") is True

    def test_valid_http_mp4(self):
        assert ITVlist.is_valid_stream("http://example.com/video.mp4") is True

    def test_valid_http_mkv(self):
        assert ITVlist.is_valid_stream("http://example.com/video.mkv") is True

    def test_reject_rtp_protocol(self):
        assert ITVlist.is_valid_stream("rtp://239.1.2.3:5000") is False

    def test_reject_udp_protocol(self):
        assert ITVlist.is_valid_stream("udp://239.1.2.3:5000") is False

    def test_reject_rtsp_protocol(self):
        assert ITVlist.is_valid_stream("rtsp://192.168.1.1/stream") is False

    def test_reject_multicast_239(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4/239.0.0.1:5000.m3u8") is False

    def test_reject_private_16(self):
        assert ITVlist.is_valid_stream("http://16.1.2.3/live/ch.m3u8") is False

    def test_reject_private_10(self):
        assert ITVlist.is_valid_stream("http://10.0.0.1/live/ch.m3u8") is False

    def test_reject_private_192(self):
        assert ITVlist.is_valid_stream("http://192.168.1.1/live/ch.m3u8") is False

    def test_reject_paiptv_path(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4/paiptv/live.m3u8") is False

    def test_reject_snm_path(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4/00/SNM/stream.m3u8") is False

    def test_reject_channel_path(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4/00/CHANNEL001.m3u8") is False

    def test_reject_no_valid_extension(self):
        assert ITVlist.is_valid_stream("http://1.2.3.4/live/stream.html") is False

    def test_reject_non_http(self):
        assert ITVlist.is_valid_stream("ftp://1.2.3.4/stream.m3u8") is False

    def test_reject_empty_string(self):
        assert ITVlist.is_valid_stream("") is False


class TestGenerateUrls:
    """Tests for the generate_urls() async function."""

    @pytest.mark.asyncio
    async def test_generates_256_ips_times_paths(self):
        url = "http://192.168.1.1:4022"
        results = await ITVlist.generate_urls(url)
        # 255 IPs * 2 JSON paths = 510 URLs
        assert len(results) == 510

    @pytest.mark.asyncio
    async def test_url_format(self):
        url = "http://10.20.30.1:8080"
        results = await ITVlist.generate_urls(url)
        assert "http://10.20.30.1:8080/iptv/live/1000.json?key=txiptv" in results
        assert "http://10.20.30.1:8080/iptv/live/1001.json?key=txiptv" in results
        assert "http://10.20.30.255:8080/iptv/live/1000.json?key=txiptv" in results

    @pytest.mark.asyncio
    async def test_ip_prefix_preserved(self):
        url = "http://172.16.0.1:9999"
        results = await ITVlist.generate_urls(url)
        # All generated URLs should have the prefix 172.16.0.X
        for r in results:
            assert "172.16.0." in r

    @pytest.mark.asyncio
    async def test_port_preserved(self):
        url = "http://1.2.3.4:5555"
        results = await ITVlist.generate_urls(url)
        for r in results:
            assert ":5555/" in r


class TestCheckUrl:
    """Tests for the check_url() async function."""

    @pytest.mark.asyncio
    async def test_returns_url_on_200(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.check_url(mock_session, "http://test.com/api", semaphore)
        assert result == "http://test.com/api"

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        mock_resp = AsyncMock()
        mock_resp.status = 404
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.check_url(mock_session, "http://test.com/api", semaphore)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.check_url(mock_session, "http://test.com/api", semaphore)
        assert result is None


class TestFetchJson:
    """Tests for the fetch_json() async function."""

    @pytest.mark.asyncio
    async def test_parses_valid_json(self):
        json_data = {
            "data": [
                {"name": "CCTV-1", "url": "http://1.2.3.4/live/cctv1.m3u8"},
                {"name": "湖南卫视", "url": "/live/hunan.ts"},
            ]
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=json_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        results = await ITVlist.fetch_json(mock_session, "http://1.2.3.4/iptv/live/1000.json?key=txiptv", semaphore)

        assert len(results) == 2
        # CCTV-1 should be mapped to CCTV1
        assert results[0][0] == "CCTV1"
        assert results[0][1] == "http://1.2.3.4/live/cctv1.m3u8"

    @pytest.mark.asyncio
    async def test_skips_entries_with_comma_in_url(self):
        json_data = {
            "data": [
                {"name": "TestCh", "url": "http://a.com/live,extra"},
            ]
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=json_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        results = await ITVlist.fetch_json(mock_session, "http://test.com/api", semaphore)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_skips_entries_without_name(self):
        json_data = {
            "data": [
                {"name": "", "url": "http://a.com/live.m3u8"},
                {"name": None, "url": "http://b.com/live.m3u8"},
            ]
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=json_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        results = await ITVlist.fetch_json(mock_session, "http://test.com/api", semaphore)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_relative_url_resolved(self):
        json_data = {
            "data": [
                {"name": "TestChannel", "url": "/live/test.m3u8"},
            ]
        }

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=json_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        results = await ITVlist.fetch_json(
            mock_session, "http://1.2.3.4:8080/iptv/live/1000.json?key=txiptv", semaphore
        )
        assert results[0][1] == "http://1.2.3.4:8080/live/test.m3u8"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("connection error"))

        semaphore = asyncio.Semaphore(10)
        results = await ITVlist.fetch_json(mock_session, "http://test.com/api", semaphore)
        assert results == []


class TestMeasureSpeed:
    """Tests for measure_speed() async function."""

    @pytest.mark.asyncio
    async def test_returns_ms_on_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.head = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.measure_speed(mock_session, "http://test.com/stream.m3u8", semaphore)
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_returns_999999_on_non_200(self):
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.head = MagicMock(return_value=mock_resp)

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.measure_speed(mock_session, "http://test.com/stream.m3u8", semaphore)
        assert result == 999999

    @pytest.mark.asyncio
    async def test_returns_999999_on_exception(self):
        mock_session = AsyncMock()
        mock_session.head = MagicMock(side_effect=asyncio.TimeoutError())

        semaphore = asyncio.Semaphore(10)
        result = await ITVlist.measure_speed(mock_session, "http://test.com/stream.m3u8", semaphore)
        assert result == 999999


class TestLoadUrls:
    """Tests for load_urls() with mocked network."""

    @patch("ITVlist.requests.get")
    def test_loads_urls_successfully(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "http://1.2.3.4:8080\nhttp://5.6.7.8:9090\n"
        mock_get.return_value = mock_resp

        urls = ITVlist.load_urls()
        assert urls == ["http://1.2.3.4:8080", "http://5.6.7.8:9090"]

    @patch("ITVlist.requests.get")
    def test_skips_empty_lines(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = "http://1.2.3.4:8080\n\n\nhttp://5.6.7.8:9090\n\n"
        mock_get.return_value = mock_resp

        urls = ITVlist.load_urls()
        assert urls == ["http://1.2.3.4:8080", "http://5.6.7.8:9090"]

    @patch("ITVlist.requests.get")
    def test_exits_on_failure(self, mock_get):
        mock_get.side_effect = Exception("network error")

        with pytest.raises(SystemExit):
            ITVlist.load_urls()


class TestChannelMapping:
    """Tests for the channel name mapping logic in fetch_json."""

    def test_all_mapping_keys_in_categories(self):
        """Every mapped channel should appear in at least one category."""
        all_channels = set()
        for channels in ITVlist.CHANNEL_CATEGORIES.values():
            all_channels.update(channels)

        for std_name in ITVlist.CHANNEL_MAPPING:
            assert std_name in all_channels, f"{std_name} in CHANNEL_MAPPING but not in CHANNEL_CATEGORIES"

    def test_no_duplicate_aliases(self):
        """No alias should appear in multiple mappings."""
        seen = {}
        for std_name, aliases in ITVlist.CHANNEL_MAPPING.items():
            for alias in aliases:
                if alias in seen:
                    # Allow same alias to map to same standard name
                    assert seen[alias] == std_name, (
                        f"Alias '{alias}' maps to both '{seen[alias]}' and '{std_name}'"
                    )
                seen[alias] = std_name
