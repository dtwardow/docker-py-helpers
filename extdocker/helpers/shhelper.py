import os
import shutil

def absPath(pathname="."):
    return os.path.abspath(pathname)

def include(filename):
    if os.path.exists(filename):
        execfile(filename)

def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def copy(src, dst):
    shutil.copyfile(src, dst)

def replaceInFile(infile, outfile, changeset):
    with open(infile, 'r') as file:
        filedata = file.read()

    for toreplace in changeset:
        filedata = filedata.replace( toreplace, changeset[toreplace] )

    with open(outfile, 'w') as file:
        file.write(filedata)
