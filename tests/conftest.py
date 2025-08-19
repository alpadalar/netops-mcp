"""
Pytest configuration and fixtures for DevOps MCP tests.
"""

import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netops_mcp.tools.base import DevOpsTool
from netops_mcp.tools.network.http_tools import HTTPTools
from netops_mcp.tools.network.connectivity_tools import ConnectivityTools
from netops_mcp.tools.network.dns_tools import DNSTools
from netops_mcp.tools.network.discovery_tools import DiscoveryTools
from netops_mcp.tools.system.network_tools import NetworkTools
from netops_mcp.tools.system.monitoring_tools import MonitoringTools
from netops_mcp.tools.security.scanning_tools import ScanningTools


@pytest.fixture
def mock_execute_command():
    """Mock _execute_command method for testing."""
    with patch.object(DevOpsTool, '_execute_command') as mock:
        yield mock


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing."""
    with patch('subprocess.run') as mock:
        yield mock


@pytest.fixture
def mock_shutil_which():
    """Mock shutil.which for testing."""
    with patch('shutil.which') as mock:
        yield mock


@pytest.fixture
def mock_psutil():
    """Mock psutil for testing."""
    with patch('psutil.cpu_percent') as mock_cpu, \
         patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.process_iter') as mock_processes:
        
        # Setup default mock returns
        mock_cpu.return_value = 25.5
        mock_memory.return_value = MagicMock(
            total=8589934592,  # 8GB
            available=4294967296,  # 4GB
            used=4294967296,  # 4GB
            percent=50.0
        )
        mock_disk.return_value = MagicMock(
            total=107374182400,  # 100GB
            used=53687091200,  # 50GB
            free=53687091200  # 50GB
        )
        mock_processes.return_value = []
        
        yield {
            'cpu': mock_cpu,
            'memory': mock_memory,
            'disk': mock_disk,
            'processes': mock_processes
        }


@pytest.fixture
def sample_curl_output():
    """Sample curl command output."""
    return {
        "success": True,
        "stdout": """{
  "http_code": "200",
  "time_total": "0.123",
  "time_connect": "0.045",
  "time_namelookup": "0.023",
  "size_download": "1234",
  "speed_download": "10000"
}""",
        "stderr": "",
        "return_code": 0,
        "command": "curl -s -w @- -o /tmp/curl_output -X GET https://example.com"
    }


@pytest.fixture
def sample_ping_output():
    """Sample ping command output."""
    return {
        "success": True,
        "stdout": """PING google.com (142.250.185.78) 56(84) bytes of data.
64 bytes from google.com (142.250.185.78): icmp_seq=1 time=1.23 ms
64 bytes from google.com (142.250.185.78): icmp_seq=2 time=1.45 ms
64 bytes from google.com (142.250.185.78): icmp_seq=3 time=1.34 ms
64 bytes from google.com (142.250.185.78): icmp_seq=4 time=1.56 ms

--- google.com ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3003ms
rtt min/avg/max/mdev = 1.230/1.395/1.560/0.134 ms""",
        "stderr": "",
        "return_code": 0,
        "command": "ping -c 4 -W 10 google.com"
    }


@pytest.fixture
def sample_traceroute_output():
    """Sample traceroute command output."""
    return {
        "success": True,
        "stdout": """traceroute to google.com (142.250.185.78), 30 hops max, 60 byte packets
 1  _gateway (192.168.1.1)  1.234 ms  0.987 ms  1.123 ms
 2  10.0.0.1 (10.0.0.1)  5.678 ms  5.432 ms  5.567 ms
 3  172.16.0.1 (172.16.0.1)  10.123 ms  9.876 ms  10.234 ms
 4  * * *
 5  google.com (142.250.185.78)  15.678 ms  15.432 ms  15.567 ms""",
        "stderr": "",
        "return_code": 0,
        "command": "traceroute google.com"
    }


@pytest.fixture
def sample_mtr_output():
    """Sample mtr command output."""
    return {
        "success": True,
        "stdout": """Start: 2025-08-19T15:06:45+0000
