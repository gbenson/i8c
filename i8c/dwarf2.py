class DwOp(object):
    # Used by the testsuite.  These should not clash with
    # characters that appear in struct format strings.
    OP_ADDR = "\1"
    OP_ULEB = "\2"
    OP_SLEB = "\3"

    def __init__(self, opcode, name):
        self.opcode = opcode
        self.name = name

class DwOp_0(DwOp):
    """A DWARF operation with no operands."""
    operands = None

class DwOp_1_u1(DwOp):
    """A DWARF operation with one unsigned byte operand."""
    operands = "B"

class DwOp_1_s1(DwOp):
    """A DWARF operation with one signed byte operand."""
    operands = "b"

class DwOp_1_u2(DwOp):
    """A DWARF operation with one unsigned 2-byte operand."""
    operands = "H"

class DwOp_1_s2(DwOp):
    """A DWARF operation with one signed 2-byte operand."""
    operands = "h"

class DwOp_1_u4(DwOp):
    """A DWARF operation with one unsigned 4-byte operand."""
    operands = "I"

class DwOp_1_s4(DwOp):
    """A DWARF operation with one signed 4-byte operand."""
    operands = "i"

class DwOp_1_u8(DwOp):
    """A DWARF operation with one unsigned 8-byte operand."""
    operands = "Q"

class DwOp_1_s8(DwOp):
    """A DWARF operation with one signed 8-byte operand."""
    operands = "q"

class DwOp_1_addr(DwOp):
    """A DWARF operation with one address-sized operand."""
    operands = DwOp.OP_ADDR

class DwOp_1_uleb(DwOp):
    """A DWARF operation with one unsigned LEB128 operand."""
    operands = DwOp.OP_ULEB

class DwOp_1_sleb(DwOp):
    """A DWARF operation with one signed LEB128 operand."""
    operands = DwOp.OP_SLEB

class DwOp_2_uleb_sleb(DwOp):
    """A DWARF operation with two operands: an ULEB128 and a SLEB128."""
    operands = DwOp.OP_ULEB + DwOp.OP_SLEB

