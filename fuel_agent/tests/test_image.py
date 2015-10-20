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


import six
import unittest2

from fuel_agent import errors
from fuel_agent.objects import image

if six.PY2:
    import mock
elif six.PY3:
    import unittest.mock as mock


class TestImage(unittest2.TestCase):

    def test_unsupported_container(self):
        self.assertRaises(errors.WrongImageDataError, image.Image, 'uri',
                          'dev', 'format', 'unsupported')

    @mock.patch('fuel_agent.objects.image.bu', create=True)
    def test_attach_tmp_file_to_loop_device(self, mock_image_bu):
        target_device = '/dev/loop0'
        img = image.Image(None, target_device, None, 'raw')
        img.img_tmp_file = tmp_file = '/tmp/file'

        img.attach_tmp_file_to_loop_device()

        mock_image_bu.attach_file_to_loop.assert_called_once_with(
            tmp_file, target_device)
        self.assertTrue(img.is_tmp_file_attached())

    @mock.patch('fuel_agent.objects.image.bu', create=True)
    def test_deattach_tmp_file_from_loop_device(self, mock_image_bu):
        target_device = '/dev/loop0'
        img = image.Image(None, target_device, None, 'raw')
        img.img_tmp_file = '/tmp/file'

        img.deattach_tmp_file_from_loop_device()

        mock_image_bu.deattach_loop.assert_called_once_with(
            target_device)
        self.assertFalse(img.is_tmp_file_attached())

    @mock.patch('fuel_agent.objects.image.bu', create=True)
    def test_attaching_and_deattaching(self, mock_image_bu):
        target_device = '/dev/loop0'
        img = image.Image(None, target_device, None, 'raw')
        img.img_tmp_file = '/tmp/file'

        self.assertFalse(img.is_tmp_file_attached())
        img.attach_tmp_file_to_loop_device()
        self.assertTrue(img.is_tmp_file_attached())
        img.deattach_tmp_file_from_loop_device()
        self.assertFalse(img.is_tmp_file_attached())
