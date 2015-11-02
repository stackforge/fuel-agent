#    Copyright 2015 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import gzip
import os
import re
import shutil
import signal as sig
import stat
import tempfile
import time

import signal
import six
import yaml

from fuel_agent import errors
from fuel_agent.openstack.common import log as logging
from fuel_agent.utils import fs as fu
from fuel_agent.utils import hardware as hu
from fuel_agent.utils import utils


LOG = logging.getLogger(__name__)

DEFAULT_APT_PATH = {
    'sources_file': 'etc/apt/sources.list',
    'sources_dir': 'etc/apt/sources.list.d',
    'preferences_file': 'etc/apt/preferences',
    'preferences_dir': 'etc/apt/preferences.d',
    'conf_dir': 'etc/apt/apt.conf.d',
}
# protocol : conf_file_name
PROXY_PROTOCOLS = {
    'ftp': '01fuel_agent-use-proxy-ftp',
    'http': '01fuel_agent-use-proxy-http',
    'https': '01fuel_agent-use-proxy-https'
}
# NOTE(agordeev): hardcoded to r00tme
ROOT_PASSWORD = '$6$IInX3Cqo$5xytL1VZbZTusOewFnG6couuF0Ia61yS3rbC6P5YbZP2TYcl'\
                'wHqMq9e3Tg8rvQxhxSlBXP1DZhdUamxdOBXK0.'


def run_debootstrap(uri, suite, chroot, arch='amd64', eatmydata=False,
                    attempts=10, proxies=None, direct_repo_addr=None):
    """Builds initial base system.

    debootstrap builds initial base system which is capable to run apt-get.
    debootstrap is well known for its glithcy resolving of package dependecies,
    so the rest of packages will be installed later by run_apt_get.
    """
    env_vars = copy.deepcopy(os.environ)
    if proxies:
        for proto in six.iterkeys(PROXY_PROTOCOLS):
            if proto in proxies:
                LOG.debug('Using {0} proxy {1} for debootstrap'.format(
                    proto, proxies[proto]))
                env_vars['{0}_proxy'.format(proto)] = proxies[proto]

    if direct_repo_addr:
        LOG.debug('Setting no_proxy for: {0}'.format(direct_repo_addr))
        env_vars['no_proxy'] = direct_repo_addr

    cmds = ['debootstrap', '--verbose', '--no-check-gpg',
            '--arch={0}'.format(arch)]
    if eatmydata:
        cmds.extend(['--include=eatmydata'])
    cmds.extend([suite, chroot, uri])
    stdout, stderr = utils.execute(*cmds, attempts=attempts,
                                   env_variables=env_vars)
    LOG.debug('Running deboostrap completed.\nstdout: %s\nstderr: %s', stdout,
              stderr)


def set_apt_get_env():
    # NOTE(agordeev): disable any confirmations/questions from apt-get side
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    os.environ['DEBCONF_NONINTERACTIVE_SEEN'] = 'true'
    os.environ['LC_ALL'] = os.environ['LANG'] = os.environ['LANGUAGE'] = 'C'


def run_apt_get(chroot, packages, eatmydata=False, attempts=10):
    """Runs apt-get install <packages>.

    Unlike debootstrap, apt-get has a perfect package dependecies resolver
    under the hood.
    eatmydata could be used to totally ignore the storm of sync() calls from
    dpkg/apt-get tools. It's dangerous, but could decrease package install
    time in X times.
    """
    for action in ('update', 'dist-upgrade'):
        cmds = ['chroot', chroot, 'apt-get', '-y', action]
        stdout, stderr = utils.execute(*cmds, attempts=attempts)
        LOG.debug('Running apt-get %s completed.\nstdout: %s\nstderr: %s',
                  action, stdout, stderr)
    cmds = ['chroot', chroot, 'apt-get', '-y', 'install', ' '.join(packages)]
    if eatmydata:
        cmds.insert(2, 'eatmydata')
    stdout, stderr = utils.execute(*cmds, attempts=attempts)
    LOG.debug('Running apt-get install completed.\nstdout: %s\nstderr: %s',
              stdout, stderr)


