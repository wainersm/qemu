# Migration test
#
# Copyright (c) 2019 Red Hat, Inc.
#
# Authors:
#  Cleber Rosa <crosa@redhat.com>
#  Caio Carrara <ccarrara@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.


import os
import socket
from avocado_qemu import Test
from qemu.machine import QEMUMachine

from avocado.utils import network
from avocado.utils import wait


class Migration(Test):

    timeout = 10

    @staticmethod
    def migration_finished(vm):
        return vm.command('query-migrate')['status'] in ('completed', 'failed')

    def _get_free_port(self):
        port = network.find_free_port()
        if port is None:
            self.cancel('Failed to find a free port')
        return port

    def assert_migration(self, source_vm, dest_vm):
        wait.wait_for(self.migration_finished,
                      timeout=self.timeout,
                      step=0.1,
                      args=(source_vm,))
        self.assertEqual(source_vm.command('query-migrate')['status'], 'completed')
        self.assertEqual(dest_vm.command('query-migrate')['status'], 'completed')
        self.assertEqual(dest_vm.command('query-status')['status'], 'running')
        self.assertEqual(source_vm.command('query-status')['status'], 'postmigrate')

    def do_migrate(self, dest_uri, source_vm=None, dest_vm=None):
        if not source_vm:
            source_vm = self.get_vm()
        if not dest_vm:
            dest_vm = self.get_vm()
        dest_vm.add_args('-incoming', dest_uri)
        dest_vm.launch()
        source_vm.launch()
        source_vm.qmp('migrate', uri=dest_uri)
        self.assert_migration(source_vm, dest_vm)

    def test_migration_with_tcp_localhost(self):
        dest_uri = 'tcp:localhost:%u' % self._get_free_port()
        self.do_migrate(dest_uri)

    def test_migration_with_fd(self):
        opaque = 'fd-migration'
        spair = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        fd1 = spair[0].fileno()
        fd2 = spair[1].fileno()
        os.set_inheritable(fd1, True)
        os.set_inheritable(fd2, True)

        scm_helper = '/home/wainersm/build/qemu_01/tests/qemu-iotests/socket_scm_helper'
        source_vm = QEMUMachine(self.qemu_bin, socket_scm_helper=scm_helper)
        source_vm.launch()
        self.assertEqual(source_vm.send_fd_scm(fd=fd1), 0)
        source_vm.command('getfd', fdname=opaque)

        dest_vm = self.get_vm('-incoming', 'fd:%s' % fd2)
        dest_vm.launch()

        source_vm.qmp('migrate', uri='fd:%s' % opaque)
        self.assert_migration(source_vm, dest_vm)
