import sys
import os
import logging
import subprocess
import time
import re
import shutil
import heapq
from collections import OrderedDict

# Init Logger
log = logging.getLogger('CLEANER')
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)



# kudos https://github.com/sandyUni/P900/blob/master/parseKMG.py

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs
      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'
      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'
      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'
      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

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



def env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")



def print_config(humanlimit,threshold,thresholdlimit,humanrunevery,config,registrydir,batch,include_local):
  log.debug("Registry config : " + config)
  log.info("Registry data dir: " + registrydir)
  log.info("LIMIT                : %s (%s)" % (human2bytes(humanlimit), humanlimit))
  log.info("LIMIT THRESHOLD      : %s percent" % threshold)
  log.info("LIMIT THRESHOLD SIZE : %s (%s)" % (thresholdlimit, bytes2human(thresholdlimit)))
  log.info("BATCH SIZE           : %s blobs" % batch)
  log.info("INCLUDE LOCAL        : %s" % include_local)
  log.info("RUNNING EVERY        : %s seconds (%s)" % (human2seconds(humanrunevery), humanrunevery))



def log_sizes(cache_size, local_size, thresholdlimit):
    total = cache_size + local_size
    log.info("CACHE SIZE : %s (%s)" % (cache_size, bytes2human(cache_size)))
    log.info("LOCAL SIZE : %s (%s)" % (local_size, bytes2human(local_size)))
    log.info("TOTAL SIZE : %s (%s), threshold <= %s " % (
        total, bytes2human(total), bytes2human(thresholdlimit)))
    return total



def get_size(start_path = '.'):
    total_size = 0
    if not os.path.isdir(start_path):
        return 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    continue

    return total_size



def run_garbage_collect(configpath):
    result = subprocess.run(
        ["registry", "garbage-collect", configpath],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        log.error("garbage-collect exit %s: %s" % (
            result.returncode,
            result.stderr.decode(errors="replace").strip(),
        ))
    return result.stdout.decode(errors="replace")



def iter_blob_dirs(blobs_root):
    if not os.path.isdir(blobs_root):
        return
    stack = [blobs_root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.name == "data" and entry.is_file(follow_symlinks=False):
                        try:
                            st = entry.stat(follow_symlinks=False)
                        except OSError:
                            continue
                        yield st.st_atime, os.path.dirname(entry.path)
        except OSError:
            continue



def oldest_blob_dirs(blobs_roots, batch):
    def all_blobs():
        for root in blobs_roots:
            yield from iter_blob_dirs(root)
    return [path for _, path in heapq.nsmallest(batch, all_blobs(), key=lambda item: item[0])]



def remove_blob_dir(directory):
    shutil.rmtree(directory, ignore_errors=True)



def main(config='/etc/docker/registry/config-gc.yml'):

    def printconfig():
        print_config(
            humanlimit, threshold, thresholdlimit, humanrunevery,
            config, registrydir, batch, include_local,
        )

    humanlimit = os.environ.get('CLEANER_MAXSIZE', '10G')
    threshold = int(os.environ.get('CLEANER_THRESHOLD_PERCENTAGE', '20'))
    humanrunevery = os.environ.get('CLEANER_RUNEVERY_TIME', '30m')
    btwdeletestime = int(os.environ.get('CLEANER_BTWDELETES_TIME', '2'))
    batch = int(os.environ.get('CLEANER_BATCH', '50'))
    config = os.environ.get('CLEANER_GC_CONFIG', config)
    local_gc_config = os.environ.get('CLEANER_GC_LOCAL_CONFIG', '/etc/docker/registry/config-gc-local.yml')
    include_local = env_bool('CLEANER_INCLUDE_LOCAL', False)

    limit = int(human2bytes(humanlimit))
    thresholdlimit = limit * ( 1 + (threshold/100))
    runeveryseconds = int(human2seconds(humanrunevery))
    registrydir = os.environ.get('REGISTRYDIR','/var/lib/registry')
    dockerdir = os.path.join(registrydir, 'docker')
    localdir = os.path.join(registrydir, 'local')
    blobsdir = os.path.join(dockerdir, 'registry/v2/blobs/sha256')
    localblobsdir = os.path.join(localdir, 'docker/registry/v2/blobs/sha256')
    blobs_roots = [blobsdir, localblobsdir] if include_local else [blobsdir]

    printconfig()

    while(True):
        cache_size = get_size(dockerdir)
        local_size = get_size(localdir)
        size = log_sizes(cache_size, local_size, thresholdlimit)
        sizehuman = bytes2human(size)
        if size > thresholdlimit:
            log.info("** CLEANING START **")
            while size > limit:
                log.info("Cleaning (%s > %s)" % (sizehuman, humanlimit))

                candidates = oldest_blob_dirs(blobs_roots, batch)
                if not candidates:
                    log.warning("No blobs left to remove")
                    break

                deleted_cache = False
                deleted_local = False
                for blobdir in candidates:
                    if blobdir.startswith(localdir + os.sep) or blobdir == localdir:
                        kind = "local"
                        deleted_local = True
                    else:
                        kind = "cache"
                        deleted_cache = True
                    log.info("Removing %s blob: %s" % (kind, blobdir))
                    remove_blob_dir(blobdir)

                if deleted_cache:
                    log.info("Executing Registry Garbage Collector (cache)....")
                    run_garbage_collect(config)
                if deleted_local:
                    log.info("Executing Registry Garbage Collector (local)....")
                    run_garbage_collect(local_gc_config)

                time.sleep(btwdeletestime)

                cache_size = get_size(dockerdir)
                local_size = get_size(localdir)
                size = log_sizes(cache_size, local_size, thresholdlimit)
                sizehuman = bytes2human(size)

            log.info("** CLEANING FINISH **")
            log.info("AFTER CLEANING SIZE: cache %s (%s), local %s (%s), total %s (%s)" % (
                cache_size, bytes2human(cache_size),
                local_size, bytes2human(local_size),
                size, sizehuman))
            printconfig()
        time.sleep(runeveryseconds)

    return True


if __name__ == '__main__':

    if len(sys.argv) == 2:
        sys.exit(main(config=sys.argv[1]))
    else:
        sys.exit(main())
