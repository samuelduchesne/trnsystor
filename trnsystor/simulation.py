"""trnsystor simulation module."""
import contextlib
import logging
import subprocess
import sys
import threading

from path import Path

logger = logging.getLogger(__name__)


class Simulation:
    """Simulate deck file class."""

    @classmethod
    def get_simulation_dir_path(cls, base_dir_path, simulation_name=None):
        """Return the simulation dir path from base dir and name."""
        return (
            Path(base_dir_path)
            if simulation_name is None
            else Path(base_dir_path) + simulation_name
        )

    def __init__(self, deck, output_dir, simulation_name=None):
        self._dir_abspath = self.get_simulation_dir_path(
            output_dir, simulation_name
        ).abspath()
        self.deck = deck

        assert (
            self._dir_abspath.exists()
        ), f"Simulation directory not found: {self._dir_abspath}"

    def run(self):
        """Run deck file."""
        eplus_cmd = r"C:\TRNSYS18\Exe\TrnEXE64.exe"
        dck_file_cmd = self.deck.save("test_equation.dck")
        cmd_l = [eplus_cmd, dck_file_cmd]

        run_subprocess(
            cmd_l,
            cwd=self._dir_abspath,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )


def run_subprocess(
    command, cwd=None, stdout=None, stderr=None, shell=False, beat_freq=None
):
    """Run a subprocess and manage its stdout/stderr streams.

    Args:
        command (list): subprocess command to run.
        cwd (path): current working directory
        stdout (typing.StringIO): output info stream (must have 'write' method)
        stderr (typing.StringIO): output error stream (must have 'write' method)
        shell (bool): see subprocess.Popen
        beat_freq: if not none, stdout will be used at least every beat_freq (in seconds)
    """
    # prepare variables
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    # run subprocess
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        shell=shell,
        universal_newlines=True,
    ) as sub_p:
        # link output streams
        with redirect_stream(sub_p.stdout, stdout), redirect_stream(
            sub_p.stderr, stderr
        ):
            while True:
                try:
                    sub_p.wait(timeout=beat_freq)
                    break
                except subprocess.TimeoutExpired:
                    stdout.write("subprocess is still running\n")
                    if hasattr(sys.stdout, "flush"):
                        sys.stdout.flush()
        return sub_p.returncode


@contextlib.contextmanager
def redirect_stream(src, dst, freq=0.1):
    """Redirect source stream to destination stream using freq.

    Args:
        src (typing.StringIO): The source stream
        dst (typing.StringIO): The destination stream
        freq (float): The tick frequency.
    """
    stop_event = threading.Event()
    t = threading.Thread(target=_redirect_stream, args=(src, dst, stop_event, freq))
    t.daemon = True
    t.start()
    try:
        yield
    finally:
        stop_event.set()
        t.join()


def _redirect_stream(src, dst, stop_event, freq):
    while not stop_event.is_set():  # read all filled lines
        try:
            content = src.readline()
        except UnicodeDecodeError as e:
            logger.error(str(e))
            content = "unicode decode error"
        if content == "":  # empty: break
            break
        dst.write(content)
        if hasattr(dst, "flush"):
            dst.flush()
