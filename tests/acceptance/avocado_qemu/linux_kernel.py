"""
Helpers for boot Linux kernel tests.
"""
#
# Copyright (c) 2019 Red Hat, Inc.
#
# Author:
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

import abc
import os
import logging
import tempfile

from avocado.utils import process
from avocado.utils import asset
from avocado.utils import archive

from . import Test


class KernelProviderBase(abc.ABC):
    """
    Implements the interface for Kernel providers that should inherit from
    this class.
    """

    def get(self, version, arch=None, checksums=(None, None), cache_dir=None):
        """
        Gets the kernel and initrd files.

        :param version: the kernel version (usually a release version if
                                            provider for distro kernels).
        :param arch: the kernel architecture. Default is the host OS arch.
        :param checksums: a tuple of checksum for checking the kernel and initrd
                         files integrity, respectively.
        :param cache_dir: the cache directory where to store the files. Default
                          is the OS temporary directory.
        :returns: a kernel object.
        """

        if cache_dir is None:
            cache_dir = tempfile.gettempdir()

        if arch is None:
            arch = os.uname()[4]

        return self.get_impl(version, arch, cache_dir, checksums)

    @abc.abstractmethod
    def get_impl(self, version, arch, cache_dir, checksums):
        """
        Providers should implement this.
        """
        pass

def get_provider(name):
    """
    Gets the provider instance.

    :param name: the provider name (case-insensitive).
    :returns: the provider instance, or None if not found.
    """
    _name = name.lower()
    for provider in list_providers():
        if _name == provider.name.lower():
            return provider()
    return None

def list_providers():
    """
    Lists the providers.

    :returns: a list of providers (classes)
    """
    return list(set(_ for _ in globals().values()
        if (isinstance(_, type) and
            issubclass(_, KernelProviderBase) and
            hasattr(_, 'name'))))

class FedoraKernelProvider(KernelProviderBase):
    """
    Implements a provider for Fedora Kernels.
    """

    name = 'Fedora'
    edition = 'Everything'

    def get_impl(self, version, arch, cache_dir, checksums):
        base_url = ('https://archives.fedoraproject.org/pub/archive/fedora/'
                    'linux/releases/{version}/{edition}/{arch}/os/images/'
                    'pxeboot')
        kernel_base_url = base_url + '/vmlinuz'
        initrd_base_url = base_url + '/initrd.img'

        if arch in ('x86_64', 'armhfp') and int(version) < 21:
            base_url = ('https://archives.fedoraproject.org/pub/archive/fedora/'
                        'linux/releases/{version}/Fedora/{arch}/os/images/'
                        'pxeboot').format(version=version, arch=arch)
            kernel_url = base_url + '/vmlinuz'
            initrd_url = base_url + '/initrd.img'
        elif arch in ('ppc64', 'ppc64le'):
            # Fedora > 27
            base_url = ('https://download.fedoraproject.org/pub/'
                        'fedora-secondary/releases/{version}/{edition}/{arch}/'
                        'os/ppc/ppc64').format(version=version, arch=arch,
                                               edition=self.edition)
            kernel_url = base_url + '/vmlinuz'
            initrd_url = base_url + '/initrd.img'
        elif arch is 's390x':
            base_url = ('https://download.fedoraproject.org/pub/'
                        'fedora-secondary/releases/{version}/{edition}/{arch}/'
                        'os/images').format(version=version, arch=arch,
                                            edition=self.edition)
            kernel_url = base_url + '/kernel.img'
            initrd_url = base_url + '/initrd.img'
        else:
            base_url = ('https://archives.fedoraproject.org/pub/archive/fedora/'
                        'linux/releases/{version}/{edition}/{arch}/os/images/'
                        'pxeboot').format(version=version, arch=arch,
                                          edition=self.edition)
            kernel_url = base_url + '/vmlinuz'
            initrd_url = base_url + '/initrd.img'

        initrd_path = asset.Asset(name="initrd-%s-%s-%s" % (self.name, version,
                                                            arch),
                                  asset_hash=checksums[1],
                                  locations=[initrd_url],
                                  cache_dirs=[cache_dir],
                                  algorithm=None,
                                  expire=None).fetch()

        kernel_path = asset.Asset(name="vmlinuz-%s-%s-%s" % (self.name, version,
                                                             arch),
                                  asset_hash=checksums[0],
                                  locations=[kernel_url],
                                  cache_dirs=[cache_dir],
                                  algorithm=None,
                                  expire=None).fetch()
        return Kernel(kernel_path, checksums[0],
                      Initrd(initrd_path, checksums[1]))

