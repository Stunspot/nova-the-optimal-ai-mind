"""Current product-owned cargo. Historical releases and local research never enter implicitly."""
from pathlib import Path
from custody import tree_files,reject_links,namespace
TOP=('README.md','START-HERE.md','CONTRIBUTING.md','LICENSE.md','RELEASE-NOTES.md','SECURITY.md','SUPPORT.md','SKILL.md','VERSION','Open.cmd','Open.command')
DIRECTORIES=('agents','assets','docs','fallbacks','knowledge','personas','references','schemas','scripts','workspace','examples')

def inventory(root):
    root=reject_links(root);files=[]
    for name in TOP:
        p=reject_links(root/name)
        if not p.is_file():raise ValueError('missing product file '+name)
        files.append(p)
    for name in DIRECTORIES:files.extend(tree_files(root/name))
    review=reject_links(root/'verification/documentation-review.md')
    if not review.is_file():raise ValueError('missing current documentation boundary')
    files.append(review)
    for p in files:
        if '__pycache__' in p.parts or p.suffix in {'.pyc','.tmp'}:raise ValueError('transient file in product cargo: '+str(p))
    namespace([(p.relative_to(root).as_posix(),False) for p in files])
    return sorted(files,key=lambda p:p.relative_to(root).as_posix())
