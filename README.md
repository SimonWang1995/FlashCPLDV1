# FlashCPLDV1
---
## Description
Cycle Flash CPLD Tool
---
## Usages
    cd tools/packages
    tar zxvf PyYAML-5.3.1.tar.gz ; cd PyYAML-5.3.1
    python3 setup.py install
inband:
    python3 flashcpld.py -l <loops> -d <device> [--ignore]
    device: MLB 2BP 12BP
    --ignore: ignore error, don't exit terminal
outband:
    python3 flashcpld.py -H <bmcip> -U <username> -P <password> -l <loops> -d <device> [--ignore]
    device: MLB 2BP 12BP
    --ignore: ignore error, don't exit terminal