HOST: test-host                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1.|-- _gateway                0.0%     3    1.2   1.1   0.9   1.3   0.2
  2.|-- 10.0.0.1                0.0%     3    5.4   5.3   5.1   5.6   0.3
  3.|-- 172.16.0.1              0.0%     3   10.1  10.2   9.8  10.5   0.4
  4.|-- google.com              0.0%     3   15.3  15.4  15.1  15.7   0.3""",
        "stderr": "",
        "return_code": 0,
        "command": "mtr -c 3 --report google.com"
    }


@pytest.fixture
def sample_nslookup_output():
    """Sample nslookup command output."""
    return {
        "success": True,
        "stdout": """Server:         8.8.8.8
Address:        8.8.8.8#53

Non-authoritative answer:
Name:   google.com
Address: 142.250.185.78
Name:   google.com
Address: 2607:f8b0:4004:c0c::65""",
        "stderr": "",
        "return_code": 0,
        "command": "nslookup -type=A google.com"
    }


@pytest.fixture
def sample_dig_output():
    """Sample dig command output."""
    return {
        "success": True,
        "stdout": """; <<>> DiG 9.16.1-Ubuntu <<>> google.com A
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; QUESTION SECTION:
;google.com.                    IN      A

;; ANSWER SECTION:
google.com.             300     IN      A       142.250.185.78

;; Query time: 5 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; WHEN: Mon Aug 19 15:06:45 UTC 2025
;; MSG SIZE  rcvd: 55""",
        "stderr": "",
        "return_code": 0,
        "command": "dig google.com A"
    }


@pytest.fixture
def sample_nmap_output():
    """Sample nmap command output."""
    return {
        "success": True,
        "stdout": """Starting Nmap 7.80 ( https://nmap.org ) at 2025-08-19 15:06 UTC
Nmap scan report for scanme.nmap.org (45.33.32.156)
Host is up (0.087s latency).
Not shown: 995 closed ports
PORT      STATE SERVICE
22/tcp    open  ssh
80/tcp    open  http
9929/tcp  open  nping-echo
31337/tcp open  Elite

Nmap done: 1 IP address (1 host up) scanned in 2.34 seconds""",
        "stderr": "",
        "return_code": 0,
        "command": "nmap -sS -p 1-1000 scanme.nmap.org"
    }


@pytest.fixture
def sample_ss_output():
    """Sample ss command output."""
    return {
        "success": True,
        "stdout": """State      Recv-Q Send-Q Local Address:Port               Peer Address:Port
LISTEN     0      128     *:22                  *:*
LISTEN     0      128     *:80                  *:*
LISTEN     0      128     *:443                 *:*
ESTAB      0      0       192.168.1.100:12345    8.8.8.8:53""",
        "stderr": "",
        "return_code": 0,
        "command": "ss -tuln"
    }


@pytest.fixture
def sample_netstat_output():
    """Sample netstat command output."""
    return {
        "success": True,
        "stdout": """Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:443             0.0.0.0:*               LISTEN""",
        "stderr": "",
        "return_code": 0,
        "command": "netstat -tuln"
    }


@pytest.fixture
def sample_arp_output():
    """Sample arp command output."""
    return {
        "success": True,
        "stdout": """Address                  HWtype  HWaddress           Flags Mask            Iface
192.168.1.1              ether   00:11:22:33:44:55     C                     eth0
192.168.1.100            ether   aa:bb:cc:dd:ee:ff     C                     eth0""",
        "stderr": "",
        "return_code": 0,
        "command": "arp -a"
    }


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# Test data fixtures
@pytest.fixture
def valid_hosts():
    """List of valid hostnames/IPs for testing."""
    return [
        "google.com",
        "192.168.1.1",
        "10.0.0.1",
        "localhost",
        "127.0.0.1",
        "::1",
        "example.com"
    ]


@pytest.fixture
def invalid_hosts():
    """List of invalid hostnames for testing."""
    return [
        "",
        None,
        "invalid..host",
        "256.256.256.256",
        "192.168.1.256",
        "host with spaces",
        "host@invalid"
    ]


@pytest.fixture
def valid_ports():
    """List of valid ports for testing."""
    return [80, 443, 8080, 22, 53, 3306, 5432, "80", "443"]


@pytest.fixture
def invalid_ports():
    """List of invalid ports for testing."""
    return [0, 70000, -1, "invalid", "abc", 65536]


@pytest.fixture
def test_urls():
    """List of test URLs for HTTP testing."""
    return [
        "https://httpbin.org/get",
        "https://httpbin.org/post",
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404",
        "https://httpbin.org/delay/1"
    ]
