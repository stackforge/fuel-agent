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
import tarfile
import tempfile
import yaml

from fuel_agent.utils import utils

from fuel_bootstrap import consts
from fuel_bootstrap import errors
from fuel_bootstrap.objects import master_node_settings
from fuel_bootstrap import settings
from fuel_bootstrap.utils import data as data_util

CONF = settings.Configuration()
LOG = logging.getLogger(__name__)
ACTIVE = 'active'


def get_all():
    data = []
    LOG.debug("Searching images in %s", CONF.bootstrap_images_dir)
    for name in os.listdir(CONF.bootstrap_images_dir):
        if not os.path.isdir(os.path.join(CONF.bootstrap_images_dir, name)):
            continue
        try:
            data.append(parse(name))
        except errors.IncorrectImage as e:
            LOG.debug("Image [%s] is skipped due to %s", name, e)
    return data


def parse(image_id):
    LOG.debug("Trying to parse [%s] image", image_id)
    dir_path = full_path(image_id)
    if os.path.islink(dir_path) or not os.path.isdir(dir_path):
        raise errors.IncorrectImage("There are no such image [{0}]."
                                    .format(image_id))

    metafile = os.path.join(dir_path, consts.METADATA_FILE)
    if not os.path.exists(metafile):
        raise errors.IncorrectImage("Image [{0}] doen's contain metadata file."
                                    .format(image_id))

    with open(metafile) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise errors.IncorrectImage("Couldn't parse metadata file for"
                                        " image [{0}] due to {1}"
                                        .format(image_id, e))
    if data.get('uuid') != os.path.basename(dir_path):
        raise errors.IncorrectImage("UUID from metadata file [{0}] doesn't"
                                    " equal directory name [{1}]"
                                    .format(data.get('uuid'), image_id))

    data['status'] = ACTIVE if is_active(data['uuid']) else ''
    return data


def delete(image_id):
    dir_path = full_path(image_id)
    image = parse(image_id)
    if image['status'] == ACTIVE:
        raise errors.ActiveImageException("Image [{0}] is active and can't be"
                                          " deleted.".format(image_id))

    shutil.rmtree(dir_path)
    return image_id


def is_active(image_id):
    return full_path(image_id) == os.path.realpath(
        CONF.active_bootstrap_symlink)


def full_path(image_id):
    if not os.path.isabs(image_id):
        return os.path.join(CONF.bootstrap_images_dir, image_id)
    return image_id


def import_image(arch_path):
    extract_dir = tempfile.mkdtemp()
    extract_to_dir(arch_path, extract_dir)

    metafile = os.path.join(extract_dir, consts.METADATA_FILE)

    with open(metafile) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise errors.IncorrectImage("Couldn't parse metadata file"
                                        " due to {0}".format(e))

    image_id = data['uuid']
    dir_path = full_path(image_id)

    if os.path.exists(dir_path):
        raise errors.ImageAlreadyExists("Image [{0}] already exists."
                                        .format(image_id))

    shutil.move(extract_dir, dir_path)

    return image_id


def extract_to_dir(arch_path, extract_path):
    LOG.info("Try extract %s to %s", arch_path, extract_path)
    tarfile.open(arch_path, 'r').extractall(extract_path)


def make_bootstrap(data={}):
    bootdata_builder = data_util.BootstrapDataBuilder(data)
    bootdata = bootdata_builder.build()

    LOG.info("Try to build image with data:\n%s", yaml.safe_dump(bootdata))

    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump(bootdata))
        f.flush()
        utils.execute('fa_mkbootstrap', '--nouse-syslog', '--data_driver',
                      'bootstrap_build_image', '--nodebug', '-v',
                      '--image_build_dir', data['image_build_dir'],
                      '--input_data_file', f.name)

    return bootdata['bootstrap']['uuid'], bootdata['output']


def activate(image_id=None):
    dir_path = full_path(image_id)
    symlink = CONF.active_bootstrap_symlink

    try:
        os.unlink(symlink)
        LOG.debug("Symlink %s was deleted", symlink)
    except OSError as e:
        LOG.warning("Symlink %s can't be removed due to %s", symlink, e)

    os.symlink(dir_path, symlink)
    LOG.debug("Symlink %s to %s directory has been created",
              symlink,
              dir_path)

    # FIXME: Do normal activation when it become clear how to do it
    utils.execute('fuel-bootstrap-image-set', 'ubuntu')

    return image_id


def call_wrapped_method(name, notify_webui, **kwargs):
    wrapped_methods = {
        'build': make_bootstrap,
        'activate': activate
    }
    failed = False
    try:
        return wrapped_methods[name](**kwargs)
    except Exception:
        failed = True
        raise
    finally:
        if notify_webui:
            notify_webui_about_results(failed, consts.ERROR_MSG)


def notify_webui_about_results(failed, error_message):
    mn_settings = master_node_settings.MasterNodeSettings()
    settings = mn_settings.get()
    settings.setdefault('bootstrap', {}).setdefault('error', {})
    if failed:
        settings['bootstrap']['error']['value'] = error_message
    else:
        settings['bootstrap']['error']['value'] = ""
    mn_settings.update(settings)
