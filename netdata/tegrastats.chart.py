#!/usr/bin/env python
# Author: Tom Stephens
# -*- coding: UTF-8 -*-
# The majority of the data parsing here is copy/paste with required adjustment for netdata needs
# Thanks to Raffaello Bonghi <raffaello@rnext.it> for a lot of the real work
# https://github.com/rbonghi/jetson_stats/blob/master/jtop/jstatslib.py

from bases.FrameworkServices.SimpleService import SimpleService
import re
import os
import subprocess

# default module values
# update_every = 4
priority = 90000
retries = 60

ORDER = [
    'cpu',
    'cpufreq',
    'ram',
    # 'lfb',
    'swap',
    'iram',
    'gpu',
    # 'gpufreq',
    'emc',
    # 'emcfreq',
    'mts',
    # 'ape',
    'temperatures',
    'power'
    ]
CHARTS = {
    'cpu': {
        'options': [None, 'CPU Utilizaton', '%', 'utilization', 'utilization.cpu', 'line'],
        'lines': [] 
    },
    'cpufreq': {
        'options': [None, 'CPU Clock', 'MHz', 'freq', 'cpufreq.cpufreq', 'line'],
        'lines': [] 
    },
    'ram': {
        'options': [None, 'RAM Utilizaton', '%', 'utilization', 'utilization.ram', 'line'],
        'lines': [
            ['ram_used', 'used', 'absolute']
        ]
    },
    # 'lfb': {
    #     'options': [None, 'Largest Free Block', 'Count', 'lfb', 'lfb','line'],
    #     'lines': [
    #         ['lfb_count', 'lfb_count', 'absolute', 1, 1000]
    #     ]
    # },
    'swap': {
        'options': [None, 'SWAP', 'MB', 'swap', 'swap','line'],
        'lines': [
            ['swap_cached', 'cached', 'absolute']
        ]
    },
    'iram': {
        'options': [None, 'SWAP', 'MB', 'swap', 'swap','line'],
        'lines': [] 
    },
    'gpu': {
        'options': [None, 'GPU Utilizaton', '%', 'utilization', 'utilization.gpu', 'line'],
        'lines': [
            ['gpu', 'gpu', 'absolute']
        ] 
    },
    # 'gpufreq': {
    #     'options': [None, 'GPU Clock', 'MHz', 'freq', 'gpufreq.gpufreq', 'line'],
    #     'lines': [
    #         ['gpufreq', 'gpu', 'absolute', 1, 1000]
    #     ] 
    # },
    'emc': {
        'options': [None, 'EMC Utilizaton', '%', 'utilization', 'utilization.emc', 'line'],
        'lines': [
            ['emc', 'emc', 'absolute']
        ] 
    },
    # 'emcfreq': {
    #     'options': [None, 'EMC Clock', 'MHz', 'freq', 'emcfreq.emcfreq', 'line'],
    #     'lines': [
    #         ['emcfreq', 'emc', 'absolute', 1, 1000]
    #     ] 
    # },
    'mts': {
        'options': [None, 'MTS Utilizaton', '%', 'utilization', 'utilization.mts', 'line'],
        'lines': [
            ['mts_fg', 'mts_fg', 'absolute'],
            ['mts_bg', 'mts_bg', 'absolute']
        ] 
    },
    # 'ape': {
    #     'options': [None, 'Audio Processing Engine', 'Mhz', 'freq', 'apefreq.apefreq', 'line'],
    #     'lines': [
    #         ['ape', 'freq', 'absolute', 1, 1000]
    #     ] 
    # },
    'temperatures': {
        'options': [None, 'Temperature', 'Celsius', 'temperature', 'sensors.temperature', 'line'],
        'lines': []
    },
    'power': {
        'options': [None, 'Power Consumption', 'mW', 'power', 'sensors.power', 'line'],
        'lines': []
    }
}

