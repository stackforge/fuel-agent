# Copyright 2014 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import os
import time

from fuel_agent import errors
from fuel_agent.openstack.common import log as logging
from fuel_agent.utils import utils

LOG = logging.getLogger(__name__)


def make_fs(fs_type, fs_options, fs_label, dev):
    # NOTE(agordeev): notice the different flag to force the fs creating
    #                ext* uses -F flag, xfs/mkswap uses -f flag.
    cmd_line = []
    cmd_name = 'mkswap'
    if fs_type != 'swap':
        cmd_name = 'mkfs.%s' % fs_type
    if fs_type == 'xfs':
        # NOTE(agordeev): force xfs creation.
        # Othwerwise, it will fail to proceed if filesystem exists.
        fs_options += ' -f '
    cmd_line.append(cmd_name)
    for opt in (fs_options, fs_label):
        cmd_line.extend([s for s in opt.split(' ') if s])
    cmd_line.append(dev)
    utils.execute(*cmd_line)


def extend_fs(fs_type, fs_dev):
    if fs_type in ('ext2', 'ext3', 'ext4'):
        # ext3,4 file system can be mounted
        # must be checked with e2fsck -f
        utils.execute('e2fsck', '-yf', fs_dev, check_exit_code=[0])
        utils.execute('resize2fs', fs_dev, check_exit_code=[0])
        utils.execute('e2fsck', '-pf', fs_dev, check_exit_code=[0])
    elif fs_type == 'xfs':
        # xfs file system must be mounted
        utils.execute('xfs_growfs', fs_dev, check_exit_code=[0])
    else:
        raise errors.FsUtilsError('Unsupported file system type')


def mount_fs(fs_type, fs_dev, fs_mount):
    utils.execute('mount', '-t', fs_type, fs_dev, fs_mount,
                  check_exit_code=[0])


def mount_bind(chroot, path, path2=None):
    if not path2:
        path2 = path
    utils.execute('mount', '--bind', path, chroot + path2,
                  check_exit_code=[0])


def umount_fs(fs_mount, try_lazy_umount=False):
    try:
        utils.execute('mountpoint', '-q', fs_mount, check_exit_code=[0])
    except errors.ProcessExecutionError:
        LOG.warning('%s is not a mountpoint, skipping umount', fs_mount)
    else:
        LOG.debug('Trying to umount {0}'.format(fs_mount))
        try:
            utils.execute('umount', fs_mount, check_exit_code=[0])
        except errors.ProcessExecutionError as e:
            if try_lazy_umount:
                LOG.warning('Error while umounting {0} '
                            'exc={1}'.format(fs_mount, e.message))
                LOG.debug('Trying lazy umounting {0}'.format(fs_mount))
                utils.execute('umount', '-l', fs_mount, check_exit_code=[0])
            else:
                raise


def _run_e2fsprogs(*cmd, **kwargs):
    # Timestamps reported tune2fs depend on time zone, however debugfs'
    # commands which manipulate the timestamps implicitly assume the UTC time
    # zone. Therefore explicitly set the UTC time zone when running debugfs,
    # tune2fs and other ext[234] related utilities.
    # Also the time format might depend on the locale. Set the POSIX locale
    # to avoid spurious failures.
    new_env = kwargs.get('env_variables') or copy.deepcopy(os.environ)
    new_env['LC_ALL'] = 'C'
    new_env['TZ'] = 'UTC'
    kwargs['env_variables'] = new_env
    return utils.execute(*cmd, **kwargs)


def get_ext234_superblock_params(device):
    """Report parameters of the ext[234] superblock as a dict"""
    try:
        raw_sb_dump, _ = _run_e2fsprogs('tune2fs', '-l', device)
    except errors.ProcessExecutionError as e:
        raise errors.FsUtilsError('Failed to run tune2fs -l %s, '
                                  'exit code: %s' % (device, e.exit_code))

    # tune2fs -l output:
    # tune2fs version X.Y.Z
    # Filesystem volume name: <none>
    # Filesystem UUID:        01234567-89ab-cdef-0123-456789abcdef
    # Filesystem revision #:  1 (dynamic)
    # Filesystem created:     Thu Jan  1 00:00:01 1970
    # Last mount time:        Thu Jan  1 00:00:01 1970
    # Last write time:        Thu Jan  1 00:00:01 1970
    # Last checked:           Thu Jan  1 00:00:01 1970

    sb_param = {}
    for line in raw_sb_dump.strip().split('\n'):
        if line.startswith('tune2fs'):
            continue
        key, val = line.split(':', 1)
        sb_param[key.strip()] = val.strip()
    return sb_param


