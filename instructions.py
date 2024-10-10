from binaryninja import InstructionTextToken, InstructionTextTokenType
import struct

# Type 1 instructions are those that take two operands.
TYPE1_INSTRUCTIONS = [
    'mov', 'add', 'addc', 'subc', 'sub', 'cmp',
    'dadd', 'bit', 'bic', 'bis', 'xor', 'and'
]

# Type 2 instructions are those that take one operand.
TYPE2_INSTRUCTIONS = [
    'rrc', 'swpb', 'rra', 'sxt', 'push', 'call',
    'reti', 'br'
]

# Type 3 instructions are (un)conditional branches. They do not
# take any operands, as the branch targets are always immediates
# stored in the instruction itself.
TYPE3_INSTRUCTIONS = [
    'jnz', 'jz', 'jnc', 'jc', 'jn', 'jge', 'jl',
    'jmp'
]

InstructionNames = [
    # No instructions use opcode 0
    None,

    # Type 2 instructions all start with 0x1 but then
    # differentiate by three more bits:
    # 0001 00 XXX .......
    ['rrc', 'swpb', 'rra', 'sxt', 'push', 'call', 'reti'],

    # Type 3 instructions start with either 0x2 or 0x3 and
    # then differentiate with the following three bits:
    # 0010 XXX ..........
    ['jnz', 'jz', 'jnc', 'jc'],
    # 0011 XXX ..........
    ['jn', 'jge', 'jl', 'jmp'],

    # Type 1 instructions all use the top 4 bits
    # for their opcodes (0x4 - 0xf)
    'mov',
    'add',
    'addc',
    'subc',
    'sub',
    'cmp',
    'dadd',
    'bit',
    'bic',
    'bis',
    'xor',
    'and'
]

# InstructionMask and InstructionMaskShift are used to mask
# off the bits that are used for the opcode of type 2 and 3
# instructions.
InstructionMask = {
    1: 0x380,
    2: 0xc00,
    3: 0xc00,
}

InstructionMaskShift = {
    1: 7,
    2: 10,
    3: 10
}

# Some instructions can be either 2 byte (word) or 1 byte
# operations.
WORD_WIDTH = 2
BYTE_WIDTH = 1

# There are technically only four different operand modes, but
# certain mode/register combinations have different semantic
# meanings.
REGISTER_MODE = 0
INDEXED_MODE = 1
INDIRECT_REGISTER_MODE = 2
INDIRECT_AUTOINCREMENT_MODE = 3
SYMBOLIC_MODE = 4
ABSOLUTE_MODE = 5
IMMEDIATE_MODE = 6
CONSTANT_MODE0 = 7
CONSTANT_MODE1 = 8
CONSTANT_MODE2 = 9
CONSTANT_MODE4 = 10
CONSTANT_MODE8 = 11
CONSTANT_MODE_NEG1 = 12
OFFSET = 13
OperandLengths = [
    0,  # REGISTER_MODE
    2,  # INDEXED_MODE
    0,  # INDIRECT_REGISTER_MODE
    0,  # INDIRECT_AUTOINCREMENT_MODE
    2,  # SYMBOLIC_MODE
    2,  # ABSOLUTE_MODE
    2,  # IMMEDIATE_MODE
    0,  # CONSTANT_MODE0
    0,  # CONSTANT_MODE1
    0,  # CONSTANT_MODE2
    0,  # CONSTANT_MODE4
    0,  # CONSTANT_MODE8
    0,  # CONSTANT_MODE_NEG1
    0,  # OFFSET
]

Registers = [
    'pc',
    'sp',
    'sr',
    'cg',
    'r4',
    'r5',
    'r6',
    'r7',
    'r8',
    'r9',
    'r10',
    'r11',
    'r12',
    'r13',
    'r14',
    'r15'
]

