import yaml

def getconfig(file):
    with open(file, 'r') as f:
        return yaml.load(f)

if __name__ == '__main__':
    file =  'E:\\python_pycharm\\CPLD_Flash\\config.yaml'
    print(getconfig(file))