class DebianKernelProvider(KernelProviderBase):
    """
    Implements a provider for Debian kernels.
    """
    name = 'Debian'

    def get_impl(self, version, arch, cache_dir, checksums):
        if arch == 'x86_64':
            arch = 'amd64'
        elif arch == 'aarch64':
            arch = 'arm64'

        # Supports version >= 'lenny'
        version = version.lower()
        if version in ('lenny', 'squeeze', 'wheezy', 'jessie'):
            base_url = ('http://archive.debian.org/debian/dists/{version}/main/'
                        'installer-{arch}/current/images/cdrom').format(
                                arch=arch, version=version)
        else:
            base_url = ('http://ftp.debian.org/debian/dists/{version}/main/'
                        'installer-{arch}/current/images/cdrom').format(
                                arch=arch, version=version)

        initrd_url = base_url + "/initrd.gz"
        initrd_path = asset.Asset(name="initrd-%s-%s-%s" % (self.name, version,
                                                            arch),
                                  asset_hash=checksums[1],
                                  locations=[initrd_url],
                                  cache_dirs=[cache_dir],
                                  algorithm=None,
                                  expire=None).fetch()

        kernel_url =  base_url + "/vmlinuz"
        kernel_path = asset.Asset(name="vmlinuz-%s-%s-%s" % (self.name, version,
                                                             arch),
                                  asset_hash=checksums[0],
                                  locations=[kernel_url],
                                  cache_dirs=[cache_dir],
                                  algorithm=None,
                                  expire=None).fetch()

        if archive.is_archive(kernel_path):
            dest = os.path.join(os.path.dirname(kernel_path), 'uncompressed')
            os.makedirs(dest, exist_ok=True)
            kernel_path = archive.uncompress(kernel_path, dest)

        return Kernel(kernel_path, checksums[0],
                      Initrd(initrd_path, checksums[1]))

    def extract_from_deb(self, deb, path, dest):
        """
        Extracts a file from a deb package into the test workdir

        :param deb: path to the deb archive
        :param file: path within the deb archive of the file to be extracted
        :returns: path of the extracted file
        """
        cwd = os.getcwd()
        os.chdir(dest)
        process.run("ar x %s data.tar.gz" % deb)
        archive.extract("data.tar.gz", dest)
        os.chdir(cwd)
        return dest + path

class Kernel:
    """
    Represents a kernel file.
    """

    def __init__(self, path, checksum=None, initrd=None):
        self.path = path
        self.checksum = checksum
        self.initrd = initrd

class Initrd:
    """
    Represents a initrd file.
    """

    def __init__(self, path, checksum=None):
        self.path = path
        self.checksum = checksum

class BootKernelTest(Test):
    """
    Base class for tests that require Linux kernel boot.
    """
    kernel = None

    def fetch_kernel(self, provider_name, version, arch=None):
        """
        Fetches the kernel and initrd files.

        :param provider_name: name of the provider.
        :param version: the provider version (usually a distro release).
        :param version: kernel architecture (default is the host arch).
        """
        provider = get_provider(provider_name)
        if provider is None:
            raise Exception("Kernel provider (%s) not found." % provider_name)
        try:
            self.kernel = provider.get(version=version, arch=arch)
        except Exception as error:
            msg = ('Failed to fetch kernel (provider={}, version={},'
                   ' arch={}).').format(provider_name, version, arch)
            logging.getLogger('console').debug(msg)
            raise error

    def boot_kernel(self, provider_name, version, arch=None, console="ttyS0",
                    cmd_line="printk.time=0", use_initrd=False):
        """
        Fetches and boot a Linux Kernel.

        :param provider_name: the kernel provider name.
        :param version: provider version.
        :param arch: kernel architecture. Default is the host OS arch.
        :param console: console device. If set to None then console is not
                        configured. Default is 'ttyS0'.
        :param cmd_line: base kernel command line. Default is 'printk.time=0'.
        :param use_initrd: If should boot with an initrd. Default is False.
        :returns: the command line argumment used with '-append'.
        """
        self.fetch_kernel(provider_name, version, arch)

        if cmd_line:
            kernel_cmd_line = list(cmd_line)
        else:
            kernel_cmd_line = []

        if console:
            self.vm.set_console()
            kernel_cmd_line.append("console=%s" % console)

        self.vm.add_args('-kernel', self.kernel.path,
                         '-append', " ".join(kernel_cmd_line))
        if use_initrd:
            self.vm.add_args('-initrd', self.kernel.initrd.path, '-m', '512')

        self.vm.launch()
        return " ".join(kernel_cmd_line)

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
