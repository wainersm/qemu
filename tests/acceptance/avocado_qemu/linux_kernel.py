"""
Helpers for boot Linux kernel tests.
"""
#
# Copyright (c) 2019 Red Hat, Inc.
#
# Author:
#  Cleber Rosa <crosa@redhat.com>
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

import os
import logging

from avocado.utils import process
from avocado.utils import archive

from . import Test


class BootKernelTest(Test):
    """
    Base class for tests that require Linux kernel boot.
    """
    kernel_path = None

    KERNELS = {
        'fedora18_x86_64': {
            'url': 'https://archives.fedoraproject.org/pub/archive/fedora/'
                   'linux/releases/18/Fedora/x86_64/os/images/pxeboot/vmlinuz',
            'md5': '41464f68efe42b9991250bed86c7081d2ccdbb21'},
        'fedora29_x86_64': {
            'url': 'https://download.fedoraproject.org/pub/fedora/linux/'
                   'releases/29/Everything/x86_64/os/images/pxeboot/vmlinuz',
            'md5': '23bebd2680757891cf7adedb033532163a792495'},
        'fedora29_aarch64': {
            'url': 'https://download.fedoraproject.org/pub/fedora/linux/'
                   'releases/29/Everything/aarch64/os/images/vmlinuz',
            'md5': '8c73e469fc6ea06a58dc83a628fc695b693b8493'},
        'fedora29_armhfp': {
            'url': 'https://download.fedoraproject.org/pub/fedora/linux/'
                   'releases/29/Everything/armhfp/os/images/pxeboot/vmlinuz',
            'md5': 'e9826d741b4fb04cadba8d4824d1ed3b7fb8b4d4'},
        'fedora29_s390x': {
            'url': 'https://download.fedoraproject.org/pub/fedora-secondary/'
                   'releases/29/Everything/s390x/os/images/kernel.img',
            'md5': 'e8e8439103ef8053418ef062644ffd46a7919313'},
        'fedora29_ppc64le': {
            'url': 'https://download.fedoraproject.org/pub/fedora-secondary/'
                   'releases/29/Everything/ppc64le/os/ppc/ppc64/vmlinuz',
            'md5': '3fe04abfc852b66653b8c3c897a59a689270bc77'},
        'debian_malta_mips': {
            'url': 'http://snapshot.debian.org/archive/debian/20130217T032700Z/'
                   'pool/main/l/linux-2.6/linux-image-2.6.32-5-4kc-malta'
                   '_2.6.32-48_mips.deb',
            'md5': 'a8cfc28ad8f45f54811fc6cf74fc43ffcfe0ba04',
            'extract': {'type': 'deb',
                        'file_path': '/boot/vmlinux-2.6.32-5-4kc-malta'}},
        'debian_malta_mipsel': {
            'url': 'http://snapshot.debian.org/archive/debian/20130217T032700Z/'
                   'pool/main/l/linux-2.6/linux-image-2.6.32-5-5kc-malta'
                   '_2.6.32-48_mipsel.deb',
            'md5': '1aaec92083bf22fda31e0d27fa8d9a388e5fc3d5',
            'extract': {'type': 'deb',
                        'file_path': '/boot/vmlinux-2.6.32-5-5kc-malta'}},
        'debian5_alpha': {
            'url': 'http://archive.debian.org/debian/dists/lenny/main/'
                   'installer-alpha/current/images/cdrom/vmlinuz',
            'md5': '3a943149335529e2ed3e74d0d787b85fb5671ba3',
            'extract': {'type': 'tarball'}},
        }

    def boot_kernel(self, name, console="ttyS0", cmd_line="printk.time=0"):
        """
        Boots a Linux Kernel.

        :param name: kernel name as in KERNELS keys.
        :type name: str
        :param console: console device. if set to None then console is not
                        configured. Default is ttyS0.
        :type console: str
        :param cmd_line: base kernel command line. Default is printk.time=0.
        :type cmd_line: list
        """
        self.prepare_kernel(name)
        if cmd_line:
            kernel_cmd_line = list(cmd_line)
        else:
            kernel_cmd_line = []
        if console:
            self.vm.set_console()
            kernel_cmd_line.append("console=%s" % console)
        self.vm.add_args('-kernel', self.kernel_path,
                         '-append', " ".join(kernel_cmd_line))
        self.vm.launch()
        return " ".join(kernel_cmd_line)

    def prepare_kernel(self, name):
        """
        Fetches the kernel (if not cached already) file and extract the binary
        in case it is packaged in a tarball or distro package format.

        :param name: kernel name as in KERNELS keys.
        :type name: str
        """
        kernel = self.KERNELS.get(name, None)
        if kernel is None:
            raise Exception("Unable to find %s kernel" % kernel)
        asset_path = self.fetch_asset(kernel['url'], asset_hash=kernel['md5'])
        extt = kernel.get("extract", None)
        if extt:
            if extt["type"] == "deb":
                self.kernel_path = self.extract_from_deb(asset_path,
                                                         extt["file_path"])
            elif extt["type"] in ["zip", "tarball"]:
                self.kernel_path = archive.uncompress(asset_path, self.workdir)
        else:
            self.kernel_path = asset_path

    def extract_from_deb(self, deb, path):
        """
        Extracts a file from a deb package into the test workdir

        :param deb: path to the deb archive
        :param file: path within the deb archive of the file to be extracted
        :returns: path of the extracted file
        """
        cwd = os.getcwd()
        os.chdir(self.workdir)
        process.run("ar x %s data.tar.gz" % deb)
        archive.extract("data.tar.gz", self.workdir)
        os.chdir(cwd)
        return self.workdir + path

    def wait_for_console_pattern(self, success_message,
                                 failure_message='Kernel panic - not syncing'):
        """
        Waits for messages to appear on the console, while logging the content

        :param success_message: if this message appears, test succeeds
        :param failure_message: if this message appears, test fails
        """
        console = self.vm.console_socket.makefile()
        console_logger = logging.getLogger('console')
        while True:
            msg = console.readline()
            console_logger.debug(msg.strip())
            if success_message in msg:
                break
            if failure_message in msg:
                fail = 'Failure message found in console: %s' % failure_message
                self.fail(fail)
