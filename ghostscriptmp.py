# /usr/bin/python

import os
import time
import shutil
import subprocess
from multiprocessing import Process, Queue, Lock
from collections import namedtuple

class GSDecomposeException(Exception):
    """ Decompose Exception by Ghostscript"""
    pass


_GSResult = namedtuple(
    'GSResult', 'error destfile message emessage start_time end_time')


class DecompResult(_GSResult):
    """
    Result of decomposition process.
    """

    def proc_time(self):
        """
        Returns the processing time.
        :return: processing time in seconds, or -1 if error.
        """
        if self.error is None:
            return self.end_time - self.start_time
        else:
            return -1

    def is_success(self):
        """
        Returns whether the process was successful.
        :return: True if success, False otherwise.
        """
        return (self.error is None)


class GhostscriptWrapMP():
    """
    A wrapper class for Ghostscript to perform parallel file conversion.
    Uses multiprocessing to run Ghostscript commands in the background.
    """

    def __init__(self, resolution=200, device="tiffg4", gs_path=None):
        """
        Initialize the Ghostscript wrapper.

        :param resolution: Resolution in DPI (default 200).
        :param device: Ghostscript device to use (default "tiffg4").
        :param gs_path: Path to the Ghostscript executable (optional).
        """
        self.processing = None
        self._dec_queue = Queue()
        self._dec_loc = Lock()
        self._dec_result = None
        self.resolution = int(resolution)
        self.device = device
        self.__find_ghostscript(gs_path)

    def __find_ghostscript(self, gs_path=None):
        """
        Find the Ghostscript executable.
        If gs_path is provided, checks if it works.
        Otherwise, searches for 'gs' or 'gswin*c.exe'.

        :param gs_path: Explicit path to GS executable.
        """
        self.gs = None
        suspects = []
        if gs_path:
            suspects.append(gs_path)

        suspects.extend([
            # linux
            "gs",
            # Windows
            "gswin32c.exe",
            "gswin64c.exe"
        ])

        for gs in suspects:
            # Check if command exists first using shutil.which (cleaner than subprocess call)
            if shutil.which(gs) or os.path.isfile(gs):
                try:
                    # Verify it works by checking version
                    exit_code = subprocess.call(
                        [gs, "-v"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    if exit_code == 0:
                        self.gs = gs
                        break
                except Exception:
                    continue

        if self.gs is None:
             # Just log for now or let it fail later?
             # It's better to raise exception or handle it, but for compatibility
             # with existing pattern of setting None, we might leave it.
             # However, decompose will fail.
             pass

    def __get_decomp_prameter(self, srcfiles, destpath):
        """
        Construct the Ghostscript command arguments.

        :param srcfiles: List of source file paths.
        :param destpath: Destination file path.
        :return: List of command line arguments.
        """
        if not self.gs:
            raise GSDecomposeException("Ghostscript executable not found.")

        decomp_cmd = [
            self.gs,
            # quiet mode
            '-q',
            # batch mode: exit after processing files
            '-dBATCH',
            # no pause after each page
            '-dNOPAUSE',
            # resolution
            "-r%d" % self.resolution,
            # device (tiffg4, tifflzw, etc)
            "-sDEVICE=%s" % self.device,
            # export
            "-sOutputFile=%s" % destpath,
        ]

        # Files should be added before -c -quit if we used -c -quit.
        # But -dBATCH implies quit after processing files.
        # The original code had '-c', '-quit' at the end AND files after that.
        # This was likely incorrect or redundant.
        # We will append files now.
        decomp_cmd.extend(srcfiles)

        # Explicit quit using -c is usually not needed with -dBATCH,
        # but to match previous intent (and maybe ensure it quits even if no files),
        # we can add it at the very end.
        decomp_cmd.extend(['-c', 'quit'])

        return decomp_cmd

    def decompose(self, srcfiles, destpath):
        """
        Start the decomposition (conversion) process in a separate process.

        :param srcfiles: List of source file paths.
        :param destpath: Destination file path.
        """
        self._dec_loc.acquire()
        try:
            self.processing = Process(target=self._decompose, args=(self._dec_queue, srcfiles, destpath))
            self.processing.start()
        finally:
            self._dec_loc.release()

    def _decompose(self, dec_queue, srcfiles, destpath):
        """
        Internal method run in the separate process to execute Ghostscript.

        :param dec_queue: Queue to put the result.
        :param srcfiles: List of source file paths.
        :param destpath: Destination file path.
        """
        msgout = ""
        st = -1
        en = -1
        try:
            gscmd = self.__get_decomp_prameter(srcfiles, destpath)
            st = time.time()
            # stderr=subprocess.STDOUT redirects stderr to stdout so we capture both in msgout
            msgout = subprocess.check_output(gscmd, stderr=subprocess.STDOUT)
            en = time.time()

            if os.path.exists(destpath):
                dec_queue.put(DecompResult(None, destpath, msgout, "", st, en))
            else:
                emsg = "%s is not created" % destpath
                dec_queue.put(DecompResult(-1, None, msgout, emsg, st, en))

        except subprocess.CalledProcessError as ce:
            # ce.output contains the output (stdout/stderr)
            output = ce.output if ce.output else b""
            dec_queue.put(DecompResult(ce.returncode, None, output, str(ce), -1, -1))
        except Exception as e:
            dec_queue.put(DecompResult(-1, None, msgout, str(e), -1, -1))

    def result(self):
        """
        Wait for the process to complete and return the result.

        :return: DecompResult object.
        """
        self._dec_loc.acquire()
        try:
            if self.processing is None:
                return self._dec_result

            self.processing.join()
            self._dec_result = self._dec_queue.get()
            self.processing = None
            return self._dec_result
        finally:
            self._dec_loc.release()

if __name__ == "__main__":
    job = "test/test.ps"
    jobs = [job]
    proc = []

    # Create dummy test file if it doesn't exist
    if not os.path.exists(job):
        if not os.path.exists("test"):
            os.makedirs("test")
        with open(job, "w") as f:
            f.write("%!PS\n(Hello World) show showpage")

    # decompose
    print("Starting jobs...")
    for test in range(1, 10):
        # We can pass local mock_gs here if we want, but for now we rely on path or default
        gs = GhostscriptWrapMP(240 + test * 30, gs_path=None)
        proc.append(gs)
        gs.decompose(jobs, "test/test%d.tiff" % test)

    # check result
    for p in proc:
        ret = p.result()
        if ret.error is None:
            print("OK")
            print("time: %f" % ret.proc_time())
            print("msg : %s" % ret.message)
        else:
            print("Error occured")
            print(" msg: %s" % ret.message)
            print("emsg: %s" % ret.emessage)
