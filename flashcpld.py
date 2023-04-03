#!/usr/bin/python3

import argparse
import os
import re
import time
from textwrap import dedent
import ipaddress
import sys
sys.path.append('./lib')
import yamlparser
from funcos import FuncOs
from cyclelogs_compare import CycleLogs_Compare
import backupfun as fg
import testlog as logger

class CPLD_Flash(object):
    def __init__(self):
        self.counter = os.path.join(pwd, 'tmp/count')
        self.image_cache = os.path.join(pwd, 'tmp/image_cache.json')
        self.flash_log = os.path.join(pwd, 'reports/flash.log')
        self.summary_log = os.path.join(pwd, 'reports/summary.log')
        self.fault_log = os.path.join(pwd, 'reports/fault.log')
        self.logpath = os.path.join(pwd, 'reports')
        self.product = config['product']
        self.line = "=" * 80
        self.loops = loops
        self.power_mode = power_mode
        self.ignore = ignore

    def pre_system(self):
        """For power cycle
        set auto login, auto excute script, save count and image_cache"""
        FuncOs().autologin()
        if ignore:
            FuncOs().profile(
                'cd {0};python3 {1} -p {2} -l {3} -d {4} --ignore --bootload;exec bash'
                    .format(pwd, __file__, power_mode, loops, ' '.join(device_list)))
        else:
            FuncOs().profile(
                'cd {0};python3 {1} -p {2} -l {3} -d {4} --ignore --bootload;exec bash'.format(
                    pwd, __file__, power_mode, loops, ' '.join(device_list)))
        self.count = 1
        self.fopen(self.counter, str(self.count), mode='w')
        """ clear log"""
        os.system("{ipmitool} sel clear".format(ipmitool=ipmitool))
        os.system("echo > /var/log/messages")

    def get_ver(self, dev):
        cmd = "{flashtool} -p {product} -t cpld -i {index} -v ".format(flashtool=os.path.join(toolpath, flashtool),
                                                                      product=self.product,
                                                                      index=config[dev][0]['index'])
        logger.debug("Running cmd: " + cmd)
        status, output = fg.runcmd(cmd)
        if status:
            logger.debug(output)
            return fg.parser_ver(output.decode())
        else:
            logger.error(output)
            raise RuntimeError("Get cpld version fail")

    def select(self):
        self.current_version = self.get_ver(self.flash_type)
        index = 1
        for i, cfg in enumerate(config[self.flash_type]):
            if self.current_version == cfg['version']:
                index = i
        if index == 0:
            self.index = config[self.flash_type][1]['index']
            self.image = config[self.flash_type][1]['image']
            self.flash_version = config[self.flash_type][1]['version']
            self.op = 'upgrade'
        else:
            self.index = config[self.flash_type][1]['index']
            self.image = config[self.flash_type][0]['image']
            self.flash_version = config[self.flash_type][0]['version']
            self.op = 'download'

    def display_info(self):
        text = dedent("""
         ====================== Flash Info ==================
         Flash Device: {0}
         Flash Operation: {1}
         Current Firmware: {2}
         Upgrate Firmware: {3}
         Upgrade Image: {4}
         """.format(self.flash_type, self.op, self.current_version, self.flash_version, self.image))
        logger.info(text)

    def flash(self):
        os.chdir(toolpath)
        cmd = "./{flashtool} -p {product} -t cpld -i {index} -f {image}".format(
            flashtool=flashtool, product=self.product, index=self.index, image=self.image)
        print('')
        logger.info('Starting Flash as following Info:')
        logger.info('  Flash Tool Path: ' + toolpath)
        logger.info('  Current Location: ' + os.getcwd())
        logger.info('  Execute Command:')
        logger.info('   ' + cmd)
        print('')
        if not os.path.exists(self.image):
            logger.error("Image %s No found" % self.image)
            exit(2)
        self.fopen(self.flash_log, '{0} firmware {1} \n'.format(self.flash_type, self.op), mode='a')
        last_flashlog = os.path.join(pwd, 'tmp/flash.log'+str(self.count))
        cmd = cmd + " 2>&1 | tee " + last_flashlog
        os.system(cmd)
        os.system("cat %s >> %s" % (last_flashlog, self.flash_log))
        if re.search('(fail|error)', self.fopen(last_flashlog), re.I):
            errmsg = dedent("""Cycle {0} Flash {1} firmware {2} ********** [ FAIL ]
                    See  {3} for more details
            """.format(self.cycle, self.flash_type, self.op, self.flash_log))
            self.fopen(self.fault_log, errmsg, mode='a')
            logger.error(errmsg)
            os.remove(last_flashlog)
            if not ignore:
                exit(2)
        else:
            passmsg = "Cycle {0} Flash {1} firmware {2} ************ [ PASS ]".format(self.cycle, self.flash_type, self.op)
            # self.fopen(self.fault_log, passmsg, mode='a')
            logger.info(passmsg)
            os.remove(last_flashlog)
        os.chdir(pwd)

    def inband_flash(self):
        if not bootload:
            self.pre_system()
        else:
            os.system("{ipmitool} sel clear".format(ipmitool=ipmitool))
            self.count = int(self.fopen(self.counter))
            self.verify_version()
        flash_dict = dict()
        if self.count <= self.loops*2:
            self.pri_num = (self.count + 1) // 2
            self.sce_num = (self.count + 1) % 2
            self.cycle = str(self.pri_num) + '-' + str(self.sce_num)
            logger.title("Start Cycle #{0}  Flash {1} CPLD ".format(self.cycle, " and ".join(device_list)))
            self.fopen(self.flash_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)), mode='a')
            self.fopen(self.fault_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)), mode='a')
            self.fopen(self.summary_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)), mode='a')
            for dev in device_list:
                logger.info("Begin Flash {0} ......".format(dev))
                self.flash_type = dev
                self.select()
                self.display_info()
                self.flash()
                flash_dict[self.flash_type] = self.flash_version
            self.healthcheck('in')

            self.fopen(self.counter, content=str(self.count+1), mode='w')
            fg.json_dump(self.image_cache, flash_dict)
            self.power_controller()
        else:
            self.summary()

    def healthcheck(self, mode):
        os.chdir(self.logpath)
        logscompare = CycleLogs_Compare(mode, ipmitool)
        if self.count == 1:
            logscompare.initsetting()
            # logscompare.logger.info("Logger initialized with file %s" % "CycleLogs_Compare")
        else:
            res, comment = logscompare.getcompare_result(self.count)
            if res == "PASS":
                logger.info('Cycle {0} Logs Compare *********** [ PASS ]'.format(self.cycle))
                # self.fopen(self.fault_log, 'Cycle {0} Logs Compare *********** [ PASS ]\n', mode='a')
            else:
                logger.error('Cycle {0} Logs Compare *********** [ FAIL ] '.format(self.cycle))
                logger.error(comment)
                self.fopen(self.fault_log, 'Cycle {0} Logs Compare *********** [ FAIL ] \n'.format(self.cycle), mode='a')
                self.fopen(self.fault_log, comment+'\n', mode='a')
                if not ignore:
                    exit(2)
        os.chdir(pwd)

    def outband_flash(self):
        self.count = 1
        while self.count <= self.loops*2:
            self.pri_num = (self.count + 1) // 2
            self.sce_num = (self.count + 1) % 2
            self.cycle = str(self.pri_num) + '-' + str(self.sce_num)
            logger.title("Start Cycle #{0}  Flash {1} CPLD ".format(self.cycle, " and ".join(device_list)))
            self.fopen(self.flash_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)),
                       mode='a')
            self.fopen(self.fault_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)),
                       mode='a')
            self.fopen(self.summary_log, 'Cycle #{0} Flash {1} \n'.format(self.cycle, " and ".join(device_list)),
                       mode='a')
            # clear sel log
            clearsel = "{ipmitool} sel clear".format(ipmitool=ipmitool)
            logger.info("Run command: %s" % clearsel)
            os.system(clearsel)
            for dev in device_list:
                logger.info("Begin Flash {0} ......".format(dev))
                self.flash_type = dev
                self.select()
                self.display_info()
                self.flash()
            self.power_controller()
            self.wait_os_up()
            self.compare_version()
            self.healthcheck('out')
            self.count += 1
            self.fopen(self.flash_log, self.line+'\n', mode='a')
            self.fopen(self.fault_log, self.line+'\n', mode='a')
            self.fopen(self.summary_log, self.line+'\n', mode='a')
        else:
            self.summary()

    def wait_os_up(self):
        """Wait system power up, via sel  detect power up"""
        logger.info("Wait system power up")
        time.sleep(60)
        for i in range(0, 16):
            if int(os.popen("{ipmitool} sel list | grep -c 'power up'".format(ipmitool=ipmitool)).read().strip()) == 1:
                break
            time.sleep(20)
            if i == 15:
                logger.error("System can not power up")
                exit(2)

    def power_controller(self):
        if power_mode == 'dc':
            logger.info("The system will restart after ten seconds")
            time.sleep(10)
            cmd = '{ipmitool} power cycle'.format(ipmitool=ipmitool)
            logger.info("Running cmd: %s" % cmd)
            os.system(cmd)
        if power_mode == 'ac':
            from pdu_control import PDU_Ctl
            logger.info("The system will ac cycle after ten seconds")
            time.sleep(10)
            PDU_Ctl.accycle(config['PDU_Inlet'])

    def compare_version(self):
        for dev in device_list:
            current_version = self.get_ver(dev)
            if self.flash_version != config[dev][0]['version']:
                errmsg = """Flash {0} firmware {1} Version compare ********** [ FAIL ]
                see summary.log for more details\n""".format(dev, self.op)
                self.fopen(self.fault_log, errmsg, mode='a')
                ret = 'NO. {0} Flash {1} firmware {2} FAIL.'.format(
                    self.cycle, dev, self.op
                )
                logger.error(ret)
                logger.error(' - Current: ' + current_version)
                logger.error(' - Criteria: ' + self.flash_version)
                if not ignore:
                    raise SystemExit(-1)
            else:
                # self.fopen(self.fault_log, "Cycle {0} version compare ************ [ PASS ]\n", mode='a')
                ret = 'NO. {0} Flash {1} firmware {2} PASS.'.format(
                    self.cycle, dev, self.op
                )
                logger.info(ret)
                logger.info(' - Current: ' + current_version)
                logger.info(' - Criteria: ' + self.flash_version)
                msgs = [
                    ret,
                    ' - Current: ' + current_version,
                    ' - Criteria: ' + self.flash_version,
                    ' - Datetime: {0}'.format(time.strftime('%Y-%m-%dT%H:%M:%S')),
                    '==========================================================='
                ]
                for e in msgs:
                    self.fopen(file=self.summary_log, content=e + '\n', mode='a')

    def verify_version(self):
        if os.path.exists(self.image_cache):
            cache_ver = fg.json_load(self.image_cache)
            for dev in device_list:
                current_version = self.get_ver(dev)
                if cache_ver[dev] == config[dev][0]['version']:
                    op = 'download'
                else:
                    op = 'upgrade'
                if current_version != cache_ver[dev]:
                    errmsg = """Flash {0} firmware {1} Version compare ********** [ FAIL ]
                see summary.log for more details\n""".format(dev, op)
                    self.fopen(self.fault_log, errmsg, mode='a')
                    ret = 'NO. {0} Flash {1} firmware {2} FAIL.'.format(
                        str(self.count//2) + '-' + str(self.count % 2), dev, op
                    )
                    logger.error(ret)
                    if not ignore:
                        raise SystemExit(-1)
                else:
                    ret = 'NO. {0} Flash {1} firmware {2} PASS.'.format(
                        str(self.count // 2) + '-' + str(self.count % 2), dev, op
                    )
                    logger.info(ret)
                    logger.info(' - Current: ' + current_version)
                    logger.info(' - Criteria: ' + cache_ver[dev])
                    msgs = [
                        ret,
                        ' - Current: ' + current_version,
                        ' - Criteria: ' + cache_ver[dev],
                        ' - Datetime: {0}'.format(time.strftime('%Y-%m-%dT%H:%M:%S')),
                        '==========================================================='
                    ]
                    for e in msgs:
                        self.fopen(file=self.summary_log, content=e + '\n', mode='a')
            self.fopen(self.flash_log, self.line+'\n', mode='a')
            self.fopen(self.fault_log, self.line+'\n', mode='a')
            self.fopen(self.summary_log, self.line+'\n', mode='a')

    def summary(self):
        sum_logs = self.fopen(file=self.summary_log).splitlines()
        fail_num = len([e for e in sum_logs if ' fail.' in e.lower()])
        pass_num = len([e for e in sum_logs if ' pass.' in e.lower()])
        r = '\n{0}\n - {1} {2}\n - PASS quantity: {3}\n\n'.format(
            'Test Summary:',
            'FAIL quantity:',
            fail_num,
            pass_num
        )
        self.fopen(file=self.summary_log, content=r, mode='a')

    @staticmethod
    def fopen(file, content='', mode='r'):
        if mode == 'w' or mode == 'a':
            with open(file, mode) as fp:
                fp.write(content)
        elif mode == 'r':
            with open(file, mode) as fp:
                content = fp.read()
            return content

def get_opt():
    parser = argparse.ArgumentParser(description='CPLD firmware Upgrade and downgrade')
    parser.add_argument('-p', '--power_mode', dest='mode', choices=['ac', 'dc'], default='dc',
                        help="Set power cycle mode(default:%(default)s)")
    parser.add_argument('-l', '--loops', dest='loops', type=int, default=1,
                        help='Set flash cycle times(default:%(default)s)')
    parser.add_argument('-d', '--device', dest='device', nargs='+', choices=['MLB', '2BP', '12BP'], default=['MLB'],
                        help='Set flash device(default:%(default)s)')
    parser.add_argument('--bootload', action='store_true', help=argparse.SUPPRESS)
    groupA = parser.add_argument_group('Ignore error, continue program')
    groupA.add_argument('--ignore', action='store_true', help='Ignore error')
    groupB = parser.add_argument_group('for out band flash')
    groupB.add_argument('-H', dest='ip', type=ipaddress.ip_address, help="BMC ip address")
    groupB.add_argument('-U', dest='username', help="BMC user name")
    groupB.add_argument('-P', dest='password', help='BMC user password')
    # parser.print_help()
    return parser.parse_args().__dict__


if __name__ == '__main__':
    support_list = ['seaking', 'entei']
    pwd = os.getcwd()
    # get option
    args = get_opt()
    power_mode = args['mode']
    loops = args['loops']
    device_list = args['device']
    ignore = args['ignore']
    bootload = args['bootload']
    ip = args['ip']
    username = args['username']
    password = args['password']
    config = yamlparser.getconfig(os.path.join(pwd, 'config.yaml'))
    # print(config)
    if not config['product'].lower() in support_list:
        print("No support product : %s " % config['product'])
        exit(1)
    toolpath = os.path.join(pwd, 'tools')
    flashtool = 'FlashTool64Bit'
    if not os.path.exists(os.path.join(toolpath, flashtool)):
        print("No Found  %s " % os.path.join(toolpath, flashtool))
        exit(2)

    flasher = CPLD_Flash()
    if not bootload:
        file_list = os.listdir(flasher.logpath)
        if file_list:
            ans = input("WARNING:\n had reports existed, Clear all reports [Y/n]? ")
            if ans.lower() == 'y':
                for dir in os.listdir(flasher.logpath):
                    if os.path.isdir(dir):
                        os.removedirs(dir)
                    if os.path.isfile(dir):
                        os.remove(dir)

    if not ip and not username and not password:
        ipmitool = 'ipmitool'
        flasher.inband_flash()
    else:
        if ip and username and password:
            cmd = 'ipmitool -H {ip} -U {username} -P {password} raw 6 1 2>&1 >/dev/null'.format(
                    ip=ip, username=username, password=password)
            if not os.system(cmd):
                flashtool = flashtool + ' -H {ip} -U {username} -P {password} '.format(
                    ip=ip, username=username, password=password)
                ipmitool = 'ipmitool -H {ip} -U {username} -P {password} '.format(ip=ip,
                                                                                  username=username, password=password)
                flasher.outband_flash()
            else:
                print("Error: Excute %s fail, Please check it!")
                exit(2)
        else:
            print('ip or username or password is empty')
            exit(2)