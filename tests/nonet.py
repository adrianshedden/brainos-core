"""No-network guard. Import and call install() at the top of a test: any attempt to open a
socket, look up a host, or run a git command that talks to a remote (push, fetch, pull, clone,
ls-remote against a URL, or against a remote name whose configured URL is one) raises from then
on, so the test fails instead of reaching the network.

Python sockets are blocked directly. A `git push` runs in a child process, which sockets-blocking
cannot see, so the guard sits on subprocess.Popen.__init__: every subprocess.run, check_call,
check_output, call and Popen goes through it, however the code under test imported subprocess.
Local remotes (a bare repo by path, or file://) still work."""
import os
import re
import shlex
import socket
import subprocess


class NetworkAttempt(AssertionError):
    pass


NETWORK_GIT = {"push", "fetch", "pull", "clone", "ls-remote"}
URL = re.compile(r"^(?:https?://|ssh://|git://|git\+ssh://|ssh\+git://|[\w.-]+@[\w.-]+:|[\w.-]+:(?![/\\]))", re.I)
# git options that take a separate value before the subcommand
_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}
# network subcommand options that take a separate value (so the value is not read as a remote)
_SUB_WITH_VALUE = {"-o", "--push-option", "--receive-pack", "--upload-pack", "--exec", "--repo", "--depth",
                   "-j", "--jobs", "-b", "--branch", "--origin", "--template",
                   "--reference", "--separate-git-dir", "--filter", "--shallow-since", "--shallow-exclude",
                   "--server-option", "--refmap", "-c", "--config", "-s", "--strategy", "-X", "--strategy-option"}

_originals = {}


def _blocked(*args, **kwargs):
    raise NetworkAttempt("an importer tried to use the network")


def _argv_list(args, shell):
    if isinstance(args, (str, bytes, os.PathLike)):
        text = os.fsdecode(args)
        try:
            return shlex.split(text) if shell else [text]
        except ValueError:
            return text.split()
    return [os.fsdecode(a) for a in args]


def _git_calls(argv):
    """Yield (workdir_args, subcommand, rest) for each git invocation found in argv, including after
    `&&`, `;`, `|` when a shell string was split into words."""
    segments, cur = [], []
    for w in argv:
        if w in ("&&", "||", ";", "|"):
            segments.append(cur)
            cur = []
        else:
            cur.append(w)
    segments.append(cur)
    for seg in segments:
        if not seg or os.path.basename(seg[0]) not in ("git", "git.exe"):
            continue
        dirs, i = [], 1
        while i < len(seg) and seg[i].startswith("-"):
            if seg[i] == "-C" and i + 1 < len(seg):
                dirs.append(seg[i + 1])
            i += 2 if seg[i] in _GLOBAL_WITH_VALUE else 1
        if i < len(seg):
            yield dirs, seg[i], seg[i + 1:]


def _positionals(rest):
    out, skip = [], False
    for w in rest:
        if skip:
            skip = False
        elif w == "--":
            continue
        elif w.startswith("-"):
            skip = w in _SUB_WITH_VALUE
            if w.startswith("--repo="):
                out.append(w.split("=", 1)[1])
        else:
            out.append(w)
    return out


def _configured_urls(real_init, cwd, dirs, names):
    """URLs (url and pushurl) of the named remotes, or of every remote when names is empty, read from
    the repo's git config with the real Popen. Reading config opens no connection."""
    where = cwd or "."
    for d in dirs:
        where = os.path.join(where, d)
    try:
        p = subprocess.Popen.__new__(subprocess.Popen)
        real_init(p, ["git", "config", "--get-regexp", r"^remote\..*\.(push)?url$"], cwd=where,
                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        text, _ = p.communicate()
    except Exception:
        return []
    urls = []
    for line in text.splitlines():
        key, _, value = line.partition(" ")
        name = key[len("remote."):].rsplit(".", 1)[0]
        if not names or name in names:
            urls.append(value)
    return urls


def _check(real_init, args, kwargs):
    shell = bool(kwargs.get("shell"))
    cwd = kwargs.get("cwd")
    cwd = os.fsdecode(cwd) if cwd is not None else None
    for dirs, sub, rest in _git_calls(_argv_list(args, shell)):
        if sub not in NETWORK_GIT:
            continue
        pos = _positionals(rest)
        for w in pos:
            if URL.match(w):
                raise NetworkAttempt(f"git {sub} against a network URL ({w}) blocked by the no-network guard")
        if sub in ("clone", "ls-remote") and pos:
            continue  # a local path (not a URL) as the repository: allowed
        names = set() if "--all" in rest else set(pos[:1])
        for u in _configured_urls(real_init, cwd, dirs, names):
            if URL.match(u):
                raise NetworkAttempt(f"git {sub} would reach a network remote ({u}); blocked by the no-network guard")


def install():
    """Safe to call again: the sockets are re-blocked each time, the subprocess guard is added once."""
    if not _originals:
        _originals["socket"] = (socket.socket, socket.create_connection, socket.getaddrinfo, socket.gethostbyname)
        real_init = subprocess.Popen.__init__
        _originals["popen_init"] = real_init
        _originals["os_system"] = os.system

        def guarded_init(self, args, *a, **kw):
            _check(real_init, args, kw)
            return real_init(self, args, *a, **kw)

        def guarded_system(command):
            _check(real_init, command, {"shell": True})
            return _originals["os_system"](command)

        subprocess.Popen.__init__ = guarded_init
        os.system = guarded_system
    socket.socket = _blocked
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked
    socket.gethostbyname = _blocked


def installed():
    return bool(_originals)


def uninstall():
    if not _originals:
        return
    socket.socket, socket.create_connection, socket.getaddrinfo, socket.gethostbyname = _originals["socket"]
    subprocess.Popen.__init__ = _originals["popen_init"]
    os.system = _originals["os_system"]
    _originals.clear()