def suppress_services_start(chroot):
    """Suppresses services start.

    Prevents start of any service such as udev/ssh/etc in chrooted environment
    while image is being built.
    """
    path = os.path.join(chroot, 'usr/sbin')
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, 'policy-rc.d'), 'w') as f:
        f.write('#!/bin/sh\n'
                '# prevent any service from being started\n'
                'exit 101\n')
        os.fchmod(f.fileno(), 0o755)


def clean_dirs(chroot, dirs, delete=False):
    """Removes dirs and recreates them

    :param chroot: Root directory where to look for subdirectories
    :param dirs: List of directories to clean/remove (Relative to chroot)
    :param delete: (Boolean) If True, directories will be removed
    (Default: False)
    """
    for d in dirs:
        path = os.path.join(chroot, d)
        if os.path.isdir(path):
            LOG.debug('Removing dir: %s', path)
            shutil.rmtree(path)
            if not delete:
                LOG.debug('Creating empty dir: %s', path)
                os.makedirs(path)


def remove_files(chroot, files):
    for f in files:
        path = os.path.join(chroot, f)
        if os.path.exists(path):
            os.remove(path)
            LOG.debug('Removed file: %s', path)


def clean_apt_settings(chroot, allow_unsigned_file='allow_unsigned_packages',
                       force_ipv4_file='force_ipv4'):
    """Cleans apt settings such as package sources and repo pinning."""
    files = [DEFAULT_APT_PATH['sources_file'],
             DEFAULT_APT_PATH['preferences_file'],
             os.path.join(DEFAULT_APT_PATH['conf_dir'], force_ipv4_file),
             os.path.join(DEFAULT_APT_PATH['conf_dir'], allow_unsigned_file)]
    # also remove proxies
    for p_file in six.itervalues(PROXY_PROTOCOLS):
        files.extend(os.path.join(DEFAULT_APT_PATH['conf_dir'],
                                  p_file).split())
    remove_files(chroot, files)
    dirs = [DEFAULT_APT_PATH['preferences_dir'],
            DEFAULT_APT_PATH['sources_dir']]
    clean_dirs(chroot, dirs)


def do_post_inst(chroot, allow_unsigned_file='allow_unsigned_packages',
                 force_ipv4_file='force_ipv4', fix_puppet=True):
    # NOTE(agordeev): set up password for root
    utils.execute('sed', '-i',
                  's%root:[\*,\!]%root:' + ROOT_PASSWORD + '%',
                  os.path.join(chroot, 'etc/shadow'))
    # NOTE(agordeev): backport from bash-script:
    # in order to prevent the later puppet workflow outage, puppet service
    # should be disabled on a node startup.
    # Being enabled by default, sometimes it leads to puppet service hanging
    # and recognizing the deployment as failed.
    if fix_puppet:
        # we don't have puppet in bootstrap
        # TODO(agordeev): take care of puppet service for other distros, once
        # fuel-agent will be capable of building images for them too.
        utils.execute('chroot', chroot, 'update-rc.d', 'puppet', 'disable')
    # NOTE(agordeev): disable mcollective to be automatically started on boot
    # to prevent confusing messages in its log (regarding connection errors).
    with open(os.path.join(chroot, 'etc/init/mcollective.override'), 'w') as f:
        f.write("manual\n")
    # NOTE(agordeev): remove custom policy-rc.d which is needed to disable
    # execution of post/pre-install package hooks and start of services
    remove_files(chroot, ['usr/sbin/policy-rc.d'])
    clean_apt_settings(chroot, allow_unsigned_file=allow_unsigned_file,
                       force_ipv4_file=force_ipv4_file)