OperandTokens = [
    lambda reg, value: [    # REGISTER_MODE
        InstructionTextToken(InstructionTextTokenType.RegisterToken, reg)
    ],
    lambda reg, value: [    # INDEXED_MODE
        InstructionTextToken(
            InstructionTextTokenType.IntegerToken, hex(value), value),
        InstructionTextToken(InstructionTextTokenType.TextToken, '('),
        InstructionTextToken(InstructionTextTokenType.RegisterToken, reg),
        InstructionTextToken(InstructionTextTokenType.TextToken, ')')
    ],
    lambda reg, value: [    # INDIRECT_REGISTER_MODE
        InstructionTextToken(InstructionTextTokenType.TextToken, '@'),
        InstructionTextToken(InstructionTextTokenType.RegisterToken, reg)
    ],
    lambda reg, value: [    # INDIRECT_AUTOINCREMENT_MODE
        InstructionTextToken(InstructionTextTokenType.TextToken, '@'),
        InstructionTextToken(InstructionTextTokenType.RegisterToken, reg),
        InstructionTextToken(InstructionTextTokenType.TextToken, '+')
    ],
    lambda reg, value: [    # SYMBOLIC_MODE
        InstructionTextToken(
            InstructionTextTokenType.CodeRelativeAddressToken, hex(value), value)
    ],
    lambda reg, value: [    # ABSOLUTE_MODE
        InstructionTextToken(InstructionTextTokenType.TextToken, '&'),
        InstructionTextToken(
            InstructionTextTokenType.PossibleAddressToken, hex(value), value)
    ],
    lambda reg, value: [    # IMMEDIATE_MODE
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(
            InstructionTextTokenType.PossibleAddressToken, hex(value), value)
    ],
    lambda reg, value: [    # CONSTANT_MODE0
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(InstructionTextTokenType.IntegerToken, str(0), 0)
    ],
    lambda reg, value: [    # CONSTANT_MODE1
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(InstructionTextTokenType.IntegerToken, str(1), 1)
    ],
    lambda reg, value: [    # CONSTANT_MODE2
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(InstructionTextTokenType.IntegerToken, str(2), 2)
    ],
    lambda reg, value: [    # CONSTANT_MODE4
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(InstructionTextTokenType.IntegerToken, str(4), 4)
    ],
    lambda reg, value: [    # CONSTANT_MODE8
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(InstructionTextTokenType.IntegerToken, str(8), 8)
    ],
    lambda reg, value: [    # CONSTANT_MODE_NEG1
        InstructionTextToken(InstructionTextTokenType.TextToken, '#'),
        InstructionTextToken(
            InstructionTextTokenType.IntegerToken, str(-1), -1)
    ],
    lambda reg, value: [    # OFFSET
        InstructionTextToken(InstructionTextTokenType.TextToken, '$'),
        InstructionTextToken(
            InstructionTextTokenType.CodeRelativeAddressToken, hex(value), value)
    ]
]


class Operand:
    def __init__(
        self,
        mode,
        target=None,
        width=None,
        value=None,
        operand_length=0
    ):
        self._mode = mode
        self._width = width
        self._target = target
        self._value = value
        self._length = operand_length

    def __repr__(self):
        return '%s(mode=%s, target=%s, width=%s, value=%s, operand_length=%s)' % (
            type(self).__name__,
            self._mode,
            self._target,
            self._width,
            self._value,
            self._length,
        )

    @property
    def mode(self):
        return self._mode
    
    @property
    def width(self):
        return self._width

    @property
    def target(self):
        return self._target

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v

    @property
    def operand_length(self):
        return self._length

class SourceOperand(Operand):
    @classmethod
    def decode(cls, instr_type, instruction, address):
        if instr_type == 3:
            mode = OFFSET
            target = None
            width = None
        else:
            width = BYTE_WIDTH if (instruction & 0x40) >> 6 else WORD_WIDTH

            # As is in the same place for Type 1 and 2 instructions
            mode = (instruction & 0x30) >> 4

        if instr_type == 2:
            target = Registers[instruction & 0xf]
        elif instr_type == 1:
            target = Registers[(instruction & 0xf00) >> 8]
        
        if target == 'pc':
            if mode == INDEXED_MODE:
                mode = SYMBOLIC_MODE
            elif mode == INDIRECT_AUTOINCREMENT_MODE:
                mode = IMMEDIATE_MODE
        elif target == 'cg':
            if mode == REGISTER_MODE:
                mode = CONSTANT_MODE0
            elif mode == INDEXED_MODE:
                mode = CONSTANT_MODE1
            elif mode == INDIRECT_REGISTER_MODE:
                mode = CONSTANT_MODE2
            else:
                mode = CONSTANT_MODE_NEG1
        elif target == 'sr':
            if mode == INDEXED_MODE:
                mode = ABSOLUTE_MODE
            elif mode == INDIRECT_REGISTER_MODE:
                mode = CONSTANT_MODE4
            elif mode == INDIRECT_AUTOINCREMENT_MODE:
                mode = CONSTANT_MODE8

        operand_length = OperandLengths[mode]

        if instr_type == 3:
            offset = instruction & 0x3ff

            # check if it's a negative offset
            if offset & 0x200:
                offset = -((-offset) & 0x3ff)

            return cls(mode, target, width, offset, operand_length)
        else:
            return cls(mode, target, width, operand_length=operand_length)

