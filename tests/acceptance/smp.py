# QEMU smp tests.
#
# Copyright (c) 2019 Red Hat, Inc.
#
# Author:
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

from functools import reduce
from avocado.utils.process import run

from avocado_qemu import Test


class Smp(Test):
    """
    Launches QEMU with various cpus, cores, threads, sockets, and maxcpus
    combination through -smp option, to check it does not accept invalid SMP
    topologies as well as it is able to calculate correctly any missing values.
    """

    vm_base_args = []

    @staticmethod
    def get_smp_topology(vm):
        """
        Returns a dict with the id of cores, threads and sockets.
        """
        res = vm.qmp('query-hotpluggable-cpus')['return']
        cpus = [x['props'] for x in res]

        # TODO: simplify me.
        return reduce(lambda x, y: {'core-id': x['core-id'].union([z for z in [y.get('core-id')]if z is not None]),
                                    'thread-id': x['thread-id'].union([z for z in [y.get('thread-id')] if z is not None]),
                                    'socket-id': x['socket-id'].union([z for z in  [y.get('socket-id')] if z is not None])},
                      cpus, {'core-id': set(), 'thread-id': set(), 'socket-id': set()})

    def get_maxcpus_limit(self, machine, accel):
        vm = self.get_vm('-S', '-machine', '%s,accel=%s' % (machine, accel))
        vm.launch()
        maxcpus_limit = None
        for entry in vm.command('query-machines'):
            if machine in [entry['name'], entry.get('alias')]:
                maxcpus_limit = entry['cpu-max']
                break
        vm.shutdown()
        return maxcpus_limit

    @staticmethod
    def build_option(**kwargs):
        """
        Builds string for the -smp option.
        Use cpus, cores, threads, sockets, maxcpus keys.
        """
        option_list = []
        if kwargs.get('cpus', None) is not None:
            option_list.append(str(kwargs.get('cpus')))
        for key, val in kwargs.items():
            if key == 'cpus':
                continue
            option_list.append('%s=%s' % (key, val))

        return ",".join(option_list)

    def launch_and_check(self, expect_fail=False, expect_cores=1, expect_threads=1,
                         expect_sockets=1, **kwargs):
        """
        Launches VM and check its SMP topology was correctly set.
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
            vm.set_qmp_monitor(disabled=True)
            vm.launch()
            vm.wait()
            self.assertNotEqual(vm.exitcode(), 0)
        else:
            vm.launch()
            smp = self.get_smp_topology(vm)
            self.assertEqual(smp['core-id'], set(range(0, expect_cores)), "check cores failed")
            self.assertEqual(smp['thread-id'], set(range(0, expect_threads)), "check threads failed")
            self.assertEqual(smp['socket-id'], set(range(0, expect_sockets)), "check sockets failed")
            vm.shutdown()

#    def launch_and_check_fail(self, **kwargs):
#        """
#        Launches VM and check the process exits with expected error code, for
#        cases where the topology is expected not valid.
#        """
#        option = self.build_option(**kwargs)
#        vm = self.get_vm('-smp', option)
#        vm.set_qmp_monitor(disabled=True)
#        vm.launch()
#        vm.wait()
#        self.assertNotEqual(vm.exitcode(), 0)
#        vm.shutdown()
        #res = run("%s -smp %s" % (self.qemu_bin, option), timeout=10,
        #          ignore_status=True)
        #self.assertNotEqual(res.exit_status, 0)

    def test_with_ppc64_pseries_tcg(self):
        """
        :avocado: tags=arch:ppc64,machine:pseries,accel:tcg
        """
        self.vm_base_args = ['-machine', "pseries,accel=tcg"]

        maxcpus_limit = self.get_maxcpus_limit('pseries', 'tcg')

        self.launch_and_check(cpus=4, expect_cores=4, expect_threads=0,
                              expect_sockets=0)

        self.launch_and_check(cpus=4, cores=2, threads=2, expect_fail=True)

        self.launch_and_check(cpus=(maxcpus_limit - 1), maxcpus=maxcpus_limit,
                              expect_cores=maxcpus_limit, expect_sockets=0,
                              expect_threads=0)

        self.launch_and_check(cpus=maxcpus_limit, expect_cores=maxcpus_limit,
                              expect_sockets=0, expect_threads=0)

        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

    def test_with_x86_64_pc_kvm(self):
        """
        :avocado: tags=arch:x86_64,machine:pc,accel:kvm
        """
        self.vm_base_args = ['-cpu', 'host', '-machine', 'pc,accel=kvm']

        maxcpus_limit = self.get_maxcpus_limit('pc', 'kvm')

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

    def test_with_x86_64_q35_kvm(self):
        """
        :avocado: tags=arch:x86_64,machine:q35,accel:kvm
        """
        self.vm_base_args = ['-cpu', 'host', '-machine',
                             "q35,accel=kvm,kernel-irqchip=split",
                             '-device', 'intel-iommu,intremap=on,eim=on']

        maxcpus_limit = self.get_maxcpus_limit('q35', 'kvm')

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

    def test_with_x86_64_q35_tcg(self):
        """
        :avocado: tags=arch:x86_64,machine:q35,accel:tcg
        """
        self.vm_base_args = ['-machine', "q35,accel=tcg"]

        maxcpus_limit = self.get_maxcpus_limit('q35', 'tcg')

#        self.launch_and_check(cpus=maxcpus_limit, expect_sockets=maxcpus_limit)

#        self.launch_and_check(cpus=(maxcpus_limit + 1), expect_fail=True)

