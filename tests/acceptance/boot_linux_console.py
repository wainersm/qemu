# Functional test that boots a Linux kernel and checks the console
#
# Copyright (c) 2018 Red Hat, Inc.
#
# Author:
#  Cleber Rosa <crosa@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

from avocado_qemu import linux_kernel


class BootLinuxConsole(linux_kernel.BootKernelTest):
    """
    Boots a Linux kernel and checks that the console is operational and the
    kernel command line is properly passed from QEMU to the kernel
    """

    timeout = 90


    def test_x86_64_pc(self):
        """
        :avocado: tags=arch:x86_64
        :avocado: tags=machine:pc
        """
        self.vm.set_machine('pc')
        kernel_command_line = self.boot_kernel('fedora29_x86_64')
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

    def test_aarch64_virt(self):
        """
        :avocado: tags=arch:aarch64
        :avocado: tags=machine:virt
        """
        self.vm.set_machine('virt')
        self.vm.add_args('-cpu', 'cortex-a53')
        kernel_command_line = self.boot_kernel('fedora29_aarch64',
                                               console='ttyAMA0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_arm_virt(self):
        """
        :avocado: tags=arch:arm
        :avocado: tags=machine:virt
        """
        self.vm.set_machine('virt')
        kernel_command_line = self.boot_kernel('fedora29_armhfp',
                                               console='ttyAMA0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_s390x_s390_ccw_virtio(self):
        """
        :avocado: tags=arch:s390x
        :avocado: tags=machine:s390_ccw_virtio
        """
        self.vm.set_machine('s390-ccw-virtio')
        self.vm.add_args('-nodefaults')
        kernel_command_line = self.boot_kernel('fedora29_s390x',
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
        kernel_command_line = self.boot_kernel('debian5_alpha')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)

    def test_ppc64_pseries(self):
        """
        :avocado: tags=arch:ppc64
        :avocado: tags=machine:pseries
        """
        self.vm.set_machine('pseries')
        kernel_command_line = self.boot_kernel('fedora29_ppc64le',
                                               console='hvc0')
        console_pattern = 'Kernel command line: %s' % kernel_command_line
        self.wait_for_console_pattern(console_pattern)