def stop_chrooted_processes(chroot, signal=sig.SIGTERM,
                            attempts=10, attempts_delay=2):
    """Sends signal to all processes, which are running inside chroot.

    It tries several times until all processes die. If at some point there
    are no running processes found, it returns True.

    :param chroot: Process root directory.
    :param signal: Which signal to send to processes. It must be either
    SIGTERM or SIGKILL. (Default: SIGTERM)
    :param attempts: Number of attempts (Default: 10)
    :param attempts_delay: Delay between attempts (Default: 2)
    """

    if signal not in (sig.SIGTERM, sig.SIGKILL):
        raise ValueError('Signal must be either SIGTERM or SIGKILL')

    def get_running_processes():
        return utils.execute(
            'fuser', '-v', chroot, check_exit_code=False)[0].split()

    for i in six.moves.range(attempts):
        running_processes = get_running_processes()
        if not running_processes:
            LOG.debug('There are no running processes in %s ', chroot)
            return True
        for p in running_processes:
            try:
                pid = int(p)
                if os.readlink('/proc/%s/root' % pid) == chroot:
                    LOG.debug('Sending %s to chrooted process %s', signal, pid)
                    os.kill(pid, signal)
            except (OSError, ValueError) as e:
                cmdline = ''
                pid = p
                try:
                    with open('/proc/%s/cmdline' % pid) as f:
                        cmdline = f.read()
                except Exception:
                    LOG.debug('Can not read cmdline for pid=%s', pid)
                LOG.warning('Exception while sending signal: '
                            'pid: %s cmdline: %s message: %s. Skipping it.',
                            pid, cmdline, e)

        # First of all, signal delivery is asynchronous.
        # Just because the signal has been sent doesn't
        # mean the kernel will deliver it instantly
        # (the target process might be uninterruptible at the moment).
        # Secondly, exiting might take a while (the process might have
        # some data to fsync, etc)
        LOG.debug('Attempt %s. Waiting for %s seconds', i + 1, attempts_delay)
        time.sleep(attempts_delay)

    running_processes = get_running_processes()
    if running_processes:
        for pid in running_processes:
            cmdline = ''
            try:
                with open('/proc/%s/cmdline' % pid) as f:
                    cmdline = f.read()
            except Exception:
                LOG.debug('Can not read cmdline for pid=%s', pid)
            LOG.warning('Process is still running: pid=%s cmdline: %s',
                        pid, cmdline)
        return False
    return True


def get_free_loop_device(loop_device_major_number=7,
                         max_loop_devices_count=255):
    """Returns the name of free loop device.

    It should return the name of free loop device or raise an exception.
    Unfortunately, free loop device couldn't be reversed for the later usage,
    so we must start to use it as fast as we can.
    If there's no free loop it will try to create new one and ask a system for
    free loop again.
    """
    for minor in range(0, max_loop_devices_count):
        cur_loop = "/dev/loop%s" % minor
        if not os.path.exists(cur_loop):
            os.mknod(cur_loop, 0o660 | stat.S_IFBLK,
                     os.makedev(loop_device_major_number, minor))
        try:
            return utils.execute('losetup', '--find')[0].split()[0]
        except (IndexError, errors.ProcessExecutionError):
            LOG.debug("Couldn't find free loop device, trying again")
    raise errors.NoFreeLoopDevices('Free loop device not found')


def populate_basic_dev(chroot):
    """Populates /dev with basic files, links, device nodes."""
    # prevent failures related with /dev/fd/62
    utils.execute('chroot', chroot, 'rm', '-fr', '/dev/fd')
    utils.execute('chroot', chroot,
                  'ln', '-s', '/proc/self/fd', '/dev/fd')


def create_sparse_tmp_file(dir, suffix, size=8192):
    """Creates sparse file.

    Creates file which consumes disk space more efficiently when the file
    itself is mostly empty.
    """
    tf = tempfile.NamedTemporaryFile(dir=dir, suffix=suffix, delete=False)
    utils.execute('truncate', '-s', '%sM' % size, tf.name)
    return tf.name


def attach_file_to_loop(filename, loop):
    utils.execute('losetup', loop, filename)


def deattach_loop(loop, check_exit_code=[0]):
    LOG.debug('Trying to figure out if loop device %s is attached', loop)
    output = utils.execute('losetup', '-a')[0]
    for line in output.split('\n'):
        # output lines are assumed to have the following format
        # /dev/loop0: [fd03]:130820 (/dev/loop0)
        if loop == line.split(':')[0]:
            LOG.debug('Loop device %s seems to be attached. '
                      'Trying to detach.', loop)
            utils.execute('losetup', '-d', loop,
                          check_exit_code=check_exit_code)


