# Functional test that boots a Linux kernel and checks the console
#
# Copyright (c) 2018 Red Hat, Inc.
#
# Author:
#  Cleber Rosa <crosa@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

import gzip

from avocado_qemu import linux_kernel


class BootLinuxConsole(linux_kernel.BootKernelTest):
    """
    Boots a Linux kernel and checks that the console is operational and the
    kernel command line is properly passed from QEMU to the kernel
    """

    timeout = 90

    def exec_command_and_wait_for_pattern(self, command, success_message):
        command += '\n'
        self.vm.console_socket.sendall(command.encode())
        self.wait_for_console_pattern(success_message)

    def test_x86_64_pc(self):
        """
        :avocado: tags=arch:x86_64
        :avocado: tags=machine:pc
        """
        self.vm.set_machine('pc')
        kernel_command_line = self.boot_kernel(provider_name='fedora',
                                               version='29', arch='x86_64')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_mips_malta(self):
        """
        :avocado: tags=arch:mips
        :avocado: tags=machine:malta
        :avocado: tags=endian:big
        """
        self.vm.set_machine('malta')
        kernel_command_line = self.boot_kernel('debian_malta_mips')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_mips64el_malta(self):
        """
        :avocado: tags=arch:mips64el
        :avocado: tags=machine:malta
        """
        self.vm.set_machine('malta')
        kernel_command_line = self.boot_kernel('debian_malta_mipsel')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_mips_malta_cpio(self):
        """
        :avocado: tags=arch:mips
        :avocado: tags=machine:malta
        :avocado: tags=endian:big
        """
        deb_url = ('http://snapshot.debian.org/archive/debian/'
                   '20160601T041800Z/pool/main/l/linux/'
                   'linux-image-4.5.0-2-4kc-malta_4.5.5-1_mips.deb')
        deb_hash = 'a3c84f3e88b54e06107d65a410d1d1e8e0f340f8'
        deb_path = self.fetch_asset(deb_url, asset_hash=deb_hash)
        kernel_path = self.extract_from_deb(deb_path,
                                            '/boot/vmlinux-4.5.0-2-4kc-malta')
        initrd_url = ('https://github.com/groeck/linux-build-test/raw/'
                      '8584a59ed9e5eb5ee7ca91f6d74bbb06619205b8/rootfs/'
                      'mips/rootfs.cpio.gz')
        initrd_hash = 'bf806e17009360a866bf537f6de66590de349a99'
        initrd_path_gz = self.fetch_asset(initrd_url, asset_hash=initrd_hash)
        initrd_path = self.workdir + "rootfs.cpio"

        with gzip.open(initrd_path_gz, 'rb') as f_in:
            with open(initrd_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        self.vm.set_machine('malta')
        self.vm.set_console()
        kernel_command_line = (self.KERNEL_COMMON_COMMAND_LINE
                               + 'console=ttyS0 console=tty '
                               + 'rdinit=/sbin/init noreboot')
        self.vm.add_args('-kernel', kernel_path,
                         '-initrd', initrd_path,
                         '-append', kernel_command_line,
                         '-no-reboot')
        self.vm.launch()
        self.wait_for_console_pattern('Boot successful.')

        self.exec_command_and_wait_for_pattern('cat /proc/cpuinfo',
                                               'BogoMIPS')
        self.exec_command_and_wait_for_pattern('uname -a',
                                               'Debian')
        self.exec_command_and_wait_for_pattern('reboot',
                                               'reboot: Restarting system')

    def do_test_mips_malta32el_nanomips(self, kernel_url, kernel_hash):
        kernel_path_xz = self.fetch_asset(kernel_url, asset_hash=kernel_hash)
        kernel_path = self.workdir + "kernel"
        with lzma.open(kernel_path_xz, 'rb') as f_in:
            with open(kernel_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        self.vm.set_machine('malta')
        self.vm.set_console()
        kernel_command_line = (self.KERNEL_COMMON_COMMAND_LINE
                               + 'mem=256m@@0x0 '
                               + 'console=ttyS0')
        self.vm.add_args('-no-reboot',
                         '-cpu', 'I7200',
                         '-kernel', kernel_path,
                         '-append', kernel_command_line)
        self.vm.launch()
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_mips_malta32el_nanomips_4k(self):
        """
        :avocado: tags=arch:mipsel
        :avocado: tags=machine:malta
        :avocado: tags=endian:little
        """
        kernel_url = ('https://mipsdistros.mips.com/LinuxDistro/nanomips/'
                      'kernels/v4.15.18-432-gb2eb9a8b07a1-20180627102142/'
                      'generic_nano32r6el_page4k.xz')
        kernel_hash = '477456aafd2a0f1ddc9482727f20fe9575565dd6'
        self.do_test_mips_malta32el_nanomips(kernel_url, kernel_hash)

    def test_mips_malta32el_nanomips_16k_up(self):
        """
        :avocado: tags=arch:mipsel
        :avocado: tags=machine:malta
        :avocado: tags=endian:little
        """
        kernel_url = ('https://mipsdistros.mips.com/LinuxDistro/nanomips/'
                      'kernels/v4.15.18-432-gb2eb9a8b07a1-20180627102142/'
                      'generic_nano32r6el_page16k_up.xz')
        kernel_hash = 'e882868f944c71c816e832e2303b7874d044a7bc'
        self.do_test_mips_malta32el_nanomips(kernel_url, kernel_hash)

    def test_mips_malta32el_nanomips_64k_dbg(self):
        """
        :avocado: tags=arch:mipsel
        :avocado: tags=machine:malta
        :avocado: tags=endian:little
        """
        kernel_url = ('https://mipsdistros.mips.com/LinuxDistro/nanomips/'
                      'kernels/v4.15.18-432-gb2eb9a8b07a1-20180627102142/'
                      'generic_nano32r6el_page64k_dbg.xz')
        kernel_hash = '18d1c68f2e23429e266ca39ba5349ccd0aeb7180'
        self.do_test_mips_malta32el_nanomips(kernel_url, kernel_hash)

    def test_aarch64_virt(self):
        """
        :avocado: tags=arch:aarch64
        :avocado: tags=machine:virt
        """
        self.vm.set_machine('virt')
        self.vm.add_args('-cpu', 'cortex-a53')
        kernel_command_line = self.boot_kernel(provider_name='fedora',
                                               version='29', arch='aarch64',
                                               console='ttyAMA0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_arm_virt(self):
        """
        :avocado: tags=arch:arm
        :avocado: tags=machine:virt
        """
        self.vm.set_machine('virt')
        kernel_command_line = self.boot_kernel(provider_name='fedora',
                                               version='29', arch='armhfp',
                                               console='ttyAMA0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_arm_emcraft_sf2(self):
        """
        :avocado: tags=arch:arm
        :avocado: tags=machine:emcraft_sf2
        :avocado: tags=endian:little
        """
        uboot_url = ('https://raw.githubusercontent.com/'
                     'Subbaraya-Sundeep/qemu-test-binaries/'
                     'fa030bd77a014a0b8e360d3b7011df89283a2f0b/u-boot')
        uboot_hash = 'abba5d9c24cdd2d49cdc2a8aa92976cf20737eff'
        uboot_path = self.fetch_asset(uboot_url, asset_hash=uboot_hash)
        spi_url = ('https://raw.githubusercontent.com/'
                   'Subbaraya-Sundeep/qemu-test-binaries/'
                   'fa030bd77a014a0b8e360d3b7011df89283a2f0b/spi.bin')
        spi_hash = '85f698329d38de63aea6e884a86fbde70890a78a'
        spi_path = self.fetch_asset(spi_url, asset_hash=spi_hash)

        self.vm.set_machine('emcraft-sf2')
        self.vm.set_console()
        kernel_command_line = 'printk.time=0'
        self.vm.add_args('-kernel', uboot_path,
                         '-append', kernel_command_line,
                         '-drive', 'file=' + spi_path + ',if=mtd,format=raw',
                         '-no-reboot')
        self.vm.launch()
        self.wait_for_console_pattern('init started: BusyBox')

    def test_s390x_s390_ccw_virtio(self):
        """
        :avocado: tags=arch:s390x
        :avocado: tags=machine:s390_ccw_virtio
        """
        self.vm.set_machine('s390-ccw-virtio')
        self.vm.add_args('-nodefaults')
        kernel_command_line = self.boot_kernel(provider_name='fedora',
                                               version='29', arch='s390x',
                                               console="sclp0")
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_alpha_clipper(self):
        """
        :avocado: tags=arch:alpha
        :avocado: tags=machine:clipper
        """
        self.vm.set_machine('clipper')
        self.vm.add_args('-vga', 'std')
        kernel_command_line = self.boot_kernel(provider_name='Debian',
                                               version='lenny', arch='alpha')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_ppc64_pseries(self):
        """
        :avocado: tags=arch:ppc64
        :avocado: tags=machine:pseries
        """
        self.vm.set_machine('pseries')
        kernel_command_line = self.boot_kernel(provider_name='fedora',
                                               version='29', arch='ppc64le',
                                               console='hvc0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)
