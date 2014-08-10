"""
Reads data from FPT (memo) files.

FPT files are used to varying lenght text or binary data which is too
large to fit in a DBF field.

VFP == Visual FoxPro
DB3 == dBase III
DB4 == dBase IV
"""
from collections import namedtuple
from .ifiles import ifind
from .struct_parser import StructParser



VFPFileHeader = StructParser(
    'FPTHeader',
    '>LHH504s',
    ['nextblock',
     'reserved1',
     'blocksize',
     'reserved2'])

VFPMemoHeader = StructParser(
    'FoxProMemoHeader',
    '>LL',
    ['type',
     'length'])

# Record type
VFP_RECORD_TYPES = {
    0x0: 'picture',
    0x1: 'memo',
    0x2: 'object',
}

DB4MemoHeader = StructParser(
    'DBase4MemoHeader',
    '<LL',
    ['reserved',  # Always 0xff 0xff 0x08 0x08.
     'length'])

# Used for Visual FoxPro memos to distinguish binary from text memos.
class BinaryMemo(bytes):
    pass

class MemoFile(object):
    def __init__(self, filename):
        self.filename = filename
        self._open()
        self._init()

    def _init(self):
        pass

    def _open(self):
        self.file = open(self.filename, 'rb')
        # Shortcuts for speed.
        self._read = self.file.read
        self._seek = self.file.seek

    def _close(self):
        self.file.close()

    def __getitem__(self, index):
        raise NotImplemented

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._close()
        return False


class FakeMemoFile(MemoFile):
    def __getitem__(self, i):
        return None

    def _open(self):
        pass

    _init = _close = _open


class VFPMemoFile(MemoFile):
    def _init(self):
        self.header = VFPFileHeader.read(self.file)

    def __getitem__(self, index):
        """Get a memo from the file."""
        if index <= 0:
            raise IndexError('memo file got index {}'.format(index))

        self._seek(index * self.header.blocksize)
        memo_header = VFPMemoHeader.read(self.file)

        data = self._read(memo_header.length)
        if len(data) != memo_header.length:
            raise IOError('EOF reached while reading memo')
        
        if memo_header.type == 0x1:
            return data
        else:
            return BinaryMemo(data)


class DB3MemoFile(MemoFile):
    """dBase III memo file."""
    # Code from dbf.py
    def __getitem__(self, index):
        block_size = 512
        self._seek(index * block_size)
        eom = -1
        data = ''
        while eom == -1:
            newdata = self._read(block_size)
            if not newdata:
                return data
            data += newdata

            # Todo: some files (help.dbt) has only one field separator.
            # Is this enough for all file though?
            eom = data.find('\x1a')
            # eom = data.find('\x1a\x1a')

            eom = data.find('\x0d\x0a')
        return data[:eom]        

class DB4MemoFile(MemoFile):
    """dBase IV memo file"""
    def __getitem__(self, index):
        # Todo: read this from the file header.
        block_size = 512

        self._seek(index * block_size)
        memo_header = DB4MemoHeader.read(self.file)
        data = self._read(memo_header.length)
        # Todo: fields are terminated in different ways.
        # \x1a is one of them
        # return data.split('\x1a', 1)[0]
        return data


def find_memofile(dbf_filename):
    for ext in ['.fpt', '.dbt']:
        name = ifind(dbf_filename, ext=ext)
        if name:
            return name
    else:
        return None


def open_memofile(filename, dbversion):
    if filename.lower().endswith('.fpt'):
        return VFPMemoFile(filename)
    else:
        if dbversion == 0x83:
            return DB3MemoFile(filename)
        else:
            return DB4MemoFile(filename)
