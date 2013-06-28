# Copyright 2013 Loop Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import collections

import psutil
# import gevent.subprocess


def make_sampler(dct):
    sampler = None
    if dct['type'] == 'python':
        sampler = PythonSampler(dct['code'])
    elif dct['type'] == 'cpu':
        sampler = CPUSampler(dct.get('pid', None))
    elif dct['type'] == 'memory':
        sampler = MemorySampler(dct.get('pid', None))
    elif dct['type'] == 'task_switches':
        sampler = SwitchSampler(dct.get('pid', None))

    return sampler


class BaseSampler(object):
    def __init__(self):
        self._samples = collections.deque(maxlen=10)
        self.value = 0.0

    def sample(self):
        self._calc_average()

    def _calc_average(self):
        if self._samples:
            s = sum(self._samples)
            self.value = s / float(len(self._samples))


class PythonSampler(BaseSampler):
    def __init__(self, code):
        super(PythonSampler, self).__init__()
        self._code = code

    def sample(self):
        self.value = eval(self._code)
        super(PythonSampler, self).sample()


class CommandSampler(BaseSampler):
    def __init__(self, cmd):
        super(CommandSampler, self).__init__()
        self._cmd = cmd

    def sample(self):
        # TODO: implement command call here
        super(CommandSampler, self).sample()


class ProcessSampler(BaseSampler):
    def __init__(self, pid=None):
        super(ProcessSampler, self).__init__()
        self._pid = pid

        if not self._pid:
            self._pid = os.getpid()

        self._process = None
        try:
            self._process = psutil.Process(self._pid)
        except psutil.NoSuchProcess:
            return

    def sample(self):
        try:
            child_processes = self._process.get_children(recursive=True)
        except psutil.NoSuchProcess:
            return
        child_processes.append(self._process)

        s = 0.0
        for p in child_processes:
            new_s = self._get_sample(p)
            if new_s:
                s += new_s

        self._samples.append(s)
        super(ProcessSampler, self).sample()


class CPUSampler(ProcessSampler):
    def _get_sample(self, p):
        try:
            return p.get_cpu_percent(0.1)
        except psutil.AccessDenied:
            pass


class MemorySampler(ProcessSampler):
    def _get_sample(self, p):
        try:
            return p.get_memory_info()[0]
        except psutil.AccessDenied:
            pass


class SwitchSampler(ProcessSampler):
    def __init__(self, sampler):
        super(SwitchSampler, self).__init__(sampler)
        self._prev = 0

    def _get_sample(self, p):
        try:
            sample = p.get_num_ctx_switches()[0]
            new = sample - self._prev
            self._prev = sample
            return new
        except psutil.AccessDenied:
            pass