def get_ext234_superblock_timestamps(device):
    sb_param = get_ext234_superblock_params(device)
    params_map = {
        'last_write': 'Last write time',
        'last_mount': 'Last mount time',
        'last_check': 'Last checked',
        'created': 'Filesystem created'
    }

    def tune2fs_strptime(string):
        # XXX(asheplyakov): tune2fs prints timestamps using C locale format,
        # i.e. "%a %b %e %H:%M:%S %Y" (example: "Thu Jan  1 00:00:01 1970").
        # However time.strptime does not support %e. As a work around
        # temporarily set the C locale and use %c (date and time for the
        # current locale)
        with utils.temporary_environ(LC_ALL='C'):
            return time.strptime(string, '%c')

    return dict([(key, tune2fs_strptime(sb_param[raw_key]))
                 for key, raw_key in params_map.iteritems()])


def set_ext234_superblock_timestamps(device,
                                     last_write=None,
                                     last_mount=None,
                                     last_check=None,
                                     created=None):
    """Set superblock timestamps of an ext[234] filesystem."""
    now = time.gmtime()

    def debugfs_strftime(ts):
        return time.strftime('%Y%m%d%H%M%S', ts)

    timestamps = {
        'last_write': debugfs_strftime(last_write or now),
        'last_mount': debugfs_strftime(last_mount or now),
        'last_check': debugfs_strftime(last_check or now),
        'created': debugfs_strftime(created or now),
    }
    debugfs_commands = [
        # NOTE(asheplyakov): debugfs (or rather e2fslibs) implicitly modifies
        # the superblock last write time when flushing the filesystem.
        # Therefore it's necessary to change debugfs' idea about current time
        # to actually change the last write time. This should be done before
        # any other modifications (so that the current timestamp won't lurk in)
        'set_current_time {last_write}',
        'set_super_value wtime {last_write}',
        'set_super_value mtime {last_mount}',
        'set_super_value lastcheck {last_check}',
        'set_super_value mkfs_time {created}',
        'close_filesys',
    ]
    debugfs_commands = '\n'.join(debugfs_commands).format(**timestamps)
    # XXX(asheplyakov): debugfs ignores most errors (failure to open the
    # filesystem, failure to read or write a parameter, etc). Also it always
    # exits with zero status in an interactive mode (i.e. when neither -f nor
    # -R flags have been specified). Therefore pass '-f -' to activate the
    # batch mode so debugfs will raise an error on invalid command.
    LOG.debug('Setting superblock timestamps on %s: %s', device,
              debugfs_commands)
    try:
        stdout, stderr = _run_e2fsprogs('debugfs', '-f', '-', '-w', device,
                                        process_input=debugfs_commands)
    except errors.ProcessExecutionError as e:
        LOG.debug('debugfs -f - -w %s failed: exit code %s',
                  device, e.exit_code)
        raise errors.FsUtilsError('Failed to run debugfs %s, '
                                  'exit_code %s' % (device, e.exit_code))

    # XXX(asheplyakov): just because debugfs returned a zero code
    # doesn't mean the operation was successful. Explicitly verify
    # that timestamps have been actually set:
    LOG.debug('Checking if timestamps on %s has been actually set', device)
    actual_timestamps = dict([(var, debugfs_strftime(val))
                              for var, val in
                              get_ext234_superblock_timestamps(device).
                              iteritems()])
    if actual_timestamps != timestamps:
        LOG.debug("Actual superblock timestamps of %s (%s) "
                  "don't match the requested ones (%s)",
                  device, str(actual_timestamps), str(timestamps))
        raise errors.FsUtilsError(
            "Failed to set superblock timestamps of %s, "
            "actual timestamps (%s) don't match the requested ones (%s)" %
            (device, str(actual_timestamps), str(timestamps)))
    LOG.debug('Successfully set superblock timestamps of %s', device)


def distant_past_ext234_superblock_timestamps(device):
    """Set superblock timestamps of ext[234] filesystem to a distant past."""
    # XXX(asheplyakov): e2fslibs limitation: zero timestamp means "now"
    # rather than "UNIX epoch", therefore use "UNIX epoch + 1 second"
    # instead.
    one_second_past_epoch = time.gmtime(1)
    LOG.debug('Setting superblock timestamps of %s to a distant past', device)
    set_ext234_superblock_timestamps(device,
                                     last_check=one_second_past_epoch,
                                     last_mount=one_second_past_epoch,
                                     last_write=one_second_past_epoch,
                                     created=one_second_past_epoch)
