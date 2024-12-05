from memory import Memory
from opcodeCases import opCodeTable
from typing import List

class CPU:
    M_CYCLES_PER_FRAME = 17556

    def __init__(self, rom: str):
        self.mem = Memory(rom)
        self.table = opCodeTable(self.mem)

    def execute(self) -> int:
        # each instruction starts by reading the byte at PC which represents the opcode
        # (hint: this is where you reference an opcode table to figure out how to process it)
        opcode = self.mem.read(self.table.PC)
        self.table.PC = (self.table.PC + 1) & 0xFFFF

        #take opcode found and execute using table
        #print(hex(opcode))
        self.table.tableLookup(opcode)
        return 

    def render_frame(self) -> List[List[int]]:
        # each frame takes a fixed length of "time" to render and the way
        # we represent this "time" is through CPU M-cycles. An instruction
        # that is executed can vary between 1-N M-cycles (machine cycles) and
        # we sum the total amount of M-cycles processed per frame here
        m_cycles_ran = 0

        # After 17556 M-cycles, a frame is rendered!
        while m_cycles_ran < self.M_CYCLES_PER_FRAME:
            self.execute()
            m_cycles_ran += self.mem.ticks_per_instr
            self.mem.ticks_per_instr = 0

        return self.mem.ppu.frame