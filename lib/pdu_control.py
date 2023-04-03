import os, sys
import platform
import ipaddress

class PDU_Ctl(object):
    def __init__(self):
        # ====== pdu info =====
        self.server_pdu_path = "/Longrun_stress/pdu_control"
        self.ver_pdu_server = "pdu_server_v1.00"
        self.pduip = '172.17.0.153'
        self.__ctl_list = ['172.17.0.52', '192.168.15.10']
        self.__ctl_user = 'root'
        self.__ctl_passwd = 'fae111111'
        self.ctl_ip = self.getserver_ip()
        if not self.ctl_ip:
            print("can't connect console server")
            exit(2)

    @staticmethod
    def con_remote(ip, username, password, port=22):
        import paramiko
        # print(ip, username, password)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port, username, password)
        return ssh
        # stdin, stdout, stderr = ssh.exec_command('cat file_not_found')
        # print(stdout.readlines())

    def accycle(self, inlet, delay=15):
        ssh = self.con_remote(self.ctl_ip, self.__ctl_user, self.__ctl_passwd)
        for i in self.chk_inlet(inlet):
            cmd = "cd {pdu_path};./{ver_pdu_server} {pdu_ip} {index} {pdu_delay} ".\
                format(pdu_path=self.server_pdu_path, ver_pdu_server=self.ver_pdu_server, pdu_ip=self.pduip, index=i,
                       pdu_delay=delay)
            print(cmd)
            ssh.exec_command(cmd)

    @staticmethod
    def chk_inlet(inlet):
        if isinstance(inlet, int):
            yield inlet
        if isinstance(inlet, list):
            for i in inlet:
                for x in PDU_Ctl.chk_inlet(i):
                    yield x
        if isinstance(inlet, str):
            raise TypeError('inlet need a int number or a int list')

    def getserver_ip(self):
        server_ip = ''
        for ctl_ip in self.__ctl_list:
            self.platform = sys.platform
            cmd = ''
            if self.platform == "linux":
                cmd = 'ping -c 1 %s > /dev/null' % ctl_ip
            elif self.platform == "win32":
                cmd = 'ping -n 1 %s' % ctl_ip
            if not os.system(cmd):
                server_ip = ctl_ip
        return server_ip

    @staticmethod
    def chkip(ip):
        pass


if __name__ == '__main__':
    pctl = PDU_Ctl()
    pctl.accycle(inlet = [2, 4])