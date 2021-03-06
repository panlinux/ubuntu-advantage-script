"""Tests related to uaclient.util module."""


import mock
import os

from uaclient.testing.helpers import TestCase
from uaclient import util

PRIVACY_POLICY_URL = (
    "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
)

OS_RELEASE_DISCO = """\
NAME="Ubuntu"
VERSION="19.04 (Disco Dingo)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu Disco Dingo (development branch)"
VERSION_ID="19.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="%s"
VERSION_CODENAME=disco
UBUNTU_CODENAME=disco
""" % (PRIVACY_POLICY_URL)

OS_RELEASE_BIONIC = """\
NAME="Ubuntu"
VERSION="18.04.1 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.1 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="%s"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
""" % (PRIVACY_POLICY_URL)

OS_RELEASE_XENIAL = """\
NAME="Ubuntu"
VERSION="16.04.5 LTS (Xenial Xerus)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 16.04.5 LTS"
VERSION_ID="16.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
VERSION_CODENAME=xenial
UBUNTU_CODENAME=xenial
"""

OS_RELEASE_TRUSTY = """\
NAME="Ubuntu"
VERSION="14.04.5 LTS, Trusty Tahr"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 14.04.5 LTS"
VERSION_ID="14.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
"""


class TestParseOSRelease(TestCase):

    def test_parse_os_release(self):
        """parse_os_release returns a dict of values from /etc/os-release."""
        tdir = self.tmp_dir()
        release_file = os.path.join(tdir, 'os-release')
        util.write_file(release_file, OS_RELEASE_TRUSTY)
        expected = {'BUG_REPORT_URL': 'http://bugs.launchpad.net/ubuntu/',
                    'HOME_URL': 'http://www.ubuntu.com/',
                    'ID': 'ubuntu', 'ID_LIKE': 'debian',
                    'NAME': 'Ubuntu', 'PRETTY_NAME': 'Ubuntu 14.04.5 LTS',
                    'SUPPORT_URL': 'http://help.ubuntu.com/',
                    'VERSION': '14.04.5 LTS, Trusty Tahr',
                    'VERSION_ID': '14.04'}
        self.assertEqual(expected, util.parse_os_release(release_file))


class TestGetPlatformInfo(TestCase):

    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.parse_os_release')
    def test_get_platform_info_error_no_version(self, m_parse, m_subp):
        """get_platform_info errors when it cannot parse os-release."""
        m_parse.return_value = {'VERSION': 'junk'}
        with self.assertRaises(RuntimeError) as ctx_mgr:
            util.get_platform_info()
        self.assertEqual(
            'Could not parse /etc/os-release VERSION: junk',
            str(ctx_mgr.exception))

    def test_get_platform_info_trusty(self):
        """get_platform_info handles trusty /etc/os-release parsing."""
        tdir = self.tmp_dir()
        release_file = os.path.join(tdir, 'os-release')
        util.write_file(release_file, OS_RELEASE_TRUSTY)
        parse_dict = util.parse_os_release(release_file)

        def fake_subp(cmd):
            if cmd == ['uname', '-r']:
                return 'kernel-ver', ''
            if cmd == ['uname', '-i']:
                return 'arm64', ''
            assert False, 'Unexpected command: %s' % cmd

        expected = {'arch': 'arm64', 'distribution': 'Ubuntu',
                    'kernel': 'kernel-ver', 'release': '14.04',
                    'series': 'trusty', 'type': 'Linux'}
        with mock.patch('uaclient.util.parse_os_release') as m_parse:
            with mock.patch('uaclient.util.subp') as m_subp:
                m_parse.return_value = parse_dict
                m_subp.side_effect = fake_subp
                self.assertEqual(expected, util.get_platform_info())

    def test_get_platform_info_xenial(self):
        """get_platform_info handles xenial /etc/os-release parsing."""
        tdir = self.tmp_dir()
        release_file = os.path.join(tdir, 'os-release')
        util.write_file(release_file, OS_RELEASE_XENIAL)
        parse_dict = util.parse_os_release(release_file)

        def fake_subp(cmd):
            if cmd == ['uname', '-r']:
                return 'kernel-ver', ''
            if cmd == ['uname', '-i']:
                return 'arm64', ''
            assert False, 'Unexpected command: %s' % cmd

        expected = {'arch': 'arm64', 'distribution': 'Ubuntu',
                    'kernel': 'kernel-ver', 'release': '16.04',
                    'series': 'xenial', 'type': 'Linux'}
        with mock.patch('uaclient.util.parse_os_release') as m_parse:
            with mock.patch('uaclient.util.subp') as m_subp:
                m_parse.return_value = parse_dict
                m_subp.side_effect = fake_subp
                self.assertEqual(expected, util.get_platform_info())

    def test_get_platform_info_bionic(self):
        """get_platform_info handles bionic /etc/os-release parsing."""
        tdir = self.tmp_dir()
        release_file = os.path.join(tdir, 'os-release')
        util.write_file(release_file, OS_RELEASE_BIONIC)
        parse_dict = util.parse_os_release(release_file)

        def fake_subp(cmd):
            if cmd == ['uname', '-r']:
                return 'kernel-ver', ''
            if cmd == ['uname', '-i']:
                return 'arm64', ''
            assert False, 'Unexpected command: %s' % cmd

        expected = {'arch': 'arm64', 'distribution': 'Ubuntu',
                    'kernel': 'kernel-ver', 'release': '18.04',
                    'series': 'bionic', 'type': 'Linux'}
        with mock.patch('uaclient.util.parse_os_release') as m_parse:
            with mock.patch('uaclient.util.subp') as m_subp:
                m_parse.return_value = parse_dict
                m_subp.side_effect = fake_subp
                self.assertEqual(expected, util.get_platform_info())

    def test_get_platform_info_disco(self):
        """get_platform_info handles disco /etc/os-release parsing."""
        tdir = self.tmp_dir()
        release_file = os.path.join(tdir, 'os-release')
        util.write_file(release_file, OS_RELEASE_DISCO)
        parse_dict = util.parse_os_release(release_file)

        def fake_subp(cmd):
            if cmd == ['uname', '-r']:
                return 'kernel-ver', ''
            if cmd == ['uname', '-i']:
                return 'arm64', ''
            assert False, 'Unexpected command: %s' % cmd

        expected = {'arch': 'arm64', 'distribution': 'Ubuntu',
                    'kernel': 'kernel-ver', 'release': '19.04',
                    'series': 'disco', 'type': 'Linux'}
        with mock.patch('uaclient.util.parse_os_release') as m_parse:
            with mock.patch('uaclient.util.subp') as m_subp:
                m_parse.return_value = parse_dict
                m_subp.side_effect = fake_subp
                self.assertEqual(expected, util.get_platform_info())