by_name, by_opcode = {}, {}
for opcode, name, klass in (
        (0x03, "DW_OP_addr",        DwOp_1_addr),
        (0x06, "DW_OP_deref",       DwOp_0),
        (0x08, "DW_OP_const1u",     DwOp_1_u1),
        (0x09, "DW_OP_const1s",     DwOp_1_s1),
        (0x0a, "DW_OP_const2u",     DwOp_1_u2),
        (0x0b, "DW_OP_const2s",     DwOp_1_s2),
        (0x0c, "DW_OP_const4u",     DwOp_1_u4),
        (0x0d, "DW_OP_const4s",     DwOp_1_s4),
        (0x0e, "DW_OP_const8u",     DwOp_1_u8),
        (0x0f, "DW_OP_const8s",     DwOp_1_s8),
        (0x10, "DW_OP_constu",      DwOp_1_uleb),
        (0x11, "DW_OP_consts",      DwOp_1_sleb),
        (0x12, "DW_OP_dup",         DwOp_0),
        (0x13, "DW_OP_drop",        DwOp_0),
        (0x14, "DW_OP_over",        DwOp_0),
        (0x15, "DW_OP_pick",        DwOp_1_u1),
        (0x16, "DW_OP_swap",        DwOp_0),
        (0x17, "DW_OP_rot",         DwOp_0),
        (0x18, "DW_OP_xderef",      DwOp_0),
        (0x19, "DW_OP_abs",         DwOp_0),
        (0x1a, "DW_OP_and",         DwOp_0),
        (0x1b, "DW_OP_div",         DwOp_0),
        (0x1c, "DW_OP_minus",       DwOp_0),
        (0x1d, "DW_OP_mod",         DwOp_0),
        (0x1e, "DW_OP_mul",         DwOp_0),
        (0x1f, "DW_OP_neg",         DwOp_0),
        (0x20, "DW_OP_not",         DwOp_0),
        (0x21, "DW_OP_or",          DwOp_0),
        (0x22, "DW_OP_plus",        DwOp_0),
        (0x23, "DW_OP_plus_uconst", DwOp_1_uleb),
        (0x24, "DW_OP_shl",         DwOp_0),
        (0x25, "DW_OP_shr",         DwOp_0),
        (0x26, "DW_OP_shra",        DwOp_0),
        (0x27, "DW_OP_xor",         DwOp_0),
        (0x28, "DW_OP_bra",         DwOp_1_s2),
        (0x29, "DW_OP_eq",          DwOp_0),
        (0x2a, "DW_OP_ge",          DwOp_0),
        (0x2b, "DW_OP_gt",          DwOp_0),
        (0x2c, "DW_OP_le",          DwOp_0),
        (0x2d, "DW_OP_lt",          DwOp_0),
        (0x2e, "DW_OP_ne",          DwOp_0),
        (0x2f, "DW_OP_skip",        DwOp_1_s2),
        (0x30, "DW_OP_lit0",        DwOp_0),
        (0x31, "DW_OP_lit1",        DwOp_0),
        (0x32, "DW_OP_lit2",        DwOp_0),
        (0x33, "DW_OP_lit3",        DwOp_0),
        (0x34, "DW_OP_lit4",        DwOp_0),
        (0x35, "DW_OP_lit5",        DwOp_0),
        (0x36, "DW_OP_lit6",        DwOp_0),
        (0x37, "DW_OP_lit7",        DwOp_0),
        (0x38, "DW_OP_lit8",        DwOp_0),
        (0x39, "DW_OP_lit9",        DwOp_0),
        (0x3a, "DW_OP_lit10",       DwOp_0),
        (0x3b, "DW_OP_lit11",       DwOp_0),
        (0x3c, "DW_OP_lit12",       DwOp_0),
        (0x3d, "DW_OP_lit13",       DwOp_0),
        (0x3e, "DW_OP_lit14",       DwOp_0),
        (0x3f, "DW_OP_lit15",       DwOp_0),
        (0x40, "DW_OP_lit16",       DwOp_0),
        (0x41, "DW_OP_lit17",       DwOp_0),
        (0x42, "DW_OP_lit18",       DwOp_0),
        (0x43, "DW_OP_lit19",       DwOp_0),
        (0x44, "DW_OP_lit20",       DwOp_0),
        (0x45, "DW_OP_lit21",       DwOp_0),
        (0x46, "DW_OP_lit22",       DwOp_0),
        (0x47, "DW_OP_lit23",       DwOp_0),
        (0x48, "DW_OP_lit24",       DwOp_0),
        (0x49, "DW_OP_lit25",       DwOp_0),
        (0x4a, "DW_OP_lit26",       DwOp_0),
        (0x4b, "DW_OP_lit27",       DwOp_0),
        (0x4c, "DW_OP_lit28",       DwOp_0),
        (0x4d, "DW_OP_lit29",       DwOp_0),
        (0x4e, "DW_OP_lit30",       DwOp_0),
        (0x4f, "DW_OP_lit31",       DwOp_0),
        (0x50, "DW_OP_reg0",        DwOp_0),
        (0x51, "DW_OP_reg1",        DwOp_0),
        (0x52, "DW_OP_reg2",        DwOp_0),
        (0x53, "DW_OP_reg3",        DwOp_0),
        (0x54, "DW_OP_reg4",        DwOp_0),
        (0x55, "DW_OP_reg5",        DwOp_0),
        (0x56, "DW_OP_reg6",        DwOp_0),
        (0x57, "DW_OP_reg7",        DwOp_0),
        (0x58, "DW_OP_reg8",        DwOp_0),
        (0x59, "DW_OP_reg9",        DwOp_0),
        (0x5a, "DW_OP_reg10",       DwOp_0),
        (0x5b, "DW_OP_reg11",       DwOp_0),
        (0x5c, "DW_OP_reg12",       DwOp_0),
        (0x5d, "DW_OP_reg13",       DwOp_0),
        (0x5e, "DW_OP_reg14",       DwOp_0),
        (0x5f, "DW_OP_reg15",       DwOp_0),
        (0x60, "DW_OP_reg16",       DwOp_0),
        (0x61, "DW_OP_reg17",       DwOp_0),
        (0x62, "DW_OP_reg18",       DwOp_0),
        (0x63, "DW_OP_reg19",       DwOp_0),
        (0x64, "DW_OP_reg20",       DwOp_0),
        (0x65, "DW_OP_reg21",       DwOp_0),
        (0x66, "DW_OP_reg22",       DwOp_0),
        (0x67, "DW_OP_reg23",       DwOp_0),
        (0x68, "DW_OP_reg24",       DwOp_0),
        (0x69, "DW_OP_reg25",       DwOp_0),
        (0x6a, "DW_OP_reg26",       DwOp_0),
        (0x6b, "DW_OP_reg27",       DwOp_0),
        (0x6c, "DW_OP_reg28",       DwOp_0),
        (0x6d, "DW_OP_reg29",       DwOp_0),
        (0x6e, "DW_OP_reg30",       DwOp_0),
        (0x6f, "DW_OP_reg31",       DwOp_0),
        (0x70, "DW_OP_breg0",       DwOp_1_sleb),
        (0x71, "DW_OP_breg1",       DwOp_1_sleb),
        (0x72, "DW_OP_breg2",       DwOp_1_sleb),
        (0x73, "DW_OP_breg3",       DwOp_1_sleb),
        (0x74, "DW_OP_breg4",       DwOp_1_sleb),
        (0x75, "DW_OP_breg5",       DwOp_1_sleb),
        (0x76, "DW_OP_breg6",       DwOp_1_sleb),
        (0x77, "DW_OP_breg7",       DwOp_1_sleb),
        (0x78, "DW_OP_breg8",       DwOp_1_sleb),
        (0x79, "DW_OP_breg9",       DwOp_1_sleb),
        (0x7a, "DW_OP_breg10",      DwOp_1_sleb),
        (0x7b, "DW_OP_breg11",      DwOp_1_sleb),
        (0x7c, "DW_OP_breg12",      DwOp_1_sleb),
        (0x7d, "DW_OP_breg13",      DwOp_1_sleb),
        (0x7e, "DW_OP_breg14",      DwOp_1_sleb),
        (0x7f, "DW_OP_breg15",      DwOp_1_sleb),
        (0x80, "DW_OP_breg16",      DwOp_1_sleb),
        (0x81, "DW_OP_breg17",      DwOp_1_sleb),
        (0x82, "DW_OP_breg18",      DwOp_1_sleb),
        (0x83, "DW_OP_breg19",      DwOp_1_sleb),
        (0x84, "DW_OP_breg20",      DwOp_1_sleb),
        (0x85, "DW_OP_breg21",      DwOp_1_sleb),
        (0x86, "DW_OP_breg22",      DwOp_1_sleb),
        (0x87, "DW_OP_breg23",      DwOp_1_sleb),
        (0x88, "DW_OP_breg24",      DwOp_1_sleb),
        (0x89, "DW_OP_breg25",      DwOp_1_sleb),
        (0x8a, "DW_OP_breg26",      DwOp_1_sleb),
        (0x8b, "DW_OP_breg27",      DwOp_1_sleb),
        (0x8c, "DW_OP_breg28",      DwOp_1_sleb),
        (0x8d, "DW_OP_breg29",      DwOp_1_sleb),
        (0x8e, "DW_OP_breg30",      DwOp_1_sleb),
        (0x8f, "DW_OP_breg31",      DwOp_1_sleb),
        (0x90, "DW_OP_regx",        DwOp_1_uleb),
        (0x91, "DW_OP_fbreg",       DwOp_1_sleb),
        (0x92, "DW_OP_bregx",       DwOp_2_uleb_sleb),
        (0x93, "DW_OP_piece",       DwOp_1_uleb),
        (0x94, "DW_OP_deref_size",  DwOp_1_u1),
        (0x95, "DW_OP_xderef_size", DwOp_1_u1),
        (0x96, "DW_OP_nop",         DwOp_0),
        (0xef, "DW_OP_GNU_i8call",  DwOp_0)):
    assert not by_name.has_key(name)
    assert not by_opcode.has_key(opcode)
    op = klass(opcode, name)
    by_name[name] = by_opcode[opcode] = op
del opcode, name, klass, op