def shrink_sparse_file(filename):
    """Shrinks file to its size of actual data. Only ext fs are supported."""
    utils.execute('e2fsck', '-y', '-f', filename)
    utils.execute('resize2fs', '-F', '-M', filename)
    data = hu.parse_simple_kv('dumpe2fs', filename)
    block_count = int(data['block count'])
    block_size = int(data['block size'])
    with open(filename, 'rwb+') as f:
        f.truncate(block_count * block_size)


def strip_filename(name):
    """Strips filename for apt settings.

    The name could only contain alphanumeric, hyphen (-), underscore (_) and
    period (.) characters.
    """
    return re.sub(r"[^a-zA-Z0-9-_.]*", "", name)


def get_release_file(uri, suite, section):
    """Download and parse repo's Release file

    It and returns an apt preferences line for specified repo.

    :param repo: a repo as dict
    :returns: a string with apt preferences rules
    """
    if section:
        # We can't use urljoin here because it works pretty bad in
        # cases when 'uri' doesn't have a trailing slash.
        download_uri = os.path.join(uri, 'dists', suite, 'Release')
    else:
        # Well, we have a flat repo case, so we should download Release
        # file from a different place. Please note, we have to strip
        # a leading slash from suite because otherwise the download
        # link will be wrong.
        download_uri = os.path.join(uri, suite.lstrip('/'), 'Release')

    return utils.init_http_request(download_uri).text


def parse_release_file(content):
    """Parse Debian repo's Release file content.

    :param content: a Debian's Release file content
    :returns: a dict with repo's attributes
    """
    _multivalued_fields = {
        'SHA1': ['sha1', 'size', 'name'],
        'SHA256': ['sha256', 'size', 'name'],
        'SHA512': ['sha512', 'size', 'name'],
        'MD5Sum': ['md5sum', 'size', 'name'],
    }

    # debian data format is very similiar to yaml, except
    # multivalued field. so we can parse it just like yaml
    # and then perform additional transformation for those
    # fields (we know which ones are multivalues).
    data = yaml.load(content)

    for attr, columns in six.iteritems(_multivalued_fields):
        if attr not in data:
            continue

        values = data[attr].split()
        data[attr] = []

        for group in utils.grouper(values, len(columns)):
            data[attr].append(dict(zip(columns, group)))

    return data


def add_apt_source(name, uri, suite, section, chroot):
    # NOTE(agordeev): The files have either no or "list" as filename extension
    filename = 'fuel-image-{name}.list'.format(name=strip_filename(name))
    if section:
        entry = 'deb {uri} {suite} {section}\n'.format(uri=uri, suite=suite,
                                                       section=section)
    else:
        entry = 'deb {uri} {suite}\n'.format(uri=uri, suite=suite)
    with open(os.path.join(chroot, DEFAULT_APT_PATH['sources_dir'], filename),
              'w') as f:
        f.write(entry)


def add_apt_preference(name, priority, suite, section, chroot, uri):
    # NOTE(agordeev): The files have either no or "pref" as filename extension
    filename = 'fuel-image-{name}.pref'.format(name=strip_filename(name))
    # NOTE(agordeev): priotity=None means that there's no specific pinning for
    # particular repo and nothing to process.
    # Default system-wide preferences (priority=500) will be used instead.

    _transformations = {
        'Archive': 'a',
        'Suite': 'a',       # suite is a synonym for archive
        'Codename': 'n',
        'Version': 'v',
        'Origin': 'o',
        'Label': 'l',
    }

    try:
        deb_release = parse_release_file(
            get_release_file(uri, suite, section)
        )
    except ValueError as exc:
        LOG.error(
            "[Attention] Failed to fetch Release file "
            "for repo '{0}': {1} - skipping. "
            "This may lead both to trouble with packages "
            "and broken OS".format(name, six.text_type(exc))
        )
        return

    conditions = set()
    for field, condition in six.iteritems(_transformations):
        if field in deb_release:
            conditions.add(
                '{0}={1}'.format(condition, deb_release[field])
            )

    with open(os.path.join(chroot, DEFAULT_APT_PATH['preferences_dir'],
                           filename), 'w') as f:
        f.write('Package: *\n')
        f.write('Pin: release ')
        f.write(', '.join(conditions) + "\n")
        f.write('Pin-Priority: {priority}\n'.format(priority=priority))


