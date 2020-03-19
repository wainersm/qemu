import os

from boot_linux import BootLinux

def get_open_fds(pid):
    """
    Get the file descriptors open by the process.

    :param pid: the process ID.
    :type pid: str or int
    :return: a mapping of each fd number to file. In case of it is denied
             permission to resolve the link, the value is set to None.
    :rtype: dict
    """
    fd_map = dict()
    proc_fd = os.path.join('/proc', str(pid), 'fd')
    for fd in os.listdir(proc_fd):
        try:
            obj = os.readlink(os.path.join(proc_fd, fd))
        except PermissionError:
            obj = None
        fd_map[fd] = obj
    return fd_map

class VirtioRng(BootLinux):
    """
    Test virtio-rng device.
    """

    enable_ssh = True
    guest_user = 'root'

    def setUp(self):
        super(VirtioRng, self).setUp()
        self.virtio_rng_dev = self.params.get('virtio_rng_dev',
                                              default='virtio-rng-pci')
        self.host_random_dev = '/dev/urandom'

    def assert_host(self):
        """
        Checks to ensure the random device on host is used.
        """
        vm_pid = self.vm.get_pid()
        self.assertIsNotNone(vm_pid, "VM's process ID")
        fds = get_open_fds(vm_pid)
        self.assertIn(self.host_random_dev, fds.values())

    def assert_guest(self):
        """
        Checks to ensure the virtio-rng device is operational on the guest.
        """
        ret = self.ssh_session.cmd('cat /sys/class/misc/hw_random/rng_current')
        self.assertTrue(ret.stdout_text.startswith('virtio_rng'),
                        'virtio-rng is currently used')

        guest_random_dev = '/dev/hwrng'
        ret = self.ssh_session.cmd('dd if=%s of=/dev/null count=1' %
                                   guest_random_dev)
        self.assertTrue(ret.exit_status == 0,
                        'Can read from %s' % guest_random_dev)

    def test_random(self):
        """
        Test the random backend.
        """
        self.vm.add_args('-object',
                         'rng-random,id=rng0,filename=%s' % self.host_random_dev,
                         '-device', '%s,rng=rng0' % self.virtio_rng_dev)
        self.launch_and_wait()
        self.assert_host()
        self.assert_guest()

    def test_builtin(self):
        """
        Test the builtin RNG backend.
        """
        self.vm.add_args('-object', 'rng-builtin,id=rng0',
                         '-device', '%s,rng=rng0' % self.virtio_rng_dev)
        self.launch_and_wait()
        self.assert_guest()

    def test_egd(self):
        """
        Test the Entropy Gathering Daemon (EGD) backend.
        """
        #self.vm.add_args('-chardev socket,host=127.0.0.1,port=1024,id=chr0',
        #                 '-object', 'rng-egd,chardev=chr0,id=rng0',
        #                 '-device', 'virtio-rng-pci,rng=rng0')

        #self.do_test()
