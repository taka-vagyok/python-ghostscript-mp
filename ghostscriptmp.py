# /usr/bin/python

import os
import time
import subprocess
from multiprocessing import Process, Queue, Lock
from collections import namedtuple

class GSDecomposeException(Exception):

    """ Decompose Exception by Ghostscript"""
    pass


_GSResult = namedtuple(
    'GSResult', 'error destfile message emessage start_time end_time')


class DecompResult(_GSResult):

    def proc_time(self):
        if self.error is None:
            return self.end_time - self.start_time
        else:
            return -1

    def is_success(self):
        return (self.error is None)


class GhostscriptWrapMP():

    def __init__(self, resolution=200, device="tiffg4"):
        self.processing = None
        self._dec_queue = Queue()
        self._dec_loc = Lock()
        self._dec_result = None
        self.resolution = int(resolution)
        self.device = device
        self.__find_ghostscript()
    def __find_ghostscript(self):
        self.gs = None
        suspects = [
            # linux
            "gs",
            # Windows
            "gswin32c.exe",
            "gswin64c.exe"
        ]
        for gs in suspects:
            exit_code = subprocess.call(
                "%s -v" % gs, shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if (0 == exit_code):
                self.gs = gs
                break

    def __get_decomp_prameter(self, srcfiles, destpath):
        decomp_cmd = [
            self.gs,
            # when end process, quit program
            '-q',  # quiet
            '-dBATCH',  # batch mode
            '-dNOPAUSE',  # none stop
            # resolution
            "-r%d" % self.resolution,
            # device (tiffg4, tifflzw, etc)
            "-sDEVICE=%s" % self.device,
            # export
            "-sOutputFile=%s" % destpath,
            # when end process, quit program
            '-c',
            '-quit'
        ]
        decomp_cmd.extend(srcfiles)
        return decomp_cmd

    def decompose(self, srcfiles, destpath):
        self._dec_loc.acquire()
        self.processing = Process(target=self._decompose, args=(self._dec_queue, srcfiles, destpath))
        self.processing.start()
        self._dec_loc.release()

    def _decompose(self, dec_queue, srcfiles, destpath):
        gscmd = self.__get_decomp_prameter(srcfiles, destpath)
        msgout = ""
        try:
            st = time.time()
            msgout = subprocess.check_output(gscmd, subprocess.STDOUT)
            en = time.time()
            if os.path.exists(destpath):
                dec_queue.put(DecompResult(None, destpath, msgout, "", st, en))
            else:
                emsg = "%s is not created" % destpath
                dec_queue.put(DecompResult(-1, None, msgout, emsg, st, en))
        except subprocess.CalledProcessError as ce:
            dec_queue.put(DecompResult(ce.returncode, None, msgout, ce.message, -1, -1))
        except Exception as e:
            # "Exception occured: %s in decompose()" % e.message
            # raise GSDecomposeException(e)
            dec_queue.put(DecompResult(-1, "ERR", e.message, -1, -1))

    def result(self):
        self._dec_loc.acquire()
        if self.processing is None:
            self._dec_loc.release()
            return self.dec_result
        self.processing.join()
        self._dec_result = self._dec_queue.get()
        self.processing = None
        self._dec_loc.release()
        return self._dec_result

if __name__ == "__main__":
    job = "test/test.ps"
    jobs = [job]
    proc = []
    # decompose
    for test in range(1, 10):
        gs = GhostscriptWrapMP(240 + test * 30)
        proc.append(gs)
        gs.decompose(jobs, "test/test%d.tiff" % test)
    # check result
    for p in proc:
        ret = p.result()
        if ret.error is None:
            print "OK"
            print "time: %f" % ret.proc_time()
            print "msg : %s" % ret.message
        else:
            print "Error occured"
            print " msg: %s" % ret.message
            print "emsg: %s" % ret.emessage

