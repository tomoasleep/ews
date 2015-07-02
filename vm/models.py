from django.db import models
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from .vmoperation import VMCreateOperation, VMSearchQuery, VMUpdateOperation, VMDeleteOperation, VMFetchOperation, VMPowerControl
import uuid

def model_alias(name):
    "Define an alias property to my instance"
    def fget(self):
        return getattr(self.instance, name)
    def fset(self, val):
        return setattr(self.instance, name, val)
    return property(fget, fset)

def attribute(name, wrapper = (lambda x: x), doc = ''):
    "Define a property always having the specified type"
    def fget(self):
        if not hasattr(self, 'attribute') :
            self.attribute = {}
        if name in self.attribute :
            return self.attribute[name]
        else :
            return None
    def fset(self, val):
        if not hasattr(self, 'attribute') :
            self.attribute = {}
        if val is None:
            self.attribute[name] = None
        else:
            self.attribute[name] = wrapper(val)
    return property(fget, fset)

class VirtualMachine(object):
    """
    Having full information about a virtual machine
    from the database and the hypervisor.
    """
    @classmethod
    def from_record(cls, record):
        res = VMSearchQuery(record.uuid).search()
        return cls(instance=record, attributes=res)

    id = model_alias('id')
    user = model_alias('user')
    name = model_alias('name')
    uuid = model_alias('uuid')
    vncport = model_alias('vncport')
    password = model_alias('password')

    # Define attributes' types
    state = attribute('state', unicode)
    cpu = attribute('cpu', int)
    os = attribute('os', unicode)
    memorysize = attribute('memorysize', int)
    disksize = attribute('disksize', int)
    bootdev = attribute('bootdev', str)
    cdrom = attribute('cdrom', str)

    def __init__(self, instance=None, attributes={}):
        if instance is None:
            self.instance = VirtualMachineRecord()
        else:
            self.instance = instance

        self.update(attributes)

        if not self.is_new() :
            VMFetchOperation(self).submit()

    def update(self, attributes = {}):
        for k, v in attributes.items():
            # Set only decleared attrs.
            if hasattr(self.__class__, k):
                setattr(self, k, v)
        return self

    def to_record(self):
        return self.instance

    def save(self):
        if self.is_new():
            self.uuid = VMCreateOperation(self).submit().get_uuid()
            self.to_record().save()
        else:
            VMUpdateOperation(self).submit()
            self.to_record().save()
        return self

    def is_new(self):
        return self.uuid is None

    def is_running(self):
        return self.state.is_running()

    def delete(self):
        VMDeleteOperation(self).submit()
        self.instance.delete()

    def get_disksize_byte(self):
        # a unit of disksize is giga byte.
        return 1024 * 1024 * 1024 * self.disksize

    def get_memorysize_kilobyte(self):
        # a unit of disksize is giga byte.
        return 1024 * 1024 * self.memorysize

    def power_on(self):
        VMPowerControl(self).power_on()

    def shutdown(self):
        VMPowerControl(self).shutdown()

class VirtualMachineRecord(models.Model):
    """ A record class whose instance is saved in the database. """
    user = models.ForeignKey(User)
    name = models.CharField(max_length=100, default='your virtual machine')
    uuid = models.UUIDField(max_length=100)
    vncport = models.IntegerField()
    password = models.CharField(max_length=100)

    @classmethod
    def find_vnc_port(cls):
        vm_records = VirtualMachineRecord.objects.all()
        vncport = 5750
        for record in vm_records:
            vncport = max(int(record.vncport), vncport)
        vncport += 1
        return vncport

    def __unicode__(self):
        return self.name