class TestGetMachineId(TestCase):

    def setUp(self):
        super().setUp()
        self.tdir = self.tmp_dir()

    def test_get_machine_id_from_etc_machine_id(self):
        """Presence of /etc/machine-id is returned if it exists."""
        etc_machine_id = self.tmp_path('etc-machine-id', dir=self.tdir)
        self.assertEqual('/etc/machine-id', util.ETC_MACHINE_ID)
        util.write_file(etc_machine_id, 'etc-machine-id')
        with mock.patch('uaclient.util.ETC_MACHINE_ID', etc_machine_id):
            value = util.get_machine_id(data_dir=None)
        self.assertEqual('etc-machine-id', value)

    def test_get_machine_id_from_var_lib_dbus_machine_id(self):
        """On trusty, machine id lives in of /var/lib/dbus/machine-id."""
        etc_machine_id = self.tmp_path('etc-machine-id', dir=self.tdir)
        dbus_machine_id = self.tmp_path('dbus-machine-id', dir=self.tdir)
        self.assertEqual('/var/lib/dbus/machine-id', util.DBUS_MACHINE_ID)
        util.write_file(dbus_machine_id, 'dbus-machine-id')
        with mock.patch('uaclient.util.DBUS_MACHINE_ID', dbus_machine_id):
            with mock.patch('uaclient.util.ETC_MACHINE_ID', etc_machine_id):
                value = util.get_machine_id(data_dir=None)
        self.assertEqual('dbus-machine-id', value)

    def test_get_machine_id_uses_machine_id_from_data_dir(self):
        """When no machine-id is found, use machine-id from data_dir."""

        data_machine_id = self.tmp_path('machine-id', dir=self.tdir)
        util.write_file(data_machine_id, 'data-machine-id')

        def fake_exists(path):
            return bool(path == data_machine_id)

        with mock.patch('uaclient.util.os.path.exists') as m_exists:
            m_exists.side_effect = fake_exists
            value = util.get_machine_id(data_dir=self.tdir)
        self.assertEqual('data-machine-id', value)

    def test_get_machine_id_create_machine_id_in_data_dir(self):
        """When no machine-id is found, create one in data_dir using uuid4."""

        data_machine_id = self.tmp_path('machine-id', dir=self.tdir)

        with mock.patch('uaclient.util.os.path.exists') as m_exists:
            with mock.patch('uaclient.util.uuid.uuid4') as m_uuid4:
                m_exists.return_value = False
                m_uuid4.return_value = '1234...1234'
                value = util.get_machine_id(data_dir=self.tdir)
        self.assertEqual('1234...1234', value)
        self.assertEqual('1234...1234', util.load_file(data_machine_id))
