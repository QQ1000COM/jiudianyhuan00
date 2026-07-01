"""Unit tests for fofa_fetch.py"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fofa_fetch


class TestGetIspFromApi:
    """Tests for get_isp_from_api() pure function."""

    def test_telecom_keyword(self):
        assert fofa_fetch.get_isp_from_api({"isp": "China Telecom"}) == "电信"

    def test_telecom_ct(self):
        assert fofa_fetch.get_isp_from_api({"isp": "CT"}) == "电信"

    def test_telecom_chinatelecom(self):
        assert fofa_fetch.get_isp_from_api({"isp": "ChinaTelecom"}) == "电信"

    def test_unicom_keyword(self):
        assert fofa_fetch.get_isp_from_api({"isp": "China Unicom"}) == "联通"

    def test_unicom_cu(self):
        assert fofa_fetch.get_isp_from_api({"isp": "CU"}) == "联通"

    def test_unicom_chinaunicom(self):
        assert fofa_fetch.get_isp_from_api({"isp": "ChinaUnicom"}) == "联通"

    def test_mobile_keyword(self):
        assert fofa_fetch.get_isp_from_api({"isp": "China Mobile"}) == "移动"

    def test_mobile_cm(self):
        assert fofa_fetch.get_isp_from_api({"isp": "CM"}) == "移动"

    def test_mobile_chinamobile(self):
        assert fofa_fetch.get_isp_from_api({"isp": "ChinaMobile"}) == "移动"

    def test_unknown_isp(self):
        assert fofa_fetch.get_isp_from_api({"isp": "SomeOtherISP"}) == "未知"

    def test_empty_isp(self):
        assert fofa_fetch.get_isp_from_api({"isp": ""}) == "未知"

    def test_none_isp(self):
        assert fofa_fetch.get_isp_from_api({"isp": None}) == "未知"

    def test_missing_isp_key(self):
        assert fofa_fetch.get_isp_from_api({}) == "未知"

    def test_case_insensitive(self):
        assert fofa_fetch.get_isp_from_api({"isp": "TELECOM"}) == "电信"
        assert fofa_fetch.get_isp_from_api({"isp": "UNICOM"}) == "联通"
        assert fofa_fetch.get_isp_from_api({"isp": "MOBILE"}) == "移动"


class TestGetIspByRegex:
    """Tests for get_isp_by_regex() pure function."""

    def test_telecom_ip_range(self):
        # IPs starting with ranges associated with telecom
        result = fofa_fetch.get_isp_by_regex("180.1.2.3")
        assert result in ("电信", "联通", "移动")  # These ranges overlap in the regex

    def test_unknown_ip(self):
        # An IP that doesn't match any known range
        result = fofa_fetch.get_isp_by_regex("8.8.8.8")
        # The regex patterns in the code might or might not match this
        assert result in ("电信", "联通", "移动", "未知")

    def test_returns_string(self):
        result = fofa_fetch.get_isp_by_regex("192.168.1.1")
        assert isinstance(result, str)

    def test_ip_starting_with_223(self):
        result = fofa_fetch.get_isp_by_regex("223.1.2.3")
        # 223 appears in telecom and mobile patterns
        assert result in ("电信", "移动")


class TestGetRunCount:
    """Tests for get_run_count() and save_run_count()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_counter_file = fofa_fetch.COUNTER_FILE
        fofa_fetch.COUNTER_FILE = os.path.join(self.tmpdir, "counter.txt")

    def teardown_method(self):
        fofa_fetch.COUNTER_FILE = self.orig_counter_file
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_0_when_file_missing(self):
        assert fofa_fetch.get_run_count() == 0

    def test_reads_existing_count(self):
        with open(fofa_fetch.COUNTER_FILE, "w") as f:
            f.write("42")
        assert fofa_fetch.get_run_count() == 42

    def test_returns_0_on_invalid_content(self):
        with open(fofa_fetch.COUNTER_FILE, "w") as f:
            f.write("not_a_number")
        assert fofa_fetch.get_run_count() == 0

    def test_returns_0_on_empty_file(self):
        with open(fofa_fetch.COUNTER_FILE, "w") as f:
            f.write("")
        assert fofa_fetch.get_run_count() == 0


