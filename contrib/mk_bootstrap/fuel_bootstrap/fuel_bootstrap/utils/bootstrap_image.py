# -*- coding: utf-8 -*-

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

import logging
import os
import shutil
import six
import subprocess
import tarfile
import tempfile
import uuid
import yaml

from fuel_agent import manager as fuel_agent_manager
from oslo_config import cfg

from fuel_bootstrap import consts
from fuel_bootstrap import errors
from fuel_bootstrap.utils import data as data_util



LOG = logging.getLogger(__name__)


def get_all():
    data = []
    for name in os.listdir(consts.BOOTSTRAP_IMAGES_DIR):
        bs_image = parse(name)
        if bs_image:
            data.append(bs_image)
    return data


def parse(image_id):
    dir_path = full_path(image_id)
    if os.path.islink(dir_path) or not os.path.isdir(dir_path):
        return None

    metafile = os.path.join(dir_path, consts.METADATA_FILE)
    if not os.path.exists(metafile):
        return None

    with open(metafile) as f:
        data = yaml.load(f)

    if data.get('uuid') != os.path.basename(dir_path):
        return None

    return data


def delete(image_id):
    dir_path = full_path(image_id)
    if is_active(dir_path):
        raise errors.ActiveImageException("The active image can't be deleted")
    shutil.rmtree(dir_path)


def activate(image_id):
    dir_path = full_path(image_id)
    try:
        os.unlink(consts.SYMLINK)
        LOG.debug("Symlink {0} was deleted".format(consts.SYMLINK))
    except OSError as e:
        LOG.warning("Symlink {0} can't be removed"
                    .format(consts.SYMLINK))

    os.symlink(dir_path, consts.SYMLINK)
    LOG.debug("Symlink {0} to {1} directory has been created"
              .format(consts.SYMLINK, dir_path))
    #TODO: dockerctl shell "$container" puppet apply 
    #          --detailed-exitcodes -dv "$manifest"
    command = ["dockerctl", "restart", "cobbler"]
    LOG.debug("Try to restart cobbler")

    try:
        # this should be tested
        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, errors = proc.communicate()
    except OSError as e:
        command_line = ' '.join(command)
        LOG.error("Command '{0}' can't be executed. {1}".
                  format(command_line, e))


def is_active(image_id):
    return full_path(image_id) == os.path.realpath(consts.SYMLINK)


def full_path(image_id):
    if not os.path.isabs(image_id):
        return os.path.join(consts.BOOTSTRAP_IMAGES_DIR, image_id)
    return image_id



def import_image(arch_path):
    extract_dir = tempfile.mkdtemp()
    extract_to_dir(arch_path, extract_dir)

    metafile = os.path.join(extract, consts.METADATA_FILE)

    with open(metafile) as f:
        data = yaml.load(f)

    image_id = data['uuid']
    dir_path = full_path(image_id)

    if os.exists(dir_path):
        raise ImageAlreadyExists("Image with UUID={0} already exists".
                                 format(image_id))

    os.rename(extract_dir, dir_path)


def extract_to_dir(arch_path, extract_path):
    LOG.debug("Try extract {0} to {1}".format(arch_path, extract_path))
    arch = tarfile.open(arch_path, 'r')
    for item in arch:
        arch.extract(item, extract_path)


def make_bootstrap(params):
    bootdata_builder = data_util.BootstrapDataBuilder(params)
    bootdata = bootdata_builder.create_data()

    LOG.info("Try to build image with data={0}".format(bootdata))

    CONF = cfg.CONF
    CONF.data_driver = 'nailgun_build_image'

    manager = fuel_agent_manager.Manager(bootdata)

    manager.do_mkbootstrap()



