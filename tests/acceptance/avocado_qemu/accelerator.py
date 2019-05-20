from qemu import QEMUMachine
from qemu import kvm_available

def _spawn_vm_checker(accel, qemu_bin):
    """ Checks accelerator can be enabled is a spawned VM """
    try:
        vm = QEMUMachine(qemu_bin)
        vm.add_args("-accel", accel)
        vm.launch()
        vm.shutdown()
    except:
        if "No accelerator found" in vm.get_log():
            return False
        raise
    return True

def tcg_checker(qemu_bin):
    """ Checks TCG is enabled in the QEMU binary """
    return _spawn_vm_checker("tcg", qemu_bin)

def kvm_checker(qemu_bin):
    """ Checks KVM is present in the host and enabled in the QEMU binary """
    if kvm_available() and _spawn_vm_checker("kvm", qemu_bin):
        return True
    return False

_checked = {}
_checkers = {"tcg": tcg_checker, "kvm": kvm_checker}

def is_available(accel, qemu_bin):
    """
    Checks if the accelerator is present on host as well as is enabled in
    the QEMU binary.

    :param accel:  accelerator's name.
    :type accel: str
    :param qemu_bin: path to the QEMU binary.
    :type qemu_bin: str
    :returns: True if accelerator is available, False otherwise.
    :rtype: boolean
    """
    checker = _checkers.get(accel, None)
    if checker:
        return checker(qemu_bin)
    raise Exception("Cannot check availability of %s accelerator" % accel)
