from .. import constants
from . import UnhandledNoteError
import struct

class Operation(object):
    NAMES = {}
    for name in dir(constants):
        if name.startswith("DW_OP_"):
            assert not NAMES.has_key(name)
            NAMES[getattr(constants, name)] = name
    del name

    OPERANDS = {
        constants.DW_OP_addr: ["address"],
        constants.DW_OP_const1u: ["u1"],
        constants.DW_OP_const1s: ["s1"],
        constants.DW_OP_const2u: ["u2"],
        constants.DW_OP_const2s: ["s2"],
        constants.DW_OP_const4u: ["u4"],
        constants.DW_OP_const4s: ["s4"],
        constants.DW_OP_const8u: ["u8"],
        constants.DW_OP_const8s: ["s8"],
        constants.DW_OP_constu: ["uleb128"],
        constants.DW_OP_consts: ["sleb128"],
        constants.DW_OP_pick: ["u1"],
        constants.DW_OP_plus_uconst: ["uleb128"],
        constants.DW_OP_bra: ["s2"],
        constants.DW_OP_skip: ["s2"],
        constants.DW_OP_breg0: ["sleb128"],
        constants.DW_OP_breg1: ["sleb128"],
        constants.DW_OP_breg2: ["sleb128"],
        constants.DW_OP_breg3: ["sleb128"],
        constants.DW_OP_breg4: ["sleb128"],
        constants.DW_OP_breg5: ["sleb128"],
        constants.DW_OP_breg6: ["sleb128"],
        constants.DW_OP_breg7: ["sleb128"],
        constants.DW_OP_breg8: ["sleb128"],
        constants.DW_OP_breg9: ["sleb128"],
        constants.DW_OP_breg10: ["sleb128"],
        constants.DW_OP_breg11: ["sleb128"],
        constants.DW_OP_breg12: ["sleb128"],
        constants.DW_OP_breg13: ["sleb128"],
        constants.DW_OP_breg14: ["sleb128"],
        constants.DW_OP_breg15: ["sleb128"],
        constants.DW_OP_breg16: ["sleb128"],
        constants.DW_OP_breg17: ["sleb128"],
        constants.DW_OP_breg18: ["sleb128"],
        constants.DW_OP_breg19: ["sleb128"],
        constants.DW_OP_breg20: ["sleb128"],
        constants.DW_OP_breg21: ["sleb128"],
        constants.DW_OP_breg22: ["sleb128"],
        constants.DW_OP_breg23: ["sleb128"],
        constants.DW_OP_breg24: ["sleb128"],
        constants.DW_OP_breg25: ["sleb128"],
        constants.DW_OP_breg26: ["sleb128"],
        constants.DW_OP_breg27: ["sleb128"],
        constants.DW_OP_breg28: ["sleb128"],
        constants.DW_OP_breg29: ["sleb128"],
        constants.DW_OP_breg30: ["sleb128"],
        constants.DW_OP_breg31: ["sleb128"],
        constants.DW_OP_regx: ["uleb128"],
        constants.DW_OP_fbreg: ["sleb128"],
        constants.DW_OP_bregx: ["uleb128", "sleb128"],
        constants.DW_OP_piece: ["uleb128"],
        constants.DW_OP_deref_size: ["u1"],
        constants.DW_OP_xderef_size: ["u1"],
    }

    FIXEDSIZE = {}
    for code in "bBhHiIqQ":
        size = struct.calcsize(code)
        type = "%s%d" % (code.isupper() and "u" or "s", size)
        assert not FIXEDSIZE.has_key(type)
        FIXEDSIZE[type] = size, code
    del code, size, type

    def __init__(self, location, code, byteorder):
        self.location = location
        pc = location[1]
        self.code = ord(code[pc])
        if not self.NAMES.has_key(self.code):
            raise UnhandledNoteError(self)
        pc += 1
        self.operands = []
        for type in self.OPERANDS.get(self.code, ()):
            sizecode = self.FIXEDSIZE.get(type, None)
            if sizecode is not None:
                size, fmt = sizecode
                fmt = byteorder + fmt
                value = struct.unpack(fmt, code[pc:pc + size])[0]
            else:
                size, value = getattr(self, "decode_" + type)(code, pc)
            self.operands.append(value)
            pc += size
        self.size = pc - location[1]

    @staticmethod
    def decode_address(code, start): # pragma: no cover
        # This function is excluded from coverage because it
        # should never be implemented.  See XXX UNWRITTEN.
        raise NotImplementedError

    @classmethod
    def decode_uleb128(cls, code, start):
        return cls.__decode_leb128(code, start, False)

    @classmethod
    def decode_sleb128(cls, code, start):
        return cls.__decode_leb128(code, start, True)

    @staticmethod
    def __decode_leb128(code, start, is_signed):
        result = shift = 0
        offset = start
        while True:
            byte = ord(code[offset])
            offset += 1
            result |= ((byte & 0x7f) << shift)
            if (byte & 0x80) == 0:
                break
            shift += 7
        if is_signed and (byte & 0x40):
            sign = 0x40 << shift
            result &= ~(0x40 << shift)
            result -= sign
        return offset - start, result

    @property
    def name(self):
        result = self.NAMES[self.code]
        assert result.startswith("DW_OP_")
        return result[6:]

    @property
    def operand(self):
        assert len(self.operands) == 1
        return self.operands[0]