class DestOperand(Operand):
    @classmethod
    def decode(cls, instr_type, instruction, address):
        if instr_type != 1:
            return None

        width = BYTE_WIDTH if (instruction & 0x40) >> 6 else WORD_WIDTH
        target = Registers[instruction & 0xf]
        mode = (instruction & 0x80) >> 7

        if target == 'sr' and mode == INDEXED_MODE:
                mode = ABSOLUTE_MODE

        operand_length = OperandLengths[mode]

        return cls(mode, target, width, operand_length=operand_length)

class Instruction:
    @classmethod
    def decode(cls, data, address):
        if len(data) < 2:
            return None

        emulated = False

        instruction = struct.unpack('<H', data[0:2])[0]

        # emulated instructions
        if instruction == 0x4130:
            return cls(address, 'ret', emulated=True)

        opcode = (instruction & 0xf000) >> 12

        mask = InstructionMask.get(opcode)
        shift = InstructionMaskShift.get(opcode)

        if None not in (mask, shift):
            mnemonic = InstructionNames[opcode][(instruction & mask) >> shift]
        else:
            mnemonic = InstructionNames[opcode]

        if mnemonic is None:
            return None

        if mnemonic in TYPE1_INSTRUCTIONS:
            type_ = 1
        elif mnemonic in TYPE2_INSTRUCTIONS:
            type_ = 2
        elif mnemonic in TYPE3_INSTRUCTIONS:
            type_ = 3

        src = SourceOperand.decode(type_, instruction, address)

        dst = DestOperand.decode(type_, instruction, address)

        length = 2 + src.operand_length + (dst.operand_length if dst else 0)

        if len(data) < length:
            return None

        offset = 2
        if src.operand_length:
            src.value = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
        if dst and dst.operand_length:
            dst.value = struct.unpack('<H', data[offset:offset+2])[0]

        # emulated instructions
        if mnemonic == 'mov' and dst.target == 'pc':
            mnemonic = 'br'
            emulated = True

        elif mnemonic == 'bis' and dst.target == 'sr' and src.value == 0xf0:
            return cls(address, 'dint', length=length, emulated=True)

        return cls(address, mnemonic, type_, src, dst, length, emulated)

    def generate_tokens(self):
        tokens = []

        mnemonic = self.mnemonic
        type_ = self.type
        src = self.src
        dst = self.dst

        if src is not None and src.width == BYTE_WIDTH:
            mnemonic += '.b'

        tokens = [
            InstructionTextToken(
                InstructionTextTokenType.TextToken, '{:7s}'.format(mnemonic))
        ]

        if type_ == 1:
            tokens += OperandTokens[src.mode](src.target, src.value)

            tokens += [InstructionTextToken(
                InstructionTextTokenType.TextToken, ',')]

            tokens += OperandTokens[dst.mode](dst.target, dst.value)

        elif type_ == 2:
            tokens += OperandTokens[src.mode](src.target, src.value)

        elif type_ == 3:
            tokens += OperandTokens[src.mode](src.target, src.value)

        return tokens

    def __init__(
        self,
        address,
        mnemonic,
        type_=None,
        src=None,
        dst=None,
        length=2,
        emulated=False
    ):
        self.address = address
        self.mnemonic = mnemonic
        self.src = src
        self.dst = dst
        self.length = length
        self.emulated = emulated
        self.type = type_

    def __repr__(self):
        return '%s(address=0x%04x, mnemonic=%s, type_=%s, src=%s, dst=%s, length=%s, emulated=%d)' % (
            type(self).__name__,
            self.address,
            self.mnemonic,
            self.type,
            self.src,
            self.dst,
            self.length,
            self.emulated,
        )
