"""Build the original-layout release without settings, tests, or development files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
ROOT=Path(__file__).resolve().parents[1]
ADDON=ROOT/'MojowAssist'
TAG='v0.9.44-classic-layout'
def main():
    toc=ADDON/'MojowAssist.toc'
    names=[line.strip() for line in toc.read_text().splitlines() if line.strip() and not line.startswith('#')]
    names += ['MojowAssist.toc','Bindings.xml','README.md','QUICKSTART.md']
    names=sorted(set(names))
    for name in names:
        if Path(name).name!=name or not (ADDON/name).is_file():
            raise ValueError('Unexpected or missing package input: '+name)
    out=ROOT/'dist'; out.mkdir(exist_ok=True)
    archive=out/('MojowAssist-'+TAG+'.zip')
    with ZipFile(archive,'w',ZIP_DEFLATED) as zipfile:
        for name in names: zipfile.write(ADDON/name,'MojowAssist/'+name)
    with ZipFile(archive) as zipfile:
        assert zipfile.testzip() is None
        assert set(zipfile.namelist())=={'MojowAssist/'+name for name in names}
        for name in names: assert zipfile.read('MojowAssist/'+name)==(ADDON/name).read_bytes()
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    print(str(archive)); print('SHA256 '+digest); print(str(len(names))+' addon files verified')
if __name__=='__main__': main()
