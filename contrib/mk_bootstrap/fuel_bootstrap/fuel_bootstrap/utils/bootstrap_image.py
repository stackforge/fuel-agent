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
import subprocess
import tarfile
import tempfile
import yaml

from oslo_config import cfg

from fuel_bootstrap import consts
from fuel_bootstrap import errors


LOG = logging.getLogger(__name__)


def get_all():
    data = []
    for name in os.listdir(consts.BOOTSTRAP_IMAGES_DIR):
        bs_image = parse(name)
        if bs_image:
            data.append(bs_image)
    print(data)
    return data


def parse(image_id):
    dir_path = full_path(image_id)
    if os.path.islink(dir_path) or not os.path.isdir(dir_path):
        return None

    metafile = os.path.join(dir_path, consts.METADATA_FILE)
    if not os.path.exists(metafile):
        return None

    with open(metafile) as f:
        try:
            data = yaml.load(f)
        except Exception as exc:
            LOG.warning("Couldn't parse metadata file {0} because of {1}"
                        .format(metafile, exc))
            return None
    if data.get('uuid') != os.path.basename(dir_path):
        return None

    data['status'] = 'active' if is_active(data['uuid']) else ''
    return data


def delete(image_id):
    dir_path = full_path(image_id)
    if is_active(dir_path):
        raise errors.ActiveImageException("The active image can't be deleted")
    shutil.rmtree(dir_path)


def is_active(image_id):
    return full_path(image_id) == os.path.realpath(consts.SYMLINK)


def full_path(image_id):
    if not os.path.isabs(image_id):
        return os.path.join(consts.BOOTSTRAP_IMAGES_DIR, image_id)
    return image_id


def import_image(arch_path):
    extract_dir = tempfile.mkdtemp()
    extract_to_dir(arch_path, extract_dir)

    metafile = os.path.join(extract_dir, consts.METADATA_FILE)

    with open(metafile) as f:
        data = yaml.load(f)

    image_id = data['uuid']
    dir_path = full_path(image_id)

    if os.path.exists(dir_path):
        raise errors.ImageAlreadyExists("Image with UUID={0} already exists"
                                        .format(image_id))

    os.rename(extract_dir, dir_path)
    return data['uuid']


def extract_to_dir(arch_path, extract_path):
    LOG.debug("Try extract {0} to {1}".format(arch_path, extract_path))
    arch = tarfile.open(arch_path, 'r')
    arch.extractall(extract_path)
