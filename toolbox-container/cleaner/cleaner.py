import sys
import os
import logging
from psutil._common import bytes2human
from pathlib import Path
import subprocess
import time
import re
from collections import OrderedDict

# Init Logger
log = logging.getLogger('CLEANER')
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)



# kudos https://github.com/sandyUni/P900/blob/master/parseKMG.py#L72
def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.
      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776
      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """
    # see: http://goo.gl/kTQMs
    SYMBOLS = {
        'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
        'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                           'zetta', 'iotta'),
        'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                           'zebi', 'yobi'),
    }

    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])



# kudos https://github.com/HPCHub/frontend/blob/master/project/applications/core/utils/human_seconds.py#L29
def human2seconds(string):
    """Convert internal string like 1M, 1Y3M, 3W to seconds.
    :type string: str
    :param string: Interval string like 1M, 1W, 1M3W4h2s...
        (s => seconds, m => minutes, h => hours, D => days, W => weeks, M => months, Y => Years).
    :rtype: int
    :return: The conversion in seconds of string.
    """
    interval_dict = OrderedDict([("h", 3600),       # 1 hour
                             ("m", 60),         # 1 minute
                             ("s", 1)])         # 1 second

    interval_exc = "Bad interval format for {0}".format(string)

    interval_regex = re.compile("^(?P<value>[0-9]+)(?P<unit>[{0}])".format("".join(interval_dict.keys())))
    seconds = 0

    while string:
        match = interval_regex.match(string)
        if match:
            value, unit = int(match.group("value")), match.group("unit")
            if int(value) and unit in interval_dict:
                seconds += value * interval_dict[unit]
                string = string[match.end():]
            else:
                raise Exception(interval_exc)
        else:
            raise Exception(interval_exc)
    return seconds



def print_config(humanlimit,threshold,thresholdlimit,humanrunevery,config,registrydir):
  log.info("Registry config : " + config)
  log.info("Registry data dir: " + registrydir)
  log.info("LIMIT           : %s (%s)" % (human2bytes(humanlimit), humanlimit))
  log.info("LIMIT THRESHOLD : %s percent" % threshold)
  log.info("LIMIT TH SIZE   : %s (%s)" % (thresholdlimit, bytes2human(thresholdlimit)))
  log.info("RUNNING EVERY   : %s seconds (%s)" % (human2seconds(humanrunevery), humanrunevery))



def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size



def run_garbage_collect(configpath):
    p = subprocess.Popen("registry garbage-collect " + configpath + " ", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    #log.debug(output.decode())
    return output.decode()



def find_oldest_file(path):
    p = subprocess.Popen("find " + path +" -name data -exec stat -c '%x %n' {} \;  | sort -n | head -n 1 | awk '{sub(/data$/,\"\");print $4}' | tr -d '\n'", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
    return output.decode()



def rmdir(directory):
    directory = Path(directory)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()



def main(config='/cleaner/config-base.yaml'):



    def printconfig():
        print_config(humanlimit, threshold, thresholdlimit, humanrunevery, config, registrydir)

    humanlimit = os.environ.get('CLEANER_MAXSIZE', '10G')
    threshold = int(os.environ.get('CLEANER_THRESHOLD_PERCENTAGE', '20'))
    humanrunevery = os.environ.get('CLEANER_RUNEVERY_TIME', '30m')
    btwdeletestime = os.environ.get('CLEANER_BTWDELETES_TIME', '2')

    limit = int(human2bytes(humanlimit))
    thresholdlimit = limit * ( 1 + (threshold/100))
    runeveryseconds = int(human2seconds(humanrunevery))
    registrydir = os.environ.get('REGISTRYDIR','/var/lib/registry')
    dockerdir = registrydir + '/docker'

    printconfig()

    while(True):
        size=get_size(dockerdir)
        sizehuman=bytes2human(size)
        log.info("CURRENT SIZE: %s (%s)" % (size, sizehuman))
        if size > thresholdlimit:
            log.info("** CLEANING START **")
            while size > limit:
                log.info("Cleaning (%s > %s)" % (sizehuman, humanlimit))

                bloboldestfile=find_oldest_file(dockerdir + '/registry/v2/blobs/sha256')
                log.info("Removing blob: " + bloboldestfile)
                rmdir(bloboldestfile)

                log.info("Executing Registry Garbage Collector....")
                run_garbage_collect(config)

                time.sleep(btwdeletestime)

                size=get_size(dockerdir)
                sizehuman=bytes2human(size)

            log.info("** CLEANING FINISH **")
            log.info("AFTER CLEANING SIZE: %s (%s)" % (size, sizehuman))
            printconfig()
        time.sleep(runeveryseconds)

    return True


if __name__ == '__main__':

    if len(sys.argv) == 2:
        sys.exit(main(config=sys.argv[1]))
    else:
        sys.exit(main())
