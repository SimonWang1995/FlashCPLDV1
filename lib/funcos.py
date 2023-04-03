import platform
import re, os


class FuncOs(object):
    """ Linux os autologin ,power on auto excute script"""
    def __init__(self):
        _platform = platform.platform().split('-')
        self.__sys = _platform[0]
        if self.__sys == 'Linux':
            self.__kernel = "%s-%s-%s" % (_platform[1], _platform[2], _platform[3])
            self.__os_ver = _platform[-3] + '-' + _platform[-2]
        else:
            print("No support paltform: " + self.__sys)
            exit(1)
        self.__gui_login_file = ''
        self.__text_login_file = ''
        self.__rc_file = ''
        self.__pro_file = ''
        self.__get_keyfile()

    def __get_keyfile(self):
        """Get autologin  file"""
        if re.search('(redhat|centos)-[6-8]', self.__os_ver):
            self.__gui_login_file = '/etc/gdm/custom.conf'
        elif re.search('debian', self.__os_ver, re.I):
            self.__gui_login_file = '/etc/gdm3/daemon.conf'
        else:
            raise RuntimeError("sorry ,no support" + self.__os_ver)
        if re.search('(redhat|centos)-6', self.__os_ver):
            self.__text_login_file = "/etc/init/tty.conf"
        elif re.search('(centos|redhat)-[7-8]', self.__os_ver):
            self.__text_login_file = "/etc/systemd/system/getty.target.wants/getty@tty1.service "
        elif re.search('debian', self.__os_ver):
            self.__text_login_file = "/etc/systemd/system/getty.target.wants/getty@tty1.service "
        else:
            raise RuntimeError("sorry ,no support"  + self.__os_ver)
        self.__pro_file = '/etc/profile'
        self.__rc_file = '/etc/rc.local'

    def enable_rootlogin(self):
        enable_file = ['/etc/pam.d/gdm-password', '/etc/pam.d/gdm-password']
        for file in enable_file:
            fp = self.File(file)
            line = fp.find(2)
            if 'root' in line and line[0] != '#':
                fp.pop(2)
                fp.insert(2, '#' + line)

    def get_osver(self):
        """get os version"""
        return self.__os_ver

    def get_kernel(self):
        return self.__kernel

    def autologin(self, mode='g'):
        """ Set auto login linux
        given one parameter g or t (g=gui t=text) """
        mode = mode.lower()
        if mode == 'g' or mode == 'gui':
            if re.search('(redhat|centos)-[6-8]', self.__os_ver):
                file = self.File(self.__gui_login_file)
                if not os.popen("cat %s | grep AutomaticLoginEnable" % self.__gui_login_file).read():
                    file.insert(4, "AutomaticLoginEnable=True\nAutomaticLogin=root\n")
            elif re.search('debian', self.__os_ver, re.I):
                self.enable_rootlogin()
                file = self.File(self.__gui_login_file)
                if not os.popen("cat %s | grep AutomaticLoginEnable" % self.__gui_login_file).read():
                    file.insert(7, "AutomaticLoginEnable=True\nAutomaticLogin=root\n")
            else:
                raise RuntimeError("sorry ,no support" + self.__os_ver)
        elif mode == 't' or mode == 'text':
            __login_cmd = "--autologin root"
        # else:
            raise RuntimeError('mode no support, select mode from  g|t (g=gui|t=text)')

    def rclocal(self, cmd):
        file = self.File(self.__rc_file)
        file.extent(cmd)

    def profile(self, cmd):
        file = self.File(self.__pro_file)
        _gnome_comm = cmd
        _gnome_info = "gnome-terminal --geometry 80x40 -x sh -c '%s'" % cmd
        if re.search('(redhat|centos)-(7.[6-9]|8)', self.__os_ver):
            _gnome_info = "gnome-terminal --geometry 80x40 -- sh -c '%s'" % cmd # redhat7.6
        if not os.popen('cat %s | grep gnome-terminal' % self.__pro_file).read():
            file.extent(_gnome_info+'\n')

    class File(object):
        def __init__(self, file):
            self.__file = file
            self.__lines = []
            with open(self.__file, 'r') as fp:
                for line in fp:
                    self.__lines.append(line)
                # print(self.__lines)
                fp.close()

        def insert(self, index, text):
            """file line write content function
            given tree args file and line and content"""
            if len(self.__lines) >= index:
                self.__lines.insert(index, text)
            else:
                raise IndexError("list index out of range")
            self.close()

        def find(self, index):
            return self.__lines[index]

        def extent(self, content):
            self.__lines.append(content)
            self.close()

        def pop(self, index=None):
            if index:
                self.__lines.pop(index)
            else:
                self.__lines.pop()
            self.close()

        def remove(self, index):
            pass

        def close(self):
            content = ''.join(self.__lines)
            with open(self.__file, 'w') as fp:
                fp.write(content)
                fp.close()


if __name__ == '__main__':
    FuncOs().File('conf').insert(2,'df')