def set_apt_proxy(chroot, proxies, direct_repo_addr=None):
    """Configure proxy for apt-config

    direct_repo_addr:: direct apt address:
    access to it bypass proxies.
    """

    def set_proxy(protocol):
        with open(os.path.join(chroot, DEFAULT_APT_PATH['conf_dir'],
                               PROXY_PROTOCOLS[protocol]), 'w') as f:
                f.write('Acquire::{0}::proxy "{1}";\n'
                        ''.format(protocol, proxies[protocol]))
                LOG.debug('Apply apt-proxy: \nprotocol: {0}\nurl: {1}'
                          ''.format(protocol, proxies[protocol]))
                if direct_repo_addr:
                    f.write('Acquire::{0}::proxy::{1} "DIRECT";\n'
                            ''.format(protocol, direct_repo_addr))
                    LOG.debug('Set DIRECT repo: \nprotocol: {0}\nurl: {1}'
                              ''.format(protocol, direct_repo_addr))
    if not proxies:
        return

    for proto in six.iterkeys(proxies):
        set_proxy(proto)


def pre_apt_get(chroot, allow_unsigned_file='allow_unsigned_packages',
                force_ipv4_file='force_ipv4',
                proxies=None, direct_repo_addr=None):
    """It must be called prior run_apt_get."""
    clean_apt_settings(chroot, allow_unsigned_file=allow_unsigned_file,
                       force_ipv4_file=force_ipv4_file)
    # NOTE(agordeev): allow to install packages without gpg digest
    with open(os.path.join(chroot, DEFAULT_APT_PATH['conf_dir'],
                           allow_unsigned_file), 'w') as f:
        f.write('APT::Get::AllowUnauthenticated 1;\n')
    with open(os.path.join(chroot, DEFAULT_APT_PATH['conf_dir'],
                           force_ipv4_file), 'w') as f:
        f.write('Acquire::ForceIPv4 "true";\n')

    set_apt_proxy(chroot, proxies, direct_repo_addr)


def containerize(filename, container, chunk_size=1048576):
    if container == 'gzip':
        output_file = filename + '.gz'
        with open(filename, 'rb') as f:
            # NOTE(agordeev): gzip in python2.6 doesn't have context manager
            # support
            g = gzip.open(output_file, 'wb')
            for chunk in iter(lambda: f.read(chunk_size), ''):
                g.write(chunk)
            g.close()
        os.remove(filename)
        return output_file
    raise errors.WrongImageDataError(
        'Error while image initialization: '
        'unsupported image container: {container}'.format(container=container))


def attach_file_to_free_loop_device(filename, max_loop_devices_count=255,
                                    loop_device_major_number=7,
                                    max_attempts=1):
    """Find free loop device and try to attach `filename` to it.

    If attaching fails then retry again. Max allowed attempts is
    `max_attempts`.

    Returns loop device to which file is attached. Otherwise, raises
    errors.NoFreeLoopDevices.
    """
    loop_device = None
    for i in range(0, max_attempts):
        try:
            LOG.debug('Looking for a free loop device')
            loop_device = get_free_loop_device(
                loop_device_major_number=loop_device_major_number,
                max_loop_devices_count=max_loop_devices_count)

            log_msg = "Attaching image file '{0}' to free loop device '{1}'"
            LOG.debug(log_msg.format(filename, loop_device))
            attach_file_to_loop(filename, loop_device)
            break
        except errors.ProcessExecutionError:
            log_msg = "Couldn't attach image file '{0}' to loop device '{1}'."
            LOG.debug(log_msg.format(filename, loop_device))

            if i == max_attempts - 1:
                log_msg = ("Maximum allowed attempts ({0}) to attach image "
                           "file '{1}' to loop device '{2}' is exceeded.")
                LOG.debug(log_msg.format(max_attempts, filename, loop_device))
                raise errors.NoFreeLoopDevices('Free loop device not found.')
            else:
                log_msg = ("Trying again to attach image file '{0}' "
                           "to free loop device '{1}'. "
                           "Attempt #{2} out of {3}")
                LOG.debug(log_msg.format(filename, loop_device,
                                         i + 1, max_attempts))

    return loop_device


