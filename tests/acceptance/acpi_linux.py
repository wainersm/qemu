
from avocado_qemu import Test

class AcpiLinux(Test):
    """
    :avocado: enable
    """
    def test(self):
        #self.vm.add_args('-no-acpi')
        self.vm.add_args('-m',  '4G,slots=4,maxmem=8G',
                         '-numa', 'node,nodeid=0',
                         '-numa', 'node,nodeid=1,mem=2G',
                         '-numa', 'node,nodeid=2,mem=2G',
                         '-numa', 'node,nodeid=3',
                         "-device", "virtio-serial-pci,id=virtio-serial0",
                         "-device", "virtio-balloon-pci",
                         "-object", "cryptodev-backend-builtin,id=cryptodev0",
                         "-device", "virtio-crypto-pci,id=crypto0,cryptodev=cryptodev0")
        self.vm.launch()
        #self.vm.command('query-commands')
        self.vm.command('query-acpi-ospm-status')
