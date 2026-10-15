"""Preflight complete portable ZIP namespaces and reject linked source custody."""
from pathlib import Path
import io,os,stat,unicodedata,zipfile

def reparse(path):
    info=path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info,"st_file_attributes",0)&getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",1024))

def assert_unlinked(root):
    root=Path(os.path.abspath(root))
    for path in (root,*root.parents):
        if reparse(path):raise ValueError(f"linked/reparse source or ancestor: {path}")
    if not root.is_dir():raise ValueError(f"source is not a directory: {root}")
    def failed(error): raise error
    for folder,dirs,files in os.walk(root,followlinks=False,onerror=failed):
        for name in dirs+files:
            path=Path(folder)/name
            if reparse(path):raise ValueError(f"linked/reparse release member: {path}")
    return root

def check_members(entries,extraction_budget=70,depth=0):
    if depth>4:raise ValueError("nested ZIP depth exceeds four")
    files=set();directories=set();explicit_dirs=set()
    for name,payload in entries:
        if not isinstance(name,str) or not name or chr(92) in name:raise ValueError("archive member must be a forward-slash path")
        directory=name.endswith("/");trim=name[:-1] if directory else name;parts=trim.split("/")
        if any(not p or p in {".",".."} or any(ord(c)<32 or c in '<>:"|?*' for c in p) for p in parts):raise ValueError(f"unsafe archive member: {name}")
        if len(name.encode("utf-16-le"))//2+extraction_budget>=260:raise ValueError(f"archive member exceeds Windows extraction budget: {name}")
        key=unicodedata.normalize("NFC",trim).casefold()
        ancestors={"/".join(key.split("/")[:i]) for i in range(1,len(parts))}
        if key in files or ancestors&files or (not directory and key in directories):raise ValueError(f"archive file/directory collision: {name}")
        if directory:
            if key in explicit_dirs:raise ValueError(f"duplicate explicit archive directory: {name}")
            explicit_dirs.add(key);directories.add(key)
        else:files.add(key)
        directories.update(ancestors)
        for part in parts:
            stem=part.split(".",1)[0].upper()
            if len(part.encode("utf-8"))>255 or part.endswith((" ",".")) or stem in {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}:raise ValueError(f"nonportable archive component: {part}")
        if not directory and name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(payload)) as nested:
                children=[]
                for entry in nested.infolist():
                    if ((entry.external_attr>>16)&0o170000)==0o120000:raise ValueError("nested ZIP contains a symbolic link")
                    children.append((entry.filename,b"" if entry.is_dir() else nested.read(entry)))
                check_members(children,extraction_budget,depth+1)

def check_tree(source,paths,prefix=""):
    source=assert_unlinked(source)
    entries=[]
    for path in paths:
        lexical=Path(os.path.abspath(path))
        if not lexical.is_relative_to(source) or not lexical.resolve().is_relative_to(source.resolve()):raise ValueError(f"member outside source: {path}")
        if reparse(lexical):raise ValueError(f"linked release member: {path}")
        name="/".join(filter(None,(prefix,lexical.relative_to(source).as_posix())))
        entries.append((name,lexical.read_bytes()))
    check_members(entries)
    return entries
