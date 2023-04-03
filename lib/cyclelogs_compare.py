import subprocess
import logging
import os
import time

class CycleLogs_Compare(object):
    def __init__(self,  mode, ipmitool='ipmitool'):
        self.sel_logs = os.path.join(os.getcwd(), 'SelLogs')
        if not os.path.exists(self.sel_logs):
            os.makedirs(self.sel_logs)
        self.sdr_logs = os.path.join(os.getcwd(), 'SdrLogs')
        if not os.path.exists(self.sdr_logs):
            os.makedirs(self.sdr_logs)
        self.fru_logs = os.path.join(os.getcwd(), 'FruLogs')
        if not os.path.exists(self.fru_logs):
            os.makedirs(self.fru_logs)
        self.error_log = os.path.join(os.getcwd(), 'error.log')
        self.cycle_log = os.path.join(os.getcwd(), 'cycle.log')
        self.mode = mode
        self.ipmitool = ipmitool
        self.bmc_cmd = {'sel': '{ipmitool} sel list'.format(ipmitool=self.ipmitool),
                        'sdr': '{ipmitool} sdr list'.format(ipmitool=self.ipmitool),
                        'fru': '{ipmitool} fru list'.format(ipmitool=self.ipmitool)}
        if self.mode == 'in':
            self.logpath = os.path.join(os.getcwd(), 'logs')
            if not os.path.exists(self.logpath):
                os.makedirs(self.logpath)
            name_array = ['pci', 'disks', 'cpu_procs', 'cpu_cores', 'cpu_speed', 'total_memory', 'memory', 'ipmi_lan',
                          'ipmi_sol', 'ipmi_bmc', 'dmidecode_type_0', 'dmidecode_type_1', 'dmidecode_type_2',
                          'dmidecode_type_3', 'ipmi_restart_cause', 'ipmi_power_restore_police', 'lspcivvv']
            # these are the tests
            lspci_nn_vvv = 'lspci -nn -vvv | grep -e "[[:alnum:]][[:alnum:]]:[[:alnum:]][[:alnum:]].[[:alnum:]] " ' \
                           '-e "LnkSta" -e "LnkCtl" -e "UESta" -e "CESta"'
            test_array = ['lspci', 'ls /dev/disk/by-id', 'grep -ci processor /proc/cpuinfo',
                          'grep -ci cores /proc/cpuinfo', 'dmidecode -t processor', 'grep MemTotal /proc/meminfo',
                          'dmidecode -t memory', 'ipmitool lan print', 'ipmitool sol info 1', 'ipmitool mc info',
                          'dmidecode -t 0', 'dmidecode -t 1', 'dmidecode -t 2', 'dmidecode -t 3',
                          'ipmitool raw 0x00 0x07', 'ipmitool raw 0x00 0x01', lspci_nn_vvv]
            self.commandsdict = dict(zip(name_array, test_array))
        self.initiateLogging(__file__)

    def initiateLogging(self, logFileName='cycle_LogsCompare.log'):
        '''
        Helper function to initiate logging.
        '''
        logging.basicConfig(filename=logFileName, level=logging.INFO,
                            format='%(asctime)s [%(levelname)s] %(module)s | %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
        self.logger = logging.getLogger()

    def initsetting(self):
        for name, cmd in self.bmc_cmd.items():
            subpro = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = subpro.communicate()
            if stderr:
                self.logger.error('Execute command: %s    FAIL' % cmd)
                self.logger.error(stderr)
                exit(2)
            if name == 'sel':
                result, comment = check_sel(stdout.decode())
                if result == 'FAIL':
                    logging.error(comment)
                    exit(2)
            self.logsave(os.path.join(eval('self.'+name+'_logs'), name + '.log1'), stdout)
            self.logger.info("Initial %s cmd output" % name)
            # self.logger.info(stdout)

        if self.mode == 'in':
            for name, cmd in self.commandsdict.items():
                subpro = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = subpro.communicate()
                if stderr:
                    self.logger.error('Execute command: %s    FAIL' % cmd)
                    self.logger.error(stderr)
                    exit(2)
                self.logsave(os.path.join(self.logpath, name+'.log1'), stdout)
                self.logger.info("Initial %s cmd output" % name)
                # self.logger.info(stdout)

    def compare_logs(self):
        org = 'org'
        last = 'last'
        errflag = False
        for name, cmd in self.bmc_cmd.items():
            subpro = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = subpro.communicate()
            origelog = os.path.join(eval('self.'+name+'_logs'), name + '.log1')
            lastlog = os.path.join(eval('self.'+name+'_logs'), name + '.log' + str(self.count))
            self.logsave(lastlog, stdout)
            if name == 'sdr':
                org = getSdrDict(self.logread(origelog))
                last = getSdrDict(self.logread(lastlog))
            elif name == 'sel':
                org = getSelList(self.logread(origelog))
                last = getSelList(self.logread(lastlog))
            else:
                org = self.logread(origelog)
                last = self.logread(lastlog)
            if not self.comparelog(org, last):
                msg = """An error was detected in test {name} on reboot #{count} logged {date}
                See {name}.log.{count} for more details.""".format(name=name, count=str(self.count),
                                                                   date=time.strftime('%Y%m%dT%H%M%S'))
                self.logsave(self.error_log, msg+'\n')
                self.logger.error(msg)
                errflag = True

        if self.mode == 'in':
            for name, cmd in self.commandsdict.items():
                subpro = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = subpro.communicate()
                output = stdout
                origelog = self.logread(os.path.join(self.logpath, name+'.log1'))
                if not self.comparelog(origelog, output.decode()):
                    self.logsave(os.path.join(self.logpath, name+'.log'+str(self.count)), stdout)
                    msg = """An error was detected in test {name} on reboot #{count} logged {date}
                    See {name}.log.{count} for more details.""".format(name=name, count=str(self.count),
                                                                       date=time.strftime('%Y%m%dT%H%M%S'))
                    self.logsave(self.error_log, msg + '\n', mode='a')
                    self.logger.error(msg)
                    errflag = True
                else:
                    text = "Successful reboot #{count} logged {data}".format(count=self.count,
                                                                      data=time.strftime('%Y%m%dT%H%M%S'))
                    self.logsave('reboot.log', text + '\n', mode='a')
                    self.logger.info(text)
            return errflag

    def getcompare_result(self, count):
        self.count = count
        if self.compare_logs():
            return ("FAIL", ' See error.log for more details.')
        else:
            return ("PASS", '')

    @staticmethod
    def comparelog(string1, string2):
        if string1 == string2:
            return True
        else:
            return False

    @staticmethod
    def logsave(file, text, mode='w'):
        if isinstance(text, bytes):
            text = text.decode()
        with open(file, mode) as fp:
            fp.write(text)

    @staticmethod
    def logread(file):
        with open(file, 'r') as fp:
            data = fp.read()
        return data


def getSdrDict(input):
    '''
    This returns the 1st and 3rd columns of the sdr output as dict.
    '''
    sdrDict = {}
    # Truncate last new line
    input = input[0:len(input) - 1]
    for line in input.split('\n'):
        sdrDict[line.split('|')[0]] = line.split('|')[2]
    return sdrDict

def getSelList(input):
    '''
    This returns the 1st and 3rd columns of the sel output as list.
    '''
    sellist = []
    # Truncate last new line
    input = input[0:len(input) - 1]
    for line in input.split('\n'):
        sellist.append("|".join(line.split('|')[3:]))
    return sellist

def check_sel(log):
    local_result = 'OK'
    local_comment = []
    sel_black_list = ['single bit error', 'going low', 'single-bit ECC', 'NMI', 'Non-recoverable',
                      'Correctable ECC', 'Uncorrectable ECC', 'error', 'IERR', 'CATERR']
    for i in sel_black_list:
        if i.lower() in log.lower():
            local_result = "FAIL"
            local_comment.append(i + "FOUND IN SEL LOG")
    return (local_result, local_comment)

if __name__ == '__main__':
    pass