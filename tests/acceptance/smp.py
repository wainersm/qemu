# Tests smp.
#
# Copyright (c) 2019 Red Hat, Inc.
#
# Author:
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

import re
from avocado.utils import process

from avocado_qemu import Test


class Smp(Test):
    """
    Test QEMU with various cpus, cores, threads, sockets, and maxcpus
    combination through -smp option.
    """

    timeout = 60

    vm_base_args = []

    @staticmethod
    def get_smp_topology(vm):
        """
        Returns a dict with the id of cores, threads and sockets.
        """
        # Use to grep thread id in the qom path.
        regex = re.compile('.*/thread\[(\d+)\]')

        topology = {'cores': set(), 'threads': set(), 'sockets': set()}
        for cpu in vm.command('query-cpus'):
            core_id = cpu['props'].get('core-id')
            if core_id:
                topology['cores'].add(core_id)
            thread_id = cpu['props'].get('thread-id')
            if thread_id is None:
                match = regex.match(cpu['qom_path'])
                if match:
                    thread_id = int(match.group(1))
            topology['threads'].add(thread_id)
            socket_id = cpu['props'].get('socket-id')
            if socket_id:
                topology['sockets'].add(socket_id)
        return topology

    @staticmethod
    def build_option(**kwargs):
        """
        Builds arg string for the -smp option.
        """
        option_list = []
        cpus = kwargs.pop('cpus', None)
        if cpus:
            option_list.append(str(cpus))
        option_list.extend(['%s=%s' % (k, v) for k, v in kwargs.items()])
        return ",".join(option_list)

    def launch_and_check(self, expect_fail=False, expect_cores=1,
                         expect_threads=1, expect_sockets=1, **kwargs):
        """
        Launches an VM and check its SMP topology was correctly set.
        Use cpus, cores, threads, sockets, and maxcpus keys to specify the
        topology.
        """
        vm = self.get_vm()
        if self.vm_base_args:
            vm.add_args(*self.vm_base_args)

        option = self.build_option(**{key: val for key, val in kwargs.items()
                                      if key in ['cpus', 'cores', 'threads',
                                                 'sockets', 'maxcpus']})
        vm.add_args('-smp', option)
        if expect_fail:
            # Expect the VM to fail on launch.
            vm.set_qmp_monitor(disabled=True)
            vm.launch()
            vm.wait()
            self.assertNotEqual(vm.exitcode(), 0)
        else:
            vm.launch()
            smp = self.get_smp_topology(vm)
            if isinstance(expect_cores, int):
                expect_cores = set(range(0, expect_cores))
            self.assertEqual(smp['cores'], expect_cores,
                             "Mismatch cores (-smp %s)" % option)
            if isinstance(expect_threads, int):
                expect_threads = set(range(0, expect_threads))
            self.assertEqual(smp['threads'], expect_threads,
                             "Mismatch threads (-smp %s)" % option)
            if isinstance(expect_sockets, int):
                expect_sockets = set(range(0, expect_sockets))
            self.assertEqual(smp['sockets'], expect_sockets,
                             "Mismatch sockets (-smp %s)" % option)
            vm.shutdown()

    def test_s390x_ccw_kvm(self):
        """
        :avocado: tags=arch:s390x,machine:s390_ccw_virtio,accel:kvm
        """
        self.vm_base_args = ['-machine', 's390_ccw_virtio,accel=kvm']
        maxcpus_limit = 1024

        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

        self.launch_and_check(cpus=(maxcpus_limit - 1), maxcpus=maxcpus_limit,
                              expect_cores=maxcpus_limit, expect_sockets=0,
                              expect_threads=0)

    def test_aarch64_virt_kvm(self):
        """
        :avocado: tags=arch:aarch64,machine:virt,accel:kvm
        """
        self.vm_base_args = ['-machine', 'virt,accel=kvm', '-cpu', 'host']
        maxcpus_limit = 8

        self.launch_and_check(cpus=4, expect_cores=0, expect_threads=4,
                              expect_sockets=0)

        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

        self.launch_and_check(cpus=(maxcpus_limit - 1),  expect_cores=0,
                              expect_sockets=0,
                              expect_threads=(maxcpus_limit - 1))

    def test_ppc64_pseries_kvm(self):
        """
        :avocado: tags=arch:ppc64,machine:pseries,accel:kvm
        """
        # SMT should be disabled on host.
        p = process.run('ppc64_cpu --smt -n')
        if p.stdout.strip() != b'SMT=1':
            self.cancel('Unable to test with SMT enabled on host')

        self.vm_base_args = ['-machine', "pseries,accel=kvm"]

        maxcpus_limit = 1024

        self.launch_and_check(cpus=4, expect_cores=4, expect_sockets=0)

        self.launch_and_check(cpus=4, cores=2, threads=2, expect_cores={0,2},
                              expect_threads=2, expect_sockets=0)

        #self.launch_and_check(cpus=8, cores=2, threads=2, sockets=2,
        #                      expect_cores=2, expect_threads=2,
        #                      expect_sockets=2)

        #self.launch_and_check(cpus=(maxcpus_limit - 1), maxcpus=maxcpus_limit,
        #                      expect_cores=maxcpus_limit, expect_sockets=0,
        #                      expect_threads=0)

        #self.launch_and_check(cpus=maxcpus_limit, expect_cores=maxcpus_limit,
        #                      expect_sockets=0, expect_threads=0)

        #self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

    def test_x86_64_pc_kvm(self):
        """
        :avocado: tags=arch:x86_64,machine:pc,accel:kvm
        """
        self.vm_base_args = ['-cpu', 'host', '-machine', 'pc,accel=kvm']

        maxcpus_limit = 255

        self.launch_and_check(cpus=4, expect_sockets=4)
        self.launch_and_check(cpus=4, maxcpus=6, expect_sockets=6)
        self.launch_and_check(cpus=4, maxcpus=4, expect_sockets=4)
        self.launch_and_check(cpus=8, maxcpus=4, expect_fail=True)
        self.launch_and_check(cpus=2, cores=4, maxcpus=8, expect_cores=4,
                              expect_sockets=2)
        self.launch_and_check(cpus=2, cores=2, threads=2, maxcpus=8,
                              expect_cores=2, expect_threads=2,
                              expect_sockets=2)
        self.launch_and_check(cpus=(maxcpus_limit - 1), maxcpus=maxcpus_limit,
                              expect_sockets=maxcpus_limit)
        self.launch_and_check(cpus=maxcpus_limit, expect_sockets=maxcpus_limit)
        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

    def test_x86_64_q35_kvm(self):
        """
        :avocado: tags=arch:x86_64,machine:q35,accel:kvm
        """
        self.vm_base_args = ['-cpu', 'host', '-machine',
                             "q35,accel=kvm,kernel-irqchip=split",
                             '-device', 'intel-iommu,intremap=on,eim=on']

        maxcpus_limit = 288

        self.launch_and_check(cpus=4, expect_sockets=4)
        self.launch_and_check(cpus=4, maxcpus=6, expect_sockets=6)
        self.launch_and_check(cpus=4, maxcpus=4, expect_sockets=4)
        self.launch_and_check(cpus=8, maxcpus=4, expect_fail=True)
        self.launch_and_check(cpus=2, cores=4, maxcpus=8, expect_cores=4,
                              expect_sockets=2)
        self.launch_and_check(cpus=2, cores=2, threads=2, maxcpus=8,
                              expect_cores=2, expect_threads=2,
                              expect_sockets=2)
        self.launch_and_check(cpus=(maxcpus_limit - 1), maxcpus=maxcpus_limit,
                              expect_sockets=maxcpus_limit)
        self.launch_and_check(cpus=maxcpus_limit, expect_sockets=maxcpus_limit)
        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

    def test_x86_64_q35_tcg(self):
        """
        :avocado: tags=arch:x86_64,machine:q35,accel:tcg
        """
        self.vm_base_args = ['-machine', "q35,accel=tcg"]

        maxcpus_limit = 255

        self.launch_and_check(cpus=4, cores=2, expect_sockets=2, expect_cores=2)
        self.launch_and_check(cpus=8, cores=2, threads=2, maxcpus=12,
                              expect_cores=2, expect_sockets=3,
                              expect_threads=2)
        self.launch_and_check(cpus=maxcpus_limit, expect_sockets=maxcpus_limit)
        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)
