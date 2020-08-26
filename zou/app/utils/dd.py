import platform


def remap_path(path: str, windows: bool = False, linux: bool = False) -> str:
    # type: (str, bool, bool) -> str
    path = path.replace("\\", "/")
    remap = [
        "/space/commercials",
        "o:",
        "/space/commercials/2016",
        "p:",
        "/space/pipeline",
        "z:",
        "/space/banque",
        "y:",
        "/space/cachefx",
        "v:",
        "/vol/clr-labo",
        "i:",
        # muster_repository multiple alias
        "/space/muster_repository",
        "//data-pipeline/muster_repository",
        "/space/muster_repository",
        "//data-pipeline.ddprs.net/muster_repository",
        "/space/muster_repository",
        "//10.40.10.18/muster_repository",
        # features multiple alias
        "/space/features",
        "q:",
        "/space/features",
        "//dd-features.ddprs.net/Projects",
        "/space/features",
        "//dd-features.ddprs.net/projects",
        "/space/features",
        "//dd-features/Projects",
        "/space/features",
        "//dd-features/projects",
        "/space/features",
        "//10.40.10.11/Projects",
        "/space/features",
        "//10.40.10.11/projects",
    ]

    if (windows or platform.system() == "Windows") and not linux:
        if path.startswith("/vol/"):
            path = path.replace("/vol/", "/space/")
        if path.startswith("/Volumes/"):
            path = path.replace("/Volumes/", "/space/")
        for unix, win in zip(remap[0::2], remap[1::2]):
            path = path.replace(unix, win)
    else:
        for unix, win in zip(remap[0::2], remap[1::2]):
            path = path.replace(win, unix)
            path = path.replace(win.upper(), unix)
        # exception for FES
        path = path.replace("/space/features", "/vol/features")
        path = path.replace("/vol/commercials", "/space/commercials")
    return path