class Service(SimpleService):
    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration=configuration, name=name)
        self.order = ORDER
        self.definitions = CHARTS
        self.log_file = self.configuration['log_file']

    def check(self):
        data = self._get_data()
        for key in data:
            details = key.split('_')
            if details[0] == 'cpu':
                CHARTS['cpu']['lines'].append([key, details[1], 'absolute'])
            if details[0] == 'cpufreq':
                CHARTS['cpufreq']['lines'].append([key, details[1], 'absolute'])            
            if key == 'swap_used':
                CHARTS['swap']['lines'].append([key, details[1], 'absolute', 1, data['swap_total']])
            if key == 'iram_used':
                CHARTS['iram']['lines'].append([key, details[1], 'absolute', 1, data['iram_total']])
            if details[0] == 'temp':
                CHARTS['temperatures']['lines'].append([key, details[1], 'absolute'])
            if details[0] == 'vdd':
                CHARTS['power']['lines'].append([key, key.replace('vdd_',''), 'absolute'])

        return True

    def _get_SWAP_status(self, text):
        # SWAP X/Y (cached Z)
        # X = Amount of SWAP in use in megabytes.
        # Y = Total amount of SWAP available for applications.
        # Z = Amount of SWAP cached in megabytes.
        find_swap = re.search('SWAP (.+?)B \(cached (.+?)B\)', text)    
        if find_swap is not None:
            swap_string = find_swap.group()
            swap_stat = re.findall("\d+", swap_string)
            text = re.sub('SWAP (.+?)B \(cached (.+?)B\) ', '', text)
            return {'swap_used': float(swap_stat[0]), 
                    'swap_total': float(swap_stat[1]),
                    'swap_cached': int(swap_stat[2])
                }, text
        else:
            return {}, text

    def _get_IRAM_status(self, text):
        # IRAM X/Y (lfb Z)
        # IRAM is memory local to the video hardware engine.
        # X = Amount of IRAM memory in use, in kilobytes.
        # Y = Total amount of IRAM memory available.
        # Z = Size of the largest free block.
        find_iram = re.search('IRAM (.+?)B\(lfb (.+?)B\)', text)
        # Find if IRAM is inside
        if find_iram is not None:
            iram_lfb_string = find_iram.group()
            iram_stat = re.findall("\d+", iram_lfb_string)
            text = re.sub('IRAM (.+?)B\(lfb (.+?)B\) ', '', text)
            return {'iram_used': float(iram_stat[0]), 
                    'iram_total': float(iram_stat[1])
                    # 'iram_size': int(iram_stat[2])
                }, text
        else:
            return {}, text
    
    def _get_RAM_status(self, text):
        # RAM X/Y (lfb NxZ)
        # Largest Free Block (lfb) is a statistic about the memory allocator. 
        # It refers to the largest contiguous block of physical memory 
        # that can currently be allocated: at most 4 MB.
        # It can become smaller with memory fragmentation.
        # The physical allocations in virtual memory can be bigger.
        # X = Amount of RAM in use in MB.
        # Y = Total amount of RAM available for applications.
        # N = The number of free blocks of this size.
        # Z = is the size of the largest free block. 
        ram_string = re.search('RAM (.+?)B', text).group()
        lfb_string = re.search('\(lfb (.+?)\)', text).group()
        ram_stat = re.findall("\d+", ram_string)
        lfb_stat = re.findall("\d+", lfb_string)
        text = re.sub('RAM (.+?)\) ', '', text)
        return {
            'ram_used': int((float(ram_stat[0])/float(ram_stat[1])) * 100)
            # 'lfb_count': float(lfb_stat[0])
            # 'lfb_size': lfb_stat[1]
        }, text

    def _get_value_processor(self, name, val):
        if 'off' in val:
            return {'name': name, 'idle': 0.0, 'frequency': 0.0}
        elif '@' in val:
            info = re.findall("\d+", val)
            return {'name': name, 'idle': float(info[0]), 'frequency': float(info[1])}
        else:
            info = re.findall("\d+", val)
            return {'name': name, 'idle': info[0]}
        return val

    def _get_CPU_status(self, text):
        # CPU [X%,Y%, , ]@Z
        # or
        # CPU [X%@Z, Y%@Z,...]
        # X and Y are rough approximations based on time spent
        # in the system idle process as reported by the Linux kernel in /proc/stat.
        # X = Load statistics for each of the CPU cores relative to the 
        #     current running frequency Z, or 'off' in case a core is currently powered down.
        # Y = Load statistics for each of the CPU cores relative to the 
        #     current running frequency Z, or 'off' in case a core is currently powered down.
        # Z = CPU frequency in megahertz. Goes up or down dynamically depending on the CPU workload.
        cpu_string = re.search('CPU (.+?)\]', text).group()
        cpu_string = cpu_string[cpu_string.find("[")+1:cpu_string.find("]")]
        text = re.sub('CPU (.+?)\] ', '', text)
        output = {}
        for idx, cpu in enumerate(cpu_string.split(",")):
            val = self._get_value_processor("cpu" + str(idx+1), cpu)
            output['cpu_' + val['name']] = val['idle']
            output['cpufreq_' + val['name']] = val['frequency']
    
        return output, text
    

    def _get_status(self, text):
        jetsonstats = {}
        
        # should never happen...
        if not text: return jetsonstats

        # Read SWAP status
        swap_status, text = self._get_SWAP_status(text)
        jetsonstats.update(swap_status)
        # Read IRAM status
        iram_status, text = self._get_IRAM_status(text)
        jetsonstats.update(iram_status)
        # Read RAM status
        ram_status, text = self._get_RAM_status(text)
        jetsonstats.update(ram_status)
        # Read CPU status
        cpu_status, text = self._get_CPU_status(text)
        jetsonstats.update(cpu_status)
                
        idx = 0
        other_values = text.split(" ")
        while idx < len(other_values):
            data = other_values[idx]
            if 'EMC' in data:
                # EMC X%@Y
                # EMC is the external memory controller, 
                # through which all sysmem/carve-out/GART memory accesses go.
                # X = Percent of EMC memory bandwidth being used, relative to the current running frequency.
                # Y = EMC frequency in megahertz.
                val = self._get_value_processor("EMC", other_values[idx+1])
                jetsonstats['emc'] = val['idle']
                # jetsonstats['emcfreq'] = val['frequency']
                # extra increase counter
                idx += 1
            elif 'APE' in data:
                # APE Y
                # APE is the audio processing engine. 
                # The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
                # Y = APE frequency in megahertz.
                # jetsonstats['ape'] = other_values[idx+1]
                # extra increase counter
                idx += 1
            elif 'GR3D' in data:
                # GR3D X%@Y
                # GR3D is the GPU engine.
                # X = Percent of the GR3D that is being used, relative to the current running frequency.
                # Y = GR3D frequency in megahertz
                val = self._get_value_processor("GPU", other_values[idx+1])
                jetsonstats['gpu'] = val['idle']
                # jetsonstats['gpufreq'] = val['frequency']
                # extra increase counter
                idx += 1
            elif 'MTS' in data:
                # MTS fg X% bg Y%
                # X = Time spent in foreground tasks.
                # Y = Time spent in background tasks.
                fg = float(other_values[idx+2].split("%")[0])
                bg = float(other_values[idx+4].split("%")[0])
                jetsonstats['mts_fg'] = fg
                jetsonstats['mts_bg'] = bg
                # extra increase counter
                idx += 4
            elif '@' in data:
                # [temp name] C
                # [temp name] is one of the names under the nodes
                # /sys/devices/virtual/thermal/thermal_zoneX/type.
                info = data.split("@")
                name = info[0]
                value = info[1]
                jetsonstats['temp_' + name] = float(value.split("C")[0])
            else:
                # [VDD_name] X/Y
                # X = Current power consumption in milliwatts.
                # Y = Average power consumption in milliwatts.
                name = data.split('_')[1]
                value = other_values[idx+1].split("/")
                jetsonstats['vdd_{}_{}'.format(name, 'curr')] = int(value[0])
                jetsonstats['vdd_{}_{}'.format(name, 'avg')] = int(value[1])
                # extra increase counter
                idx += 1
            # Update counter
            idx +=1
        
        return jetsonstats

    def _get_data(self):
        stats = ''
        try:
            p = subprocess.Popen(['tail', '-1', self.log_file], shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            res,err = p.communicate()

            if err:
                self.error(err.decode('utf-8'))
            else:
                stats = res.decode('utf-8')
        except:
            self.error("Unable to run tail command.")

        return self._get_status(stats)