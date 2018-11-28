# QEMU smp tests.
#
# Copyright (c) 2018 Red Hat, Inc.
#
# Author:
#  Wainer dos Santos Moschetta <wainersm@redhat.com>
#
# This work is licensed under the terms of the GNU GPL, version 2 or
# later.  See the COPYING file in the top-level directory.

from functools import reduce
from avocado.utils.process import run

from avocado_qemu import Test


class SmpOption(Test):
    """
    Launches QEMU with various cpus, cores, threads, sockets, and maxcpus
    combination through -smp option, to check it does not accept invalid SMP
    topologies as well as it is able to calculate correctly any missing values.

    :avocado: enable
    :avocado: tags=slow
    """
    def setUp(self):
        super().setUp()
        self.machine = self.params.get('machine', default='q35')
        self.accel = self.params.get('accel', default='kvm')
        self.maxcpus_limit = int(self.params.get('maxcpus_limit', default=288))

    def get_smp_topology(self):
        """
        Returns a dict with the id of cores, threads and sockets.
        """
        res = self.vm.qmp('query-hotpluggable-cpus')['return']
        cpus = [x['props'] for x in res]

        # TODO: simplify me.
        return reduce(lambda x, y: {'core-id': x['core-id'].union([z for z in [y.get('core-id')]if z is not None]),
                                    'thread-id': x['thread-id'].union([z for z in [y.get('thread-id')] if z is not None]),
                                    'socket-id': x['socket-id'].union([z for z in  [y.get('socket-id')] if z is not None])},
                      cpus, {'core-id': set(), 'thread-id': set(), 'socket-id': set()})

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

    def launch_and_check(self, expect_cores=1, expect_threads=1,
                         expect_sockets=1, **kwargs):
        """
        Launches VM and check its SMP topology was correctly set.
        Use cpus, cores, threads, sockets, and maxcpus keys to specify the
        topology.
        """
        option = self.build_option(**{key: val for key, val in kwargs.items()
                                      if key in ['cpus', 'cores', 'threads',
                                                 'sockets', 'maxcpus']})
        self.vm.add_args('-smp', option)
        self.vm.launch()
        smp = self.get_smp_topology()
        self.assertEqual(smp['core-id'], set(range(0, expect_cores)), "check cores failed")
        self.assertEqual(smp['thread-id'], set(range(0, expect_threads)), "check threads failed")
        self.assertEqual(smp['socket-id'], set(range(0, expect_sockets)), "check sockets failed")
        self.vm.shutdown()

    def launch_and_check_fail(self, **kwargs):
        """
        Launches VM and check the process exits with expected error code, for
        cases where the topology is expected not valid.
        """
        option = self.build_option(**kwargs)
        res = run("%s -smp %s" % (self.qemu_bin, option), timeout=10,
                  ignore_status=True)
        self.assertNotEqual(res.exit_status, 0)


    def test_ppc64_pseries_tcg(self):
        if not (self.machine == 'pseries' and self.accel == 'tcg'):
            self.cancel()

        def prepare_vm():
            self.vm._args.clear()
            self.vm.add_args('-machine', "%s,accel=%s" % (self.machine, self.accel))

        prepare_vm()
        self.launch_and_check(cpus=4,
                              expect_cores=4,
                              expect_threads=0,
                              expect_sockets=0)
        prepare_vm()
        self.launch_and_check_fail(cpus=4, cores=2, threads=2)

        prepare_vm()
        self.launch_and_check(cpus=(self.maxcpus_limit - 1), maxcpus=self.maxcpus_limit,
                              expect_cores=self.maxcpus_limit,
                              expect_sockets=0,
                              expect_threads=0)
        prepare_vm()
        self.launch_and_check(cpus=self.maxcpus_limit,
                              expect_cores=self.maxcpus_limit,
                              expect_sockets=0,
                              expect_threads=0)
        prepare_vm()
        self.launch_and_check_fail(cpus=(self.maxcpus_limit + 1))

    def test_i386_pc_kvm(self):
        if not (self.machine == 'pc' and self.accel == 'kvm'):
            self.cancel("Not suitable")

        def prepare_vm():
            self.vm._args.clear()
            self.vm.add_args('-cpu', 'host')
            self.vm.add_args('-machine', 'pc,accel=kvm')

        prepare_vm()
        self.launch_and_check(cpus=4,
                              expect_sockets=4)
        prepare_vm()
        self.launch_and_check(cpus=4,
                              maxcpus=6,
                              expect_sockets=6)
        prepare_vm()
        self.launch_and_check(cpus=4,
                              maxcpus=4,
                              expect_sockets=4)
        prepare_vm()
        self.launch_and_check_fail(cpus=8,
                                   maxcpus=4)
        prepare_vm()
        self.launch_and_check(cpus=2, cores=4, maxcpus=8,
                              expect_cores=4,
                              expect_sockets=2)
        prepare_vm()
        self.launch_and_check(cpus=2, cores=2, threads=2, maxcpus=8,
                              expect_cores=2,
                              expect_threads=2,
                              expect_sockets=2)
        prepare_vm()
        self.launch_and_check(cpus=(self.maxcpus_limit - 1), maxcpus=self.maxcpus_limit,
                              expect_sockets=self.maxcpus_limit)
        prepare_vm()
        self.launch_and_check(cpus=self.maxcpus_limit,
                              expect_sockets=self.maxcpus_limit)
        prepare_vm()
        self.launch_and_check_fail(cpus=(self.maxcpus_limit + 1))

    def test_i386_q35_kvm(self):
        """
        """
        if not (self.machine == 'q35' and self.accel == 'kvm'):
            self.cancel()

        def prepare_vm():
            self.vm._args.clear()
            self.vm.add_args('-cpu', 'host')
            self.vm.add_args('-machine', "%s,accel=%s,kernel-irqchip=split" % (self.machine, self.accel))
            self.vm.add_args('-device', 'intel-iommu,intremap=on,eim=on')

        prepare_vm()
        self.launch_and_check(cpus=4,
                              expect_sockets=4)

        prepare_vm()
        self.launch_and_check(cpus=4,
                              maxcpus=6,
                              expect_sockets=6)
        prepare_vm()
        self.launch_and_check(cpus=4,
                              maxcpus=4,
                              expect_sockets=4)
        prepare_vm()
        self.launch_and_check_fail(cpus=8,
                                  maxcpus=4)

        prepare_vm()
        self.launch_and_check(cpus=2, cores=4, maxcpus=8,
                              expect_cores=4,
                              expect_sockets=2)

        prepare_vm()
        self.launch_and_check(cpus=2, cores=2, threads=2, maxcpus=8,
                              expect_cores=2,
                              expect_threads=2,
                              expect_sockets=2)

        prepare_vm()
        self.launch_and_check(cpus=(self.maxcpus_limit - 1),
                              maxcpus=self.maxcpus_limit,
                              expect_sockets=self.maxcpus_limit)

        prepare_vm()
        self.launch_and_check(cpus=self.maxcpus_limit,
                              expect_sockets=self.maxcpus_limit)

        prepare_vm()
        self.launch_and_check_fail(cpus=(self.maxcpus_limit + 1))