def folder_to_tar_gz(d_input, d_output, name):
    o_file = os.path.join(os.path.normpath(d_output), name + '.tgz')
    LOG.info('Creating archive: %s', o_file)
    try:
        utils.execute('tar', '-czf', o_file, '--directory',
                      os.path.normcase(d_input), '.', logged=True)
        LOG.info('Creating archive finished: %s', o_file)
    except Exception as exc:
        LOG.error('Failed to create archive: %s', exc)
        raise
    return o_file


def run_script_in_chroot(chroot, script):

    LOG.info('Copy user-script {0} into chroot:{1}'.format(script, chroot))

    utils.execute('cp', '-r', script, chroot)
    LOG.info('Make user-script {0} executable:'.format(script))
    utils.execute('chmod', '0755', os.path.join(chroot, os.path.basename(
        script)))

    stdout, stderr = utils.execute(
        'chroot', chroot, '/bin/bash', '-c', os.path.join(
            '/', os.path.basename(script)))
    LOG.debug('Running user-script completed: \nstdout: {0}\nstderr: {1}'.
              format(stdout, stderr))


def recompress_initramfs(chroot, compress):

    LOG.info('Change initramfs compression type to:{0}'.format(compress))
    utils.execute(
        'sed', '-i', 's/COMPRESS\s*=\s*gzip/COMPRESS={0}/'.format(compress),
        os.path.join(chroot, 'etc/initramfs-tools/initramfs.conf'))

    stdout, stderr = utils.execute(
        'find', os.path.join(chroot, 'boot/'), '-iname', '"initrd*"',
        '-exec', 'rm', '-vf', '{} \;')

    LOG.info('Removing old initramfs completed: \nstdout:{0}'
             '\nstderr:{1}'.format(stdout, stderr))

    cmds = ['chroot', chroot, 'update-initramfs -v -c -k all']

    stdout, stderr = utils.execute(*cmds,
                                   env_variables={'TMPDIR': '/tmp',
                                                  'TMP': '/tmp'})
    LOG.debug('Running "update-initramfs" completed.\nstdout: '
              '%s\nstderr: %s', stdout, stderr)


def propagate_host_resolv_conf(chroot):
    """Backup hosts/resolv files in chroot

    i have no idea why we need this hack :( "
    opposite to restore_resolv_conf
    """
    c_etc = os.path.join(chroot, 'etc/')

    utils.makedirs_if_not_exists(c_etc)
    for conf in ('resolv.conf', 'hosts'):
        if os.path.isfile(os.path.join(c_etc, conf)):
            LOG.info('Disabling default {0} inside chroot'.format(conf))
            utils.execute('cp', '-va', os.path.join(c_etc, conf),
                          os.path.join(c_etc, conf) + '.bup',
                          logged=True)


def restore_resolv_conf(chroot):
    """restore hosts/resolv files in chroot """

    # opposite to propagate_host_resolv_conf

    c_etc = os.path.join(chroot, '/etc/')
    utils.makedirs_if_not_exists(c_etc)
    for conf in 'resolv.conf' 'hosts':
        if os.path.isfile(c_etc + conf + '.bup'):
            LOG.info('Restoring default {0} inside chroot'.format(conf))
            utils.execute(
                'mv', '-vfa', os.path.join(c_etc, conf) + '.bup',
                os.path.join(c_etc, conf), logged=True)


