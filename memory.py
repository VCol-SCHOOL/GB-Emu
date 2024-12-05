from typing import List
from timer import Timer
from apu import APU
from ppu import PPU

class Memory:
    def __init__(self, rom: str):
        self.testing = False
        
        self.rom: List[int] = [0] * 0x8000
        self.wram = [0] * 0x2000
        #self.vram = [0] * 0x2000
        #self.xram = [0] * 0x2000
        self.oam = [0] * 0xA0 #sprites
        self.hram = [0] * 0x7F

        self.IF = 0x0
        self.IE = 0x0

        # components of the Gameboy that memory has access to
        self.timer = Timer()
        self.apu = APU()
        self.ppu = PPU()
        
        self.ticks_per_instr = 0

        if rom:
            # loading the "game cartridge" into our emulator
            with open(rom, "rb") as f:
                self.rom = f.read()
        else:
            # if no ROM is "inserted" the CPU is assumed to be in a mode for debugging
            # this array represents the entire memory in a plain array of bytes which
            # is used to test the integrity of tests
            self.testing = True
            self.memory = [0] * 0x10000


    def tick(self):
        self.ticks_per_instr += 1
        # does 1 cycle of work across all connected components
        self.ppu.tick()
        self.apu.tick()
        self.timer.tick()

    # sends data from memory to our CPU
    def read(self, addr: int) -> int:
        self.tick()

        if self.testing:
            return self.memory[addr]
        
        match addr >> 12:
            case 0x0 | 0x1 | 0x2 | 0x3 | 0x4 | 0x5 | 0x6 | 0x7:
                return self.rom[addr]
            case 0xC | 0xD:
                return self.wram[addr - 0xC000]
            case 0xE:
                # Nintendo says use of this area is prohibited.
                return 0xFF
            case 0xF:
                if addr <= 0xFDFF:
                    # Nintendo says use of this area is prohibited.
                    return 0xFF
                elif addr >= 0xFE00 and addr <= 0xFE9F:
                    return self.oam
                elif addr >= 0xFEA0 and addr <= 0xFEFF:
                    # Nintendo says use of this area is prohibited.
                    return 0xFF
                elif addr >= 0xFF80 and addr <= 0xFFFE:
                    return self.hram
                else:
                    # memory mapped IO + IE (interrupt enable register)
                    match addr:
                        case 0xFF44:
                            return self.ppu.LY
                        case _:
                            #vram and xram are here for now
                            print("attempted to read from mmio register:", hex(addr))
                            exit(1)

    # sends data from our CPU to memory
    def write(self, addr: int, value: int):
        self.tick()

        if self.testing:
            self.memory[addr] = value
            return

        match addr >> 12:
            case 0x0 | 0x1 | 0x2 | 0x3 | 0x4 | 0x5 | 0x6 | 0x7:
                self.rom[addr] = value
            case 0xC | 0xD:
                self.wram[addr - 0xC000] = value
            case 0xE:
                # Nintendo says use of this area is prohibited.
                pass
            case 0xF:
                if addr <= 0xFDFF:
                    # Nintendo says use of this area is prohibited.
                    pass
                elif addr >= 0xFE00 and addr <= 0xFE9F:
                    self.oam = value
                elif addr >= 0xFEA0 and addr <= 0xFEFF:
                    # Nintendo says use of this area is prohibited.
                    pass
                elif addr >= 0xFF80 and addr <= 0xFFFE:
                    self.hram = value
                else:
                    # memory mapped IO + IE (interrupt enable register)
                    match addr:
                        case 0xFF07:
                            self.timer.TAC = value
                        case 0xFF0F:
                            self.IF = value
                        case 0xFF26:
                            self.apu.NR52 = value
                        case 0xFF25:
                            self.apu.NR51 = value
                        case 0xFF24:
                            self.apu.NR50 = value
                        case 0xFF40:
                            self.ppu.LCDC = value
                        case 0xFF42:
                            self.ppu.SCY = value
                        case 0xFF43:
                            self.ppu.SCX = value
                        case 0xFF47:
                            self.ppu.BGP = value
                        case 0xFFFF:
                            self.IE = value
                        case _:
                            print("attempted to write to mmio register:", hex(addr))
                            exit(1)
            case _:
                print("attempted to write to:", hex(addr))
                exit(1)