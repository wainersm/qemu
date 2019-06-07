# Linux initrd acceptance test.
#
# Copyright (c) 2018 Red Hat, Inc.
#
# Author:
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

import logging
import tempfile
from avocado.utils.process import run

from avocado_qemu import linux_kernel

class LinuxInitrd(linux_kernel.BootKernelTest):
    """
    Checks QEMU evaluates correctly the initrd file passed as -initrd option.

    :avocado: tags=arch:x86_64
    """

    timeout = 300

    def test_with_2gib_file_should_exit_error_msg_with_linux_v3_6(self):
        """
        Pretends to boot QEMU with an initrd file with size of 2GiB
        and expect it exits with error message.
        Fedora-18 shipped with linux-3.6 which have not supported xloadflags
        cannot support more than 2GiB initrd.
        """
        self.prepare_kernel('fedora18_x86_64')
        max_size = 2 * (1024 ** 3) - 1

        with tempfile.NamedTemporaryFile() as initrd:
            initrd.seek(max_size)
            initrd.write(b'\0')
            initrd.flush()
            cmd = "%s -kernel %s -initrd %s -m 4096" % (
                  self.qemu_bin, self.kernel_path, initrd.name)
            res = run(cmd, ignore_status=True)
            self.assertEqual(res.exit_status, 1)
            expected_msg = r'.*initrd is too large.*max: \d+, need %s.*' % (
                max_size + 1)
            self.assertRegex(res.stderr_text, expected_msg)

    def test_with_2gib_file_should_work_with_linux_v4_16(self):
        """
        QEMU has supported up to 4 GiB initrd for recent kernel
        Expect guest can reach 'Unpacking initramfs...'
        """
        max_size = 2 * (1024 ** 3) + 1

        with tempfile.NamedTemporaryFile() as initrd:
            initrd.seek(max_size)
            initrd.write(b'\0')
            initrd.flush()

            self.vm.set_machine('pc')
            self.vm.add_args('-initrd', initrd.name, '-m', '5120')
            self.boot_kernel('fedora29_x86_64')
            self.wait_for_console_pattern('Unpacking initramfs...')