def populate_squashfs(chroot, compress, dstdir):
    """Create squashfs

    1)Mount tmpfs under chroot/mnt
    2)run mksquashfs inside a chroot
    3)move result files to dstdir

    :return:
    """
    # TODO(azvyagintsev) fetch from uri driver
    files = {'squashfs': 'root.squashfs',
             'kernel': 'vmlinuz',
             'initrd': 'initrd.img'
             }
    temp = 'squashfs_tmp'

    s_dst = os.path.join(chroot, 'mnt/dst/')
    s_src = os.path.join(chroot, 'mnt/src/')
    try:
        utils.execute(
            'find', os.path.join(chroot, 'boot/'),
            '-maxdepth 1', '-type', 'f', '\( -iname', '"initrd*"', '-o -iname',
            '"vmlinuz*" \)', '-exec', 'sh', '-c',
            '"cp -va {{}} {0}/`basename {{}}`.{1}" \;'.format(
                os.path.normcase(dstdir), temp), logged=True)

        utils.execute(
            'find', os.path.join(chroot, 'boot/'),
            '-maxdepth 1', '-type', 'f', '\( -iname', '"initrd*"',
            '-o -iname', '"vmlinuz*" \)', '-exec', 'rm -vf {} \;', logged=True)

        fu.mount_fs(
            'tmpfs', 'mnt_{0}'.format(temp),
            (os.path.join(chroot, 'mnt/'.format(temp))),
            'rw,nodev,nosuid,noatime,mode=0755,size=4M')

        utils.makedirs_if_not_exists(s_src)
        utils.makedirs_if_not_exists(s_dst)
        fu.mount_bind(s_src, chroot, ' ')

        fu.mount_fs(None, None, s_src, 'remount,bind,ro')
        fu.mount_bind(s_dst, dstdir, ' ')
        utils.execute(
            'chroot', chroot, 'mksquashfs', '/mnt/src',
            '/mnt/dst/{0}.{1}'.format(files['squashfs'], temp),
            '-comp {0} -no-progress -noappend'.format(compress), logged=True)
        # move to result names
        for file in six.iterkeys(files):
            utils.execute(
                'find', s_dst, '-maxdepth 1', '-type', 'f',
                '-iname "{0}*"'.format(files[file]), '-exec', 'sh', '-c',
                '" mv -v {{}} {0}/{1} " \;'.format(os.path.normcase(dstdir),
                                                   files[file]), logged=True)

    except Exception as exc:
        LOG.error('squashfs_image build failed: %s', exc)
        raise
    finally:
        LOG.info('squashfs_image clean-up')
        stop_chrooted_processes(chroot, signal=signal.SIGTERM)
        fu.umount_fs(os.path.join(chroot, 'mnt/dst/'))
        fu.umount_fs(os.path.join(chroot, 'mnt/src/'))
        fu.umount_fs(os.path.join(chroot, 'mnt/'))


def dpkg_list(chroot):
    """return simple dpkg list"""
    stdout, stderr = utils.execute('chroot', chroot, 'dpkg-query',
                                   '-W -f=\'${Package} ${Version}\\t\' ')
    # split, output will be = package - version
    p_list = stdout.split('\t')
    # remove last empty ''
    p_list.pop()

    p_dict = {}
    for item in p_list:
        p_dict[item.split(' ')[0]] = item.split(' ')[1]
    return p_dict


def create_temp_chroot_directory(root_dir, suffix):
    LOG.debug('Creating temporary chroot directory')
    utils.makedirs_if_not_exists(root_dir)
    chroot = tempfile.mkdtemp(
        dir=root_dir, suffix=suffix)
    LOG.debug('Temporary chroot dir: %s', chroot)
    return chroot


def dump_mkbootstrap_yaml(metadata, c_dir):
    """fetch some data rom metadata

    :param c_dir: folder,where yaml should be saved
    """

    drop_data = {'modules': {}}
    for module in metadata['bootstrap_modules']:
        fname = os.path.basename(metadata['bootstrap_modules']
                                 [module]['uri'])
        fs_file = os.path.join(c_dir, fname)
        try:
            raw_size = os.path.getsize(fs_file)
        except IOError as exc:
            LOG.error('There was an error while getting file size: {0}'.format(
                exc))
            raise
        raw_md5 = utils.calculate_md5(fs_file, raw_size)
        drop_data['modules'][module] = {
            'raw_md5': raw_md5,
            'raw_size': raw_size,
            'file': fname,
            'uri': metadata['bootstrap_modules'][module]['uri']
        }

    drop_data['uuid'] = metadata['uuid']
    drop_data['os'] = metadata['os']
    drop_data['extend_kopts'] = metadata['extend_kopts']
    drop_data['all_packages'] = metadata['all_packages']
    drop_data['repos'] = metadata['raw_repos']

    LOG.debug('Image metadata: %s', drop_data)
    with open(os.path.join(c_dir, metadata['meta_file']),
              'wt') as f:
        yaml.safe_dump(drop_data, stream=f, encoding='utf-8')