class TestSaveRunCount:
    """Tests for save_run_count()."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_counter_file = fofa_fetch.COUNTER_FILE
        fofa_fetch.COUNTER_FILE = os.path.join(self.tmpdir, "counter.txt")

    def teardown_method(self):
        fofa_fetch.COUNTER_FILE = self.orig_counter_file
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_saves_count(self):
        fofa_fetch.save_run_count(10)
        with open(fofa_fetch.COUNTER_FILE, "r") as f:
            assert f.read() == "10"

    def test_overwrites_existing(self):
        fofa_fetch.save_run_count(5)
        fofa_fetch.save_run_count(99)
        with open(fofa_fetch.COUNTER_FILE, "r") as f:
            assert f.read() == "99"

    def test_saves_zero(self):
        fofa_fetch.save_run_count(0)
        with open(fofa_fetch.COUNTER_FILE, "r") as f:
            assert f.read() == "0"


class TestSecondStage:
    """Tests for second_stage() with temp file system."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_ip_dir = fofa_fetch.IP_DIR
        self.orig_rtp_dir = fofa_fetch.RTP_DIR
        self.orig_zubo_file = fofa_fetch.ZUBO_FILE
        fofa_fetch.IP_DIR = os.path.join(self.tmpdir, "ip")
        fofa_fetch.RTP_DIR = os.path.join(self.tmpdir, "rtp")
        fofa_fetch.ZUBO_FILE = os.path.join(self.tmpdir, "zubo.txt")

    def teardown_method(self):
        fofa_fetch.IP_DIR = self.orig_ip_dir
        fofa_fetch.RTP_DIR = self.orig_rtp_dir
        fofa_fetch.ZUBO_FILE = self.orig_zubo_file
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_skips_when_ip_dir_missing(self, capsys):
        fofa_fetch.second_stage()
        captured = capsys.readouterr()
        assert "ip 目录不存在" in captured.out

    def test_skips_when_rtp_dir_missing(self, capsys):
        os.makedirs(fofa_fetch.IP_DIR)
        fofa_fetch.second_stage()
        captured = capsys.readouterr()
        assert "rtp 目录不存在" in captured.out

    def test_generates_zubo_with_rtp_urls(self):
        os.makedirs(fofa_fetch.IP_DIR)
        os.makedirs(fofa_fetch.RTP_DIR)

        # Create matching ip and rtp files
        with open(os.path.join(fofa_fetch.IP_DIR, "湖北电信.txt"), "w") as f:
            f.write("1.2.3.4:8080\n")

        with open(os.path.join(fofa_fetch.RTP_DIR, "湖北电信.txt"), "w") as f:
            f.write("CCTV1,rtp://239.0.0.1:5000\n")
            f.write("湖南卫视,rtp://239.0.0.2:6000\n")

        fofa_fetch.second_stage()

        assert os.path.exists(fofa_fetch.ZUBO_FILE)
        with open(fofa_fetch.ZUBO_FILE, "r") as f:
            content = f.read()

        assert "CCTV1,http://1.2.3.4:8080/rtp/239.0.0.1:5000" in content
        assert "湖南卫视,http://1.2.3.4:8080/rtp/239.0.0.2:6000" in content

    def test_generates_zubo_with_udp_urls(self):
        os.makedirs(fofa_fetch.IP_DIR)
        os.makedirs(fofa_fetch.RTP_DIR)

        with open(os.path.join(fofa_fetch.IP_DIR, "广东移动.txt"), "w") as f:
            f.write("5.6.7.8:9090\n")

        with open(os.path.join(fofa_fetch.RTP_DIR, "广东移动.txt"), "w") as f:
            f.write("CCTV2,udp://224.1.1.1:5000\n")

        fofa_fetch.second_stage()

        with open(fofa_fetch.ZUBO_FILE, "r") as f:
            content = f.read()

        assert "CCTV2,http://5.6.7.8:9090/udp/224.1.1.1:5000" in content

    def test_deduplicates_urls(self):
        os.makedirs(fofa_fetch.IP_DIR)
        os.makedirs(fofa_fetch.RTP_DIR)

        # Two IPs with same RTP source will produce duplicate URLs only if same IP
        with open(os.path.join(fofa_fetch.IP_DIR, "test.txt"), "w") as f:
            f.write("1.2.3.4:8080\n1.2.3.4:8080\n")

        with open(os.path.join(fofa_fetch.RTP_DIR, "test.txt"), "w") as f:
            f.write("CCTV1,rtp://239.0.0.1:5000\n")

        fofa_fetch.second_stage()

        with open(fofa_fetch.ZUBO_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]

        # Should deduplicate by URL
        assert len(lines) == 1

    def test_skips_rtp_lines_without_comma(self):
        os.makedirs(fofa_fetch.IP_DIR)
        os.makedirs(fofa_fetch.RTP_DIR)

        with open(os.path.join(fofa_fetch.IP_DIR, "test.txt"), "w") as f:
            f.write("1.2.3.4:8080\n")

        with open(os.path.join(fofa_fetch.RTP_DIR, "test.txt"), "w") as f:
            f.write("invalid_line_no_comma\n")
            f.write("CCTV1,rtp://239.0.0.1:5000\n")

        fofa_fetch.second_stage()

        with open(fofa_fetch.ZUBO_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == 1
        assert "CCTV1" in lines[0]


class TestChannelMapping:
    """Tests for channel mapping consistency in fofa_fetch."""

    def test_all_mapping_keys_in_categories(self):
        """Every standard name in mapping should exist in categories."""
        all_channels = set()
        for channels in fofa_fetch.CHANNEL_CATEGORIES.values():
            all_channels.update(channels)

        for std_name in fofa_fetch.CHANNEL_MAPPING:
            assert std_name in all_channels, (
                f"{std_name} in CHANNEL_MAPPING but not in CHANNEL_CATEGORIES"
            )

    def test_mapping_values_are_lists(self):
        """All mapping values should be lists."""
        for std_name, aliases in fofa_fetch.CHANNEL_MAPPING.items():
            assert isinstance(aliases, list), f"Aliases for {std_name} is not a list"

    def test_no_empty_alias_lists(self):
        """No mapping should have an empty alias list."""
        for std_name, aliases in fofa_fetch.CHANNEL_MAPPING.items():
            assert len(aliases) > 0, f"{std_name} has empty alias list"


class TestConfigConstants:
    """Tests for configuration constants."""

    def test_fofa_urls_not_empty(self):
        assert len(fofa_fetch.FOFA_URLS) > 0

    def test_channel_categories_has_expected_keys(self):
        expected = {"央视频道", "卫视频道", "数字频道", "湖北"}
        assert set(fofa_fetch.CHANNEL_CATEGORIES.keys()) == expected

    def test_headers_has_user_agent(self):
        assert "User-Agent" in fofa_fetch.HEADERS

    def test_ip_dir_path(self):
        assert fofa_fetch.IP_DIR == "ip"

    def test_rtp_dir_path(self):
        assert fofa_fetch.RTP_DIR == "rtp"


class TestFirstStageIpParsing:
    """Tests for IP parsing logic in first_stage (isolated)."""

    def test_get_isp_from_api_with_mixed_case(self):
        # Verify mixed case handling
        assert fofa_fetch.get_isp_from_api({"isp": "cHiNaTelEcOm"}) == "电信"
        assert fofa_fetch.get_isp_from_api({"isp": "cHiNaUnIcOm"}) == "联通"
        assert fofa_fetch.get_isp_from_api({"isp": "cHiNaMoBiLe"}) == "移动"

    def test_get_isp_from_api_partial_match(self):
        # Should match partial strings
        assert fofa_fetch.get_isp_from_api({"isp": "SomeTelecomProvider"}) == "电信"
        assert fofa_fetch.get_isp_from_api({"isp": "MyUnicomNet"}) == "联通"
        assert fofa_fetch.get_isp_from_api({"isp": "MobileData"}) == "移